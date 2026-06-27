"""Training plan generator — deterministic, no LLM."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.event_packs.public_forum import (
    SKILL_PREREQUISITES,
    SKILL_REGISTRY,
    get_lesson,
    NOVICE_PF_CURRICULUM,
    LEGACY_SKILL_MAP,
    get_skill,
)
from app.services.mastery_engine import PROFICIENT_THRESHOLD, MASTERY_THRESHOLD

# ── Priority ordering for PF skills ──────────────────────────────────────────

PF_SKILL_PRIORITY: list[str] = [
    "warranting",
    "evidence_use",
    "clash",
    "responses",
    "extensions",
    "weighing",
    "collapse",
    "judge_adaptation",
    "frontlining",
    "comparative_analysis",
    "impact_explanation",
    "organization",
    "clarity",
    "claim_construction",
    "citation_quality",
    "crossfire_questioning",
    "crossfire_answering",
    "pacing",
    "emphasis",
    "confidence",
    "concision",
    "audience_adaptation",
    "evidence_explanation",
    "constructive_skill",
    "rebuttal_skill",
    "summary_skill",
    "final_focus_skill",
    "crossfire_skill",
]

# Estimated per-week mastery gain by starting level
_EXPECTED_WEEKLY_GAIN: dict[str, float] = {
    "not_started": 15.0,
    "introduced":  12.0,
    "developing":  10.0,
    "proficient":   8.0,
    "mastered":     3.0,
    "needs_refresh": 8.0,
}


def _prereqs_met(skill_id: str, mastery_profile: dict[str, dict]) -> bool:
    """Return True if all prerequisites for skill_id are at or above PROFICIENT_THRESHOLD."""
    prereqs = SKILL_PREREQUISITES.get(skill_id, [])
    for p in prereqs:
        entry = mastery_profile.get(p, {})
        score = float(entry.get("mastery_score", 0))
        if score < PROFICIENT_THRESHOLD:
            return False
    return True


def prioritize_skills(
    mastery_profile: dict[str, dict],
    event_pack: str = "public_forum",
) -> list[str]:
    """
    Return an ordered list of up to 6 skill IDs to focus on next.

    Logic:
    1. Include only skills whose prerequisites are met.
    2. Among those, prefer skills below the proficient threshold (< 50).
    3. Break ties by PF_SKILL_PRIORITY ordering, then by how far below
       the proficient threshold the current score is (larger gap first).
    """
    candidates: list[tuple[int, float, str]] = []  # (priority_rank, gap, skill_id)

    for skill_id in SKILL_REGISTRY:
        entry = mastery_profile.get(skill_id, {})
        score = float(entry.get("mastery_score", 0))

        # Skip already-mastered skills
        if score >= MASTERY_THRESHOLD:
            continue

        if not _prereqs_met(skill_id, mastery_profile):
            continue

        try:
            rank = PF_SKILL_PRIORITY.index(skill_id)
        except ValueError:
            rank = len(PF_SKILL_PRIORITY)

        gap = max(0.0, PROFICIENT_THRESHOLD - score)
        candidates.append((rank, gap, skill_id))

    # Sort: lower rank = higher priority; larger gap = higher priority as tiebreaker
    candidates.sort(key=lambda x: (x[0], -x[1]))
    return [c[2] for c in candidates[:6]]


def _lesson_for_skill(skill_id: str) -> Optional[dict]:
    """Return the first curriculum lesson targeting this skill, or None."""
    for lesson in NOVICE_PF_CURRICULUM:
        if lesson["skill_id"] == skill_id:
            return lesson
    return None


def generate_weekly_objective(
    skill_id: str,
    current_mastery: float,
    week_num: int,
) -> dict:
    """
    Return a weekly plan dict for focusing on a single skill.

    Keys: week, skill_focus, skill_name, objective, lesson_id, drill_description,
          speech_application, completion_criteria, mastery_target, estimated_hours
    """
    skill = get_skill(skill_id) or {}
    skill_name = skill.get("name", skill_id.replace("_", " ").title())
    lesson = _lesson_for_skill(skill_id)
    lesson_id = lesson["id"] if lesson else None

    # Estimate mastery gain this week
    if current_mastery >= MASTERY_THRESHOLD:
        state = "mastered"
    elif current_mastery >= PROFICIENT_THRESHOLD:
        state = "proficient"
    elif current_mastery > 0:
        state = "developing"
    else:
        state = "not_started"

    gain = _EXPECTED_WEEKLY_GAIN.get(state, 10.0)
    mastery_target = min(100.0, round(current_mastery + gain, 1))

    # Drill description from skill registry or lesson
    drill_description = (
        lesson["micro_drill"]
        if lesson
        else f"Practice {skill_name} in a recorded 3-minute speech, then self-critique."
    )

    # Speech application from lesson or generic
    speech_application = (
        lesson["speech_application"]
        if lesson
        else f"Apply {skill_name} in your next practice speech and note where it felt natural vs. forced."
    )

    # Completion criteria
    success_criteria = skill.get("success_criteria", [])
    if lesson:
        completion_criteria = lesson.get("success_checklist", success_criteria)[:4]
    else:
        completion_criteria = success_criteria[:4]

    if not completion_criteria:
        completion_criteria = [
            f"Complete at least one recorded speech focusing on {skill_name}",
            f"Score at least {mastery_target:.0f} mastery points by end of week",
        ]

    objective_map: dict[str, str] = {
        "not_started": f"Learn the fundamentals of {skill_name} and apply them in one practice speech.",
        "introduced": f"Deepen your understanding of {skill_name} through targeted drill work.",
        "developing": f"Build consistency in {skill_name} across multiple speech types.",
        "proficient": f"Achieve mastery-level {skill_name} under tournament conditions.",
        "mastered": f"Maintain and refine {skill_name} — focus on judge-specific adaptation.",
        "needs_refresh": f"Refresh your {skill_name} fundamentals — review and re-apply.",
    }
    objective = objective_map.get(state, f"Work on {skill_name} this week.")

    estimated_hours = 1.0 if state in ("not_started", "introduced") else 1.5

    return {
        "week": week_num,
        "skill_focus": skill_id,
        "skill_name": skill_name,
        "objective": objective,
        "lesson_id": lesson_id,
        "drill_description": drill_description,
        "speech_application": speech_application,
        "completion_criteria": completion_criteria,
        "mastery_target": mastery_target,
        "estimated_hours": estimated_hours,
    }


def generate_plan(
    mastery_profile: dict[str, dict],
    plan_type: str,
    tournament_date: Optional[date] = None,
    coach_priority_skills: Optional[list[str]] = None,
) -> dict:
    """
    Generate a complete training plan dict.

    plan_type: '1_week' | '4_week' | 'tournament_countdown' | 'custom'

    Returns:
      plan_type, event_pack, total_weeks, weeks (list of week dicts), created_at, summary
    """
    # Determine weeks
    if plan_type == "1_week":
        total_weeks = 1
    elif plan_type == "4_week":
        total_weeks = 4
    elif plan_type == "tournament_countdown" and tournament_date is not None:
        today = date.today()
        days_until = max(0, (tournament_date - today).days)
        total_weeks = max(1, min(8, days_until // 7))
    else:
        total_weeks = 4  # default for custom or missing tournament_date

    # Build skill priority queue
    priority_skills = prioritize_skills(mastery_profile)

    # Prepend coach-specified skills (resolve legacy names, dedupe)
    if coach_priority_skills:
        from app.event_packs.public_forum import resolve_legacy_skill
        resolved_coach = [resolve_legacy_skill(s) for s in coach_priority_skills]
        # Put coach skills first, then priority_skills not already in the list
        combined = resolved_coach + [s for s in priority_skills if s not in resolved_coach]
        priority_skills = combined

    # Generate one week per top skill
    weeks: list[dict] = []
    for week_num in range(1, total_weeks + 1):
        idx = (week_num - 1) % max(1, len(priority_skills))
        skill_id = priority_skills[idx] if priority_skills else "organization"
        entry = mastery_profile.get(skill_id, {})
        current_mastery = float(entry.get("mastery_score", 0))
        week_obj = generate_weekly_objective(skill_id, current_mastery, week_num)
        weeks.append(week_obj)

    # Build summary
    if weeks:
        focus_skills = list(dict.fromkeys(w["skill_name"] for w in weeks))[:4]
        summary = (
            f"{total_weeks}-week plan focusing on: {', '.join(focus_skills)}. "
            "Each week includes a curriculum lesson, micro drills, and speech application."
        )
    else:
        summary = f"{total_weeks}-week training plan."

    return {
        "plan_type": plan_type,
        "event_pack": "public_forum",
        "total_weeks": total_weeks,
        "weeks": weeks,
        "created_at": date.today().isoformat(),
        "summary": summary,
    }


def suggest_practice_agenda(
    team_skill_gaps: dict,
    duration_minutes: int = 60,
) -> list[dict]:
    """
    Generate a practice session agenda for a coach based on team skill gaps.

    team_skill_gaps: {skill_id: {avg_score, pct_proficient, pct_mastered, student_count}}

    Returns list of agenda items, each with:
      activity_type, skill_id, description, duration_minutes, team_data_reason
    """
    if not team_skill_gaps:
        return []

    # Sort skills by avg_score ascending (worst gaps first)
    sorted_skills = sorted(
        team_skill_gaps.items(),
        key=lambda kv: (kv[1].get("avg_score", 0), kv[1].get("pct_proficient", 0)),
    )

    # Take top 3 worst skills
    focus_skills = sorted_skills[:3]

    # Reserve 10 min at end for reflection/re-record if time allows
    reflection_time = 10 if duration_minutes >= 30 else 0
    available_time = duration_minutes - reflection_time

    # Allocate time proportionally: worse skills get more time
    gaps = [max(1.0, PROFICIENT_THRESHOLD - kv[1].get("avg_score", 0)) for kv in focus_skills]
    total_gap = sum(gaps)

    agenda: list[dict] = []

    for i, (skill_id, gap_data) in enumerate(focus_skills):
        skill = get_skill(skill_id)
        skill_name = skill["name"] if skill else skill_id.replace("_", " ").title()
        alloc = round((gaps[i] / total_gap) * available_time)
        alloc = max(10, alloc)  # minimum 10 minutes

        avg_score = gap_data.get("avg_score", 0)
        pct_proficient = gap_data.get("pct_proficient", 0)
        student_count = gap_data.get("student_count", 0)

        reason = (
            f"Team average {avg_score:.0f}/100 on {skill_name}; "
            f"only {pct_proficient:.0f}% of {student_count} students are proficient."
        )

        # Choose activity type based on skill level
        if avg_score < 25:
            activity_type = "review"
            description = (
                f"Mini-lesson on {skill_name}: explain the concept, "
                f"show a weak vs. strong example, then check for understanding."
            )
        elif avg_score < 40:
            activity_type = "drill"
            description = (
                f"{skill_name} drill: each debater takes 90 seconds to apply "
                f"{skill_name} in a timed segment. Peer feedback follows."
            )
        else:
            activity_type = "partner_exercise"
            description = (
                f"Partner {skill_name} exercise: one debates, one coaches using "
                f"the success criteria checklist."
            )

        agenda.append({
            "activity_type": activity_type,
            "skill_id": skill_id,
            "description": description,
            "duration_minutes": alloc,
            "team_data_reason": reason,
        })

    # Reflection / re-record block
    if reflection_time > 0:
        top_skill = focus_skills[0][0] if focus_skills else "warranting"
        top_skill_name = get_skill(top_skill)["name"] if get_skill(top_skill) else top_skill
        agenda.append({
            "activity_type": "rerecord",
            "skill_id": top_skill,
            "description": (
                f"Re-record: each debater re-records a 2-minute speech "
                f"focusing on {top_skill_name}. Compare to their previous recording."
            ),
            "duration_minutes": reflection_time,
            "team_data_reason": "Re-record sessions accelerate skill retention.",
        })

    return agenda
