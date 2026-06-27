"""Diagnostic engine — initial skill assessment from minimal evidence."""
from __future__ import annotations

from typing import Optional

from app.event_packs.public_forum import (
    NOVICE_PF_CURRICULUM,
    LEGACY_SKILL_MAP,
    SKILL_PREREQUISITES,
    SKILL_REGISTRY,
    get_skill,
    resolve_legacy_skill,
)
from app.services.mastery_engine import normalize_score, PROFICIENT_THRESHOLD, MASTERY_THRESHOLD

# ── Experience-level baseline scores ──────────────────────────────────────────

_BASELINE: dict[str, float] = {
    "first_time": 5.0,
    "novice":     15.0,
    "jv":         30.0,
    "varsity":    50.0,
}

_BASELINE_CONFIDENCE: dict[str, float] = {
    "first_time": 0.3,
    "novice":     0.3,
    "jv":         0.35,
    "varsity":    0.4,
}

_WITH_SPEECH_CONFIDENCE: dict[str, float] = {
    "first_time": 0.4,
    "novice":     0.4,
    "jv":         0.45,
    "varsity":    0.5,
}

# Self-rating 1-5 → score boost
_SELF_RATING_BOOST: dict[int, float] = {1: 0.0, 2: 5.0, 3: 10.0, 4: 20.0, 5: 30.0}

# Rubric dimension name → canonical skill ID mapping
_RUBRIC_TO_SKILL: dict[str, str] = {
    "case_structure":  "organization",
    "warranting":      "warranting",
    "evidence_use":    "evidence_use",
    "clash":           "clash",
    "weighing":        "weighing",
    "delivery":        "clarity",
    "organization":    "organization",
    "impact":          "impact_explanation",
    "extensions":      "extensions",
    "drops":           "responses",
    "crossfire":       "crossfire_skill",
    "judge_adaptation": "judge_adaptation",
    "claim_support":   "warranting",
    "argument_quality": "warranting",
    "response_quality": "responses",
}


# ── Public API ────────────────────────────────────────────────────────────────

def compute_initial_mastery_from_diagnostic(intake_data: dict) -> dict[str, dict]:
    """
    Compute initial mastery estimates from diagnostic intake data.

    intake_data keys:
      experience_level : str ('first_time'|'novice'|'jv'|'varsity')
      self_ratings     : dict[str, int]   skill_id → 1-5 rating
      speech_scores    : dict[str, float] rubric dimension → 0-20 score (optional)

    Returns: dict[skill_id, {mastery_score, confidence, mastery_state, source}]
    """
    experience_level = intake_data.get("experience_level", "novice")
    self_ratings: dict[str, int] = intake_data.get("self_ratings", {})
    speech_scores: dict[str, float] = intake_data.get("speech_scores", {})

    baseline = _BASELINE.get(experience_level, 15.0)
    has_speech = bool(speech_scores)

    if has_speech:
        confidence_base = _WITH_SPEECH_CONFIDENCE.get(experience_level, 0.4)
    else:
        confidence_base = _BASELINE_CONFIDENCE.get(experience_level, 0.3)

    # Max allowed score ceiling per level (don't over-inflate)
    score_ceiling: dict[str, float] = {
        "first_time": 25.0,
        "novice":     40.0,
        "jv":         60.0,
        "varsity":    80.0,
    }
    ceiling = score_ceiling.get(experience_level, 40.0)

    result: dict[str, dict] = {}

    # Build speech-score map: canonical skill_id → normalized score
    speech_skill_scores: dict[str, float] = {}
    for dim_name, raw in speech_scores.items():
        canonical = _RUBRIC_TO_SKILL.get(dim_name) or resolve_legacy_skill(dim_name)
        if canonical in SKILL_REGISTRY:
            speech_skill_scores[canonical] = normalize_score(raw, "speech_analysis", "0-20")

    for skill_id in SKILL_REGISTRY:
        score = float(baseline)

        # Self-rating boost
        # Try canonical first, then legacy aliases
        rating_key = skill_id
        rating = self_ratings.get(rating_key)
        if rating is None:
            # Try legacy name
            from app.event_packs.public_forum import CANONICAL_TO_LEGACY
            legacy_name = CANONICAL_TO_LEGACY.get(skill_id)
            if legacy_name:
                rating = self_ratings.get(legacy_name)

        if rating is not None:
            boost = _SELF_RATING_BOOST.get(int(rating), 0.0)
            # Boost is relative to experience level to avoid pushing novices to 80
            score = min(ceiling, score + boost * 0.5)

        # Speech score override (more authoritative than self-rating)
        if skill_id in speech_skill_scores:
            speech_val = speech_skill_scores[skill_id]
            # Blend: 60% speech score, 40% experience-based estimate
            score = min(ceiling, 0.6 * speech_val + 0.4 * score)

        score = max(0.0, round(score, 2))

        # Mastery state from score
        if score >= MASTERY_THRESHOLD:
            state = "mastered"
        elif score >= PROFICIENT_THRESHOLD:
            state = "proficient"
        elif score > 0:
            state = "introduced"
        else:
            state = "not_started"

        source = "speech_and_diagnostic" if has_speech else "diagnostic_only"

        result[skill_id] = {
            "mastery_score": score,
            "confidence": round(confidence_base, 3),
            "mastery_state": state,
            "source": source,
        }

    return result


def identify_strengths_and_priorities(
    mastery_profile: dict[str, dict],
) -> tuple[list[str], list[str]]:
    """
    Return (top_3_strengths, top_3_priorities).

    Strengths: up to 3 skill_ids with highest mastery_score.
    Priorities: up to 3 skill_ids with lowest mastery_score that
                have all prerequisites met.
    """
    from app.event_packs.public_forum import get_prerequisites_met

    skill_scores: list[tuple[str, float]] = [
        (skill_id, float(entry.get("mastery_score", 0)))
        for skill_id, entry in mastery_profile.items()
        if skill_id in SKILL_REGISTRY
    ]

    # Strengths: highest scores
    sorted_desc = sorted(skill_scores, key=lambda x: -x[1])
    strengths = [s[0] for s in sorted_desc[:3] if s[1] > 0]

    # Priorities: lowest scores with prerequisites met
    mastered_set = {
        sid for sid, entry in mastery_profile.items()
        if float(entry.get("mastery_score", 0)) >= PROFICIENT_THRESHOLD
    }

    eligible_low: list[tuple[str, float]] = []
    for skill_id, score in skill_scores:
        if score >= MASTERY_THRESHOLD:
            continue  # already mastered
        if get_prerequisites_met(skill_id, mastered_set):
            eligible_low.append((skill_id, score))

    sorted_asc = sorted(eligible_low, key=lambda x: x[1])
    priorities = [s[0] for s in sorted_asc[:3]]

    return strengths, priorities


def recommend_starting_track(
    experience_level: str,
    priorities: list[str],
) -> str:
    """
    Return the recommended track ID.
    Always returns 'novice_pf' in this pass.
    """
    return "novice_pf"


def get_first_week_plan(
    experience_level: str,
    priorities: list[str],
) -> list[str]:
    """
    Return 3-5 action items as strings for the student's first week.

    Action items are concrete, specific to the identified priorities,
    and appropriate for the experience level.
    """
    if not priorities:
        priorities = ["organization", "warranting", "evidence_use"]

    top_skill = priorities[0] if priorities else "organization"
    skill = get_skill(top_skill)
    skill_name = skill["name"] if skill else top_skill.replace("_", " ").title()

    second_skill_id = priorities[1] if len(priorities) > 1 else "warranting"
    second_skill = get_skill(second_skill_id)
    second_name = second_skill["name"] if second_skill else second_skill_id.replace("_", " ").title()

    # Find lesson for top skill
    lesson = None
    for l in NOVICE_PF_CURRICULUM:
        if l["skill_id"] == top_skill:
            lesson = l
            break

    base_actions = [
        f"Complete the '{skill_name}' lesson in the Training OS curriculum.",
        f"Record a 2-minute practice speech focusing on {skill_name} and review the recording.",
        f"Do the micro drill from the {skill_name} lesson at least twice this week.",
        f"Identify one moment in your next practice round where you apply {second_name}.",
    ]

    if experience_level == "first_time":
        base_actions.insert(0, "Read the novice PF guide to understand speech structure before drilling.")

    elif experience_level in ("jv", "varsity"):
        base_actions.append(
            f"After each practice round, write one note on how well you applied {skill_name} under pressure."
        )

    return base_actions[:5]
