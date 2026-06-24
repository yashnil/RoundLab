"""Pass 15 — Judge Comparison Mode.

Compares adaptation output across two or more judge profiles.
Identifies what remains constant, what changes, and why.
No judge type is treated as inherently superior.
"""

from __future__ import annotations

from typing import Optional

from app.models.judge_adaptation import (
    AdaptationChange,
    JudgeComparisonDiff,
    JudgeComparisonResult,
    JudgeType,
)
from app.services.judge_profiles import (
    get_builtin_profile,
    strongest_differences,
    preference_label,
)
from app.services.adaptation_rules import get_adaptation_changes


# Dimensions that represent structural debate requirements (always present)
_UNIVERSAL_CONSTANTS = [
    "Evidence body text is never altered",
    "Citation and source metadata are preserved",
    "Support verdict is unchanged across all judge types",
    "Factual magnitude and causal strength are preserved",
    "Argument status on the flow is preserved",
    "Population and geographic scope of claims is preserved",
]

_PREFERENCE_DIMENSION_LABELS = {
    "jargon_tolerance": "Jargon tolerance",
    "speed_tolerance": "Speed tolerance",
    "evidence_detail_preference": "Evidence detail preference",
    "line_by_line_expectation": "Line-by-line expectation",
    "extension_strictness": "Extension strictness",
    "weighing_expectation": "Weighing expectation",
    "narrative_preference": "Narrative preference",
    "real_world_explanation": "Real-world explanation expectation",
    "technical_rule_sensitivity": "Technical rule sensitivity",
    "intervention_tolerance": "Intervention tolerance",
    "organization_preference": "Organization preference",
    "source_qualification_importance": "Source qualification importance",
    "persuasion_vs_flow_emphasis": "Persuasion vs flow emphasis",
}

_DIMENSION_EXPLANATIONS = {
    "jargon_tolerance": (
        "High jargon tolerance → use technical debate labels. "
        "Low jargon tolerance → replace all jargon with plain language."
    ),
    "narrative_preference": (
        "High narrative preference → tell a clear story with real-world connection. "
        "Low narrative preference → skip story and lead with argument structure."
    ),
    "line_by_line_expectation": (
        "High expectation → label every response explicitly; drops are permanent. "
        "Low expectation → 1-2 key responses suffice; tracking is not expected."
    ),
    "extension_strictness": (
        "High strictness → every dropped extension is a lost argument. "
        "Low strictness → brief summary of impact is sufficient."
    ),
    "evidence_detail_preference": (
        "High preference → full card text, source context, and qualifier. "
        "Low preference → one-sentence impact summary is enough."
    ),
    "weighing_expectation": (
        "High expectation → explicit comparative analysis on three dimensions. "
        "Low expectation → 'our side wins because X' is sufficient."
    ),
    "real_world_explanation": (
        "High → concrete real-world analogy required for every impact. "
        "Low → abstract analysis is acceptable."
    ),
    "persuasion_vs_flow_emphasis": (
        "High → story, tone, and credibility win the round. "
        "Low → technical flow accuracy wins the round."
    ),
}


def compare_profiles(
    judge_types: list[JudgeType],
    source_type: str,
    source_id: str,
    *,
    tag: Optional[str] = None,
    has_evidence: bool = True,
    response_count: int = 0,
) -> JudgeComparisonResult:
    """Compare adaptations across two or more judge profiles.

    Args:
        judge_types: list of judge types to compare (2-4)
        source_type: "evidence", "argument", "frontline", etc.
        source_id: ID of the source material
        tag: card tag or argument title
        has_evidence: whether evidence cards are linked
        response_count: number of responses (for frontlines)

    Returns:
        JudgeComparisonResult
    """
    if len(judge_types) < 2:
        raise ValueError("At least 2 judge types required for comparison")

    profiles = [get_builtin_profile(jt) or _fallback_profile(jt) for jt in judge_types]
    changes_by_type: dict[str, list[AdaptationChange]] = {}
    for jt in judge_types:
        changes_by_type[jt] = get_adaptation_changes(
            jt,
            tag=tag,
            has_evidence=has_evidence,
            response_count=response_count,
        )

    # ── Constants ─────────────────────────────────────────────────────────────
    constants = list(_UNIVERSAL_CONSTANTS)

    # Find dimensions with the same value across ALL profiles
    if len(profiles) >= 2:
        first_prefs = profiles[0].preferences.model_dump()
        for dim, val in first_prefs.items():
            if all(p.preferences.model_dump()[dim] == val for p in profiles[1:]):
                lbl = _PREFERENCE_DIMENSION_LABELS.get(dim, dim)
                constants.append(f"{lbl}: all profiles agree ({preference_label(val)})")

    # ── Differences ───────────────────────────────────────────────────────────
    differences: list[JudgeComparisonDiff] = []
    wording_diffs: list[JudgeComparisonDiff] = []
    time_diffs: list[JudgeComparisonDiff] = []

    # Pairwise comparison of first two profiles (most informative comparison)
    a, b = profiles[0], profiles[1]
    for dim, va, vb, delta in strongest_differences(a, b, top_n=7):
        if delta == 0:
            continue
        lbl = _PREFERENCE_DIMENSION_LABELS.get(dim, dim)
        why = _DIMENSION_EXPLANATIONS.get(dim, f"Preference gap of {delta} on {lbl}.")
        differences.append(JudgeComparisonDiff(
            dimension=lbl,
            judge_a_value=f"{a.judge_type}: {preference_label(va)}",
            judge_b_value=f"{b.judge_type}: {preference_label(vb)}",
            why_different=why,
        ))

    # Wording differences: changes present in one type but not another
    changes_a_dims = {c.dimension for c in changes_by_type.get(judge_types[0], [])}
    changes_b_dims = {c.dimension for c in changes_by_type.get(judge_types[1], [])}
    only_in_a = changes_a_dims - changes_b_dims
    only_in_b = changes_b_dims - changes_a_dims
    for dim in sorted(only_in_a):
        wording_diffs.append(JudgeComparisonDiff(
            dimension=dim,
            judge_a_value=f"Recommended for {judge_types[0]}",
            judge_b_value=f"Not required for {judge_types[1]}",
            why_different=f"Profile preference difference requires {dim} adaptation only for {judge_types[0]}.",
        ))
    for dim in sorted(only_in_b):
        wording_diffs.append(JudgeComparisonDiff(
            dimension=dim,
            judge_a_value=f"Not required for {judge_types[0]}",
            judge_b_value=f"Recommended for {judge_types[1]}",
            why_different=f"Profile preference difference requires {dim} adaptation only for {judge_types[1]}.",
        ))

    # Time allocation differences
    time_map = {
        "lay": "More time on 1-2 key arguments with explicit impact framing",
        "parent": "More time on context-setting and real-world connection",
        "flow": "Equal time per argument; fast extension signposting",
        "technical": "More time on concession exploitation and burden framing",
        "coach": "Balanced: 1/3 breadth, 1/3 depth, 1/3 weighing",
    }
    for i in range(len(judge_types) - 1):
        ta = time_map.get(judge_types[i], judge_types[i])
        tb = time_map.get(judge_types[i + 1], judge_types[i + 1])
        if ta != tb:
            time_diffs.append(JudgeComparisonDiff(
                dimension="time_allocation",
                judge_a_value=f"{judge_types[i]}: {ta}",
                judge_b_value=f"{judge_types[i+1]}: {tb}",
                why_different="Different judge preference for argument depth vs. breadth coverage.",
            ))

    # ── Risks by judge type (empty here; populated by orchestrator) ───────────
    risks_by_judge: dict[str, list] = {jt: [] for jt in judge_types}

    return JudgeComparisonResult(
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        judge_types=judge_types,
        constants=constants,
        differences=differences,
        strategic_risks_by_judge=risks_by_judge,
        wording_differences=wording_diffs,
        time_allocation_differences=time_diffs,
    )


def _fallback_profile(judge_type: str):
    """Return a minimal fallback profile for unknown types."""
    from app.models.judge_adaptation import JudgePreferences, JudgeProfile
    return JudgeProfile(
        judge_type=judge_type,  # type: ignore[arg-type]
        name=judge_type.title(),
        description="Custom judge profile",
        preferences=JudgePreferences(
            jargon_tolerance=3,
            speed_tolerance=3,
            evidence_detail_preference=3,
            line_by_line_expectation=3,
            extension_strictness=3,
            weighing_expectation=3,
            narrative_preference=3,
            real_world_explanation=3,
            technical_rule_sensitivity=3,
            intervention_tolerance=3,
            organization_preference=3,
            source_qualification_importance=3,
            persuasion_vs_flow_emphasis=3,
        ),
        is_builtin=False,
    )
