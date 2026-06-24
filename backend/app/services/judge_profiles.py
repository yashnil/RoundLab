"""Pass 15 — Judge Profile Definitions.

Five built-in profiles with deterministic preferences.
Custom profiles are stored in DB and loaded separately.

Preference scale: 1 = very low / not expected, 5 = very high / strongly expected.
"""

from __future__ import annotations

from typing import Optional

from app.models.judge_adaptation import JudgePreferences, JudgeProfile, JudgeType


# ── Built-in profile preference constants ────────────────────────────────────

_BUILTIN_PROFILES: dict[str, dict] = {
    "lay": {
        "name": "Lay Judge",
        "description": (
            "A community member with no formal debate training. "
            "Persuaded by clear stories, plain language, and obvious impact. "
            "Will not track technical argument labels or catch missed line-by-line coverage."
        ),
        "preferences": {
            "jargon_tolerance": 1,
            "speed_tolerance": 1,
            "evidence_detail_preference": 2,
            "line_by_line_expectation": 1,
            "extension_strictness": 1,
            "weighing_expectation": 3,
            "narrative_preference": 5,
            "real_world_explanation": 5,
            "technical_rule_sensitivity": 1,
            "intervention_tolerance": 4,
            "organization_preference": 3,
            "source_qualification_importance": 2,
            "persuasion_vs_flow_emphasis": 5,
        },
    },
    "parent": {
        "name": "Parent Judge",
        "description": (
            "A parent of a debater — familiar with the topic from their child's practice "
            "but not trained in debate theory. Values fairness, clarity, and practical impact. "
            "Expects debate terms to be defined. Will intervene if something seems unfair."
        ),
        "preferences": {
            "jargon_tolerance": 2,
            "speed_tolerance": 1,
            "evidence_detail_preference": 2,
            "line_by_line_expectation": 1,
            "extension_strictness": 2,
            "weighing_expectation": 4,
            "narrative_preference": 5,
            "real_world_explanation": 5,
            "technical_rule_sensitivity": 2,
            "intervention_tolerance": 4,
            "organization_preference": 3,
            "source_qualification_importance": 3,
            "persuasion_vs_flow_emphasis": 4,
        },
    },
    "flow": {
        "name": "Flow Judge",
        "description": (
            "An experienced flow judge who flows every argument and expects clear "
            "line-by-line coverage, explicit extensions, and complete argument structure. "
            "Will drop arguments that are not extended. Tracks drops carefully."
        ),
        "preferences": {
            "jargon_tolerance": 4,
            "speed_tolerance": 4,
            "evidence_detail_preference": 4,
            "line_by_line_expectation": 5,
            "extension_strictness": 5,
            "weighing_expectation": 5,
            "narrative_preference": 2,
            "real_world_explanation": 2,
            "technical_rule_sensitivity": 3,
            "intervention_tolerance": 1,
            "organization_preference": 5,
            "source_qualification_importance": 3,
            "persuasion_vs_flow_emphasis": 2,
        },
    },
    "technical": {
        "name": "Technical Judge",
        "description": (
            "A debater or coach who understands debate rules precisely. "
            "Tracks concessions, drops, and exact argument interactions. "
            "Distinguishes terminal defense from mitigation. Cares about burden and framework."
        ),
        "preferences": {
            "jargon_tolerance": 5,
            "speed_tolerance": 5,
            "evidence_detail_preference": 5,
            "line_by_line_expectation": 5,
            "extension_strictness": 5,
            "weighing_expectation": 5,
            "narrative_preference": 1,
            "real_world_explanation": 1,
            "technical_rule_sensitivity": 5,
            "intervention_tolerance": 1,
            "organization_preference": 5,
            "source_qualification_importance": 4,
            "persuasion_vs_flow_emphasis": 1,
        },
    },
    "coach": {
        "name": "Coach Judge",
        "description": (
            "A coach judge who values educational debate habits, strategic soundness, "
            "and complete argument structure. May correct poor habits even when a shortcut "
            "might technically win. Balances flow and delivery."
        ),
        "preferences": {
            "jargon_tolerance": 4,
            "speed_tolerance": 3,
            "evidence_detail_preference": 4,
            "line_by_line_expectation": 4,
            "extension_strictness": 4,
            "weighing_expectation": 5,
            "narrative_preference": 3,
            "real_world_explanation": 3,
            "technical_rule_sensitivity": 4,
            "intervention_tolerance": 2,
            "organization_preference": 5,
            "source_qualification_importance": 4,
            "persuasion_vs_flow_emphasis": 3,
        },
    },
}


def get_builtin_profile(judge_type: str) -> Optional[JudgeProfile]:
    """Return the built-in profile for a judge type. Returns None for 'custom'."""
    data = _BUILTIN_PROFILES.get(judge_type)
    if not data:
        return None
    return JudgeProfile(
        judge_type=judge_type,  # type: ignore[arg-type]
        name=data["name"],
        description=data["description"],
        preferences=JudgePreferences(**data["preferences"]),
        is_builtin=True,
    )


def get_all_builtin_profiles() -> list[JudgeProfile]:
    """Return all five built-in profiles in a consistent order."""
    return [
        get_builtin_profile("lay"),   # type: ignore[arg-type]
        get_builtin_profile("parent"),
        get_builtin_profile("flow"),
        get_builtin_profile("technical"),
        get_builtin_profile("coach"),
    ]


def profiles_differ_meaningfully(a: JudgeProfile, b: JudgeProfile) -> bool:
    """Return True if two profiles have meaningfully different preferences (diff ≥ 2 on any dim)."""
    pa, pb = a.preferences.model_dump(), b.preferences.model_dump()
    return any(abs(pa[k] - pb[k]) >= 2 for k in pa)


def preference_delta(
    a: JudgeProfile,
    b: JudgeProfile,
) -> dict[str, int]:
    """Return signed delta (b - a) for each preference dimension."""
    pa, pb = a.preferences.model_dump(), b.preferences.model_dump()
    return {k: pb[k] - pa[k] for k in pa}


def strongest_differences(
    a: JudgeProfile,
    b: JudgeProfile,
    top_n: int = 5,
) -> list[tuple[str, int, int, int]]:
    """Return top_n dimensions with the largest absolute preference gap.

    Returns list of (dimension, value_a, value_b, abs_delta) sorted by abs_delta desc.
    """
    pa, pb = a.preferences.model_dump(), b.preferences.model_dump()
    results = [
        (k, pa[k], pb[k], abs(pb[k] - pa[k]))
        for k in pa
    ]
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:top_n]


def preference_label(value: int) -> str:
    """Human label for a 1-5 preference value."""
    return {1: "very low", 2: "low", 3: "moderate", 4: "high", 5: "very high"}.get(value, str(value))
