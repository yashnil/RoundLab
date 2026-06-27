"""
Unified Priority Pipeline — determines the single next student action.

Implements:
  mastery gaps → prerequisite gaps → coach priorities → active assignments
  → tournament urgency → recent performance → next activity

This replaces the ad-hoc priority logic in mission_recommender.py and
training_planner.py when both systems need to agree on one recommendation.

Rules:
  1. Only one primary action at a time.
  2. Next Mission is the vehicle for drill/speech work.
  3. Active training plan steps inform which mission skill to pick.
  4. Completing a mission advances the training plan and vice versa.
  5. Coach overrides beat everything except active assignments with deadlines.
  6. Paused missions do not generate new active work.
"""

from __future__ import annotations

from typing import Optional

from app.event_packs.public_forum import (
    SKILL_PREREQUISITES, SKILL_REGISTRY, resolve_legacy_skill, get_lesson,
)
from app.services.mastery_engine import PROFICIENT_THRESHOLD


# Skills that matter most for PF — ordered by tournament impact
PF_SKILL_PRIORITY_ORDER = [
    "warranting", "evidence_use", "clash", "responses",
    "extensions", "weighing", "collapse", "judge_adaptation",
    "frontlining", "comparative_analysis", "impact_explanation",
    "claim_construction", "organization", "clarity",
]


def _prereqs_met(skill_id: str, mastered_ids: set[str]) -> bool:
    """Return True if all prerequisites for skill_id are in mastered_ids."""
    return all(p in mastered_ids for p in SKILL_PREREQUISITES.get(skill_id, []))


def compute_next_action(
    mastery_profile: dict[str, dict],
    active_plan_week: Optional[dict],
    coach_priority_skills: list[str],
    pending_assignments: list[dict],
    active_missions: list[dict],
    tournament_date_days: Optional[int],
    recent_skill_scores: dict[str, float],
) -> dict:
    """
    Return one recommendation dict:

    {
        "skill_id": str,
        "lesson_id": Optional[str],
        "mission_skill": str,     # may be legacy name for backward compat
        "source": str,            # why this was chosen
        "priority_score": float,
        "context": str,           # human-readable explanation
    }

    All inputs are pre-fetched dicts — no DB calls here.
    """

    # Step 0: never duplicate an active (non-paused) mission
    active_mission_skills = {
        resolve_legacy_skill(m.get("skill", ""))
        for m in active_missions
        if m.get("status") == "active"
    }

    mastered_ids: set[str] = {
        sid for sid, data in mastery_profile.items()
        if data.get("mastery_state") in ("proficient", "mastered")
    }

    # Step 1: active assignment with deadline beats everything
    for assignment in sorted(
        [a for a in pending_assignments if a.get("due_date")],
        key=lambda a: a.get("due_date", ""),
    ):
        skill = resolve_legacy_skill(assignment.get("skill_focus") or assignment.get("skill", ""))
        if not skill or skill in active_mission_skills:
            continue
        if skill in SKILL_REGISTRY:
            return {
                "skill_id": skill,
                "lesson_id": _find_lesson(skill),
                "mission_skill": _to_legacy(skill),
                "source": "coach_assignment",
                "priority_score": 100.0,
                "context": f"Coach assigned {SKILL_REGISTRY[skill]['name']} (due {assignment.get('due_date', 'soon')})",
            }

    # Step 2: active training plan week
    if active_plan_week:
        plan_skill = resolve_legacy_skill(active_plan_week.get("skill_focus", ""))
        if plan_skill and plan_skill in SKILL_REGISTRY and plan_skill not in active_mission_skills:
            if _prereqs_met(plan_skill, mastered_ids):
                return {
                    "skill_id": plan_skill,
                    "lesson_id": active_plan_week.get("lesson_id"),
                    "mission_skill": _to_legacy(plan_skill),
                    "source": "training_plan",
                    "priority_score": 85.0,
                    "context": f"Training plan: {SKILL_REGISTRY[plan_skill]['name']} — {active_plan_week.get('objective', '')}",
                }

    # Step 3: coach priority skills (no deadline)
    for skill_raw in coach_priority_skills:
        skill = resolve_legacy_skill(skill_raw)
        if skill in SKILL_REGISTRY and skill not in active_mission_skills:
            if _prereqs_met(skill, mastered_ids):
                return {
                    "skill_id": skill,
                    "lesson_id": _find_lesson(skill),
                    "mission_skill": _to_legacy(skill),
                    "source": "coach_priority",
                    "priority_score": 80.0,
                    "context": f"Coach prioritized {SKILL_REGISTRY[skill]['name']}",
                }

    # Step 4: mastery gaps — find lowest-scored skill where prereqs met
    candidates: list[tuple[float, float, str]] = []
    for skill_id in PF_SKILL_PRIORITY_ORDER:
        if skill_id not in SKILL_REGISTRY:
            continue
        if skill_id in active_mission_skills:
            continue
        if not _prereqs_met(skill_id, mastered_ids):
            continue
        score = float((mastery_profile.get(skill_id) or {}).get("mastery_score", 0))
        if score >= PROFICIENT_THRESHOLD:
            continue
        # Priority index from the order list (lower idx = higher priority)
        idx = PF_SKILL_PRIORITY_ORDER.index(skill_id)
        priority_weight = (PROFICIENT_THRESHOLD - score) + (len(PF_SKILL_PRIORITY_ORDER) - idx) * 0.5
        # Boost if tournament is soon
        if tournament_date_days is not None and tournament_date_days <= 14:
            priority_weight *= 1.5
        candidates.append((-priority_weight, score, skill_id))

    if candidates:
        candidates.sort()
        skill_id = candidates[0][2]
        score = candidates[0][1]
        return {
            "skill_id": skill_id,
            "lesson_id": _find_lesson(skill_id),
            "mission_skill": _to_legacy(skill_id),
            "source": "mastery_gap",
            "priority_score": abs(candidates[0][0]),
            "context": f"{SKILL_REGISTRY[skill_id]['name']} needs work (current: {score:.0f}/100)",
        }

    # Step 5: needs_refresh — find stale proficient skill
    refresh_candidates = [
        sid for sid, data in mastery_profile.items()
        if data.get("mastery_state") == "needs_refresh"
        and sid not in active_mission_skills
    ]
    if refresh_candidates:
        skill_id = refresh_candidates[0]
        name = SKILL_REGISTRY.get(skill_id, {}).get("name", skill_id)
        return {
            "skill_id": skill_id,
            "lesson_id": _find_lesson(skill_id),
            "mission_skill": _to_legacy(skill_id),
            "source": "needs_refresh",
            "priority_score": 40.0,
            "context": f"{name} hasn't been practiced recently — refresh it",
        }

    # Step 6: fallback — first available skill
    fallback = PF_SKILL_PRIORITY_ORDER[0]
    return {
        "skill_id": fallback,
        "lesson_id": _find_lesson(fallback),
        "mission_skill": _to_legacy(fallback),
        "source": "fallback",
        "priority_score": 10.0,
        "context": f"Start with {SKILL_REGISTRY.get(fallback, {}).get('name', fallback)}",
    }


def _find_lesson(skill_id: str) -> Optional[str]:
    """Find the first curriculum lesson for a skill."""
    from app.event_packs.public_forum import NOVICE_PF_CURRICULUM
    for lesson in NOVICE_PF_CURRICULUM:
        lesson_skill = resolve_legacy_skill(lesson.get("skill_id", ""))
        if lesson_skill == skill_id:
            return lesson["id"]
    return None


def _to_legacy(canonical_skill: str) -> str:
    """Convert canonical skill ID back to a legacy name for mission_recommender compatibility."""
    from app.event_packs.public_forum import CANONICAL_TO_LEGACY
    return CANONICAL_TO_LEGACY.get(canonical_skill, canonical_skill)


def sync_plan_with_mission_completion(
    mastery_profile: dict[str, dict],
    active_plan: dict,
    completed_mission_skill: str,
) -> dict:
    """
    When a mission completes, check if the plan's current week should advance.

    Returns the updated plan dict (in-memory). Caller persists to DB.
    The plan week advances if:
    - The completed skill matches the current week's skill_focus, AND
    - mastery for that skill is now >= proficient threshold
    """
    if not active_plan or not active_plan.get("weeks"):
        return active_plan

    current_week_idx = active_plan.get("current_week", 1) - 1
    weeks = active_plan.get("weeks", [])
    if current_week_idx >= len(weeks):
        return active_plan

    current_week = weeks[current_week_idx]
    week_skill = resolve_legacy_skill(current_week.get("skill_focus", ""))
    mission_skill = resolve_legacy_skill(completed_mission_skill)

    if week_skill != mission_skill:
        return active_plan

    # Check mastery
    skill_data = mastery_profile.get(week_skill, {})
    score = float(skill_data.get("mastery_score", 0))
    if score >= PROFICIENT_THRESHOLD:
        new_week = min(active_plan["current_week"] + 1, active_plan.get("total_weeks", 4))
        return {**active_plan, "current_week": new_week}

    return active_plan
