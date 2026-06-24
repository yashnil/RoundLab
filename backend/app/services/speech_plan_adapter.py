"""Pass 15 — Judge-Specific Speech Plan Adaptation.

Generates speech stage (rebuttal/summary/final focus) plans adapted for a judge type.
Does not generate new arguments or evidence. References existing preparation.
"""

from __future__ import annotations

from typing import Literal, Optional

from app.models.judge_adaptation import (
    AdaptationChange,
    AdaptationRisk,
    JudgeType,
    SpeechStageAdaptation,
)
from app.services.adaptation_risk_checker import (
    check_missing_extension,
    check_new_argument_late_speech,
    check_narrative_over_flow,
)

SpeechStage = Literal["rebuttal", "summary", "final_focus"]


def _time_notes(judge_type: JudgeType, stage: SpeechStage) -> str:
    if stage == "rebuttal":
        if judge_type in ("lay", "parent"):
            return "Spend 60% on 1-2 key responses. Save 40% for explanation and impact."
        if judge_type in ("flow", "technical"):
            return "Cover all responses efficiently. Allocate time by importance, not order."
        return "Balance breadth and depth. 2/3 coverage, 1/3 explanation."
    if stage == "summary":
        if judge_type in ("lay", "parent"):
            return "30s setup the story, 90s on 1-2 key arguments with impact, 30s weighing."
        if judge_type in ("flow", "technical"):
            return "10s per extension + label, 60s weighing, preserve line-by-line coverage."
        return "60s extensions, 60s weighing, 30s strategic framing."
    # final_focus
    if judge_type in ("lay", "parent"):
        return "90s telling the story of the round. 30s comparative. No new content."
    if judge_type in ("flow", "technical"):
        return "60s voter framing + extension status. 60s comparative weighing. Exact."
    return "60s strategic framing + best argument. 60s weighing. Clear delivery."


def _collapse_recommendation(judge_type: JudgeType, argument_count: int) -> Optional[str]:
    if argument_count <= 1:
        return None
    if judge_type in ("lay", "parent"):
        return (
            f"Collapse to 1 strong argument in summary. "
            f"A {judge_type} judge cannot track {argument_count} separate voters."
        )
    if judge_type in ("flow", "technical"):
        return (
            f"Collapse to your strongest 1-2 voters. "
            "Extend each explicitly with claim → warrant → impact."
        )
    return f"Collapse to the strategically strongest argument. Explain why it wins the round."


def _voter_framing(judge_type: JudgeType) -> str:
    if judge_type in ("lay", "parent"):
        return "Frame the voter as a real-world outcome: 'The most important question is what happens to [group] if [outcome]...'"
    if judge_type == "flow":
        return "Frame the voter as the argument left standing: 'We win the round because our [impact] is uncontested and outweighs on [dimension]...'"
    if judge_type == "technical":
        return "Frame the voter by burden + concession: 'They conceded [X], which means the [burden] falls on Pro/Con. The only unrefuted offense is...' "
    return "Frame the voter around which team demonstrated better debate: 'The clearest reason to vote for us is...'"


def _extension_guidance(judge_type: JudgeType) -> str:
    if judge_type in ("lay", "parent"):
        return "Remind the judge of your best argument. Say 'Remember, we said...' not 'extend contention 1.'"
    if judge_type in ("flow", "technical"):
        return "Explicit extension required: 'Extend [label] — [evidence tag] — still true because [why] — impacts [impact]'"
    return "Full extension: claim, warrant, evidence reference, and impact."


def adapt_speech_for_judge(
    stage: SpeechStage,
    judge_type: JudgeType,
    *,
    argument_count: int = 2,
    response_count: int = 3,
    has_extensions: bool = True,
    has_weighing: bool = True,
    is_introducing_new_content: bool = False,
    is_heavy_narrative: bool = False,
    argument_refs: Optional[list[str]] = None,
) -> SpeechStageAdaptation:
    """Generate a judge-specific speech plan for one stage.

    Args:
        stage: "rebuttal", "summary", or "final_focus"
        judge_type: target judge
        argument_count: number of offense arguments
        response_count: number of defensive responses
        has_extensions: whether arguments are explicitly extended
        has_weighing: whether comparative weighing is present
        is_introducing_new_content: True if new evidence or arguments appear
        is_heavy_narrative: True if presentation is story-heavy
        argument_refs: list of argument IDs for ordering
    """
    argument_refs = argument_refs or []
    changes: list[AdaptationChange] = []
    risks: list[AdaptationRisk] = []

    is_ff = stage == "final_focus"
    is_summary_or_ff = stage in ("summary", "final_focus")

    # ── New content risk ──────────────────────────────────────────────────────
    risks.extend(check_new_argument_late_speech(is_ff, is_introducing_new_content))
    risks.extend(check_missing_extension(is_summary_or_ff, has_extensions, judge_type))
    risks.extend(check_narrative_over_flow(judge_type, is_heavy_narrative))

    # ── Response ordering ─────────────────────────────────────────────────────
    if stage == "rebuttal":
        if judge_type in ("lay", "parent"):
            ordering = ["Most intuitive response first", "Clear impact statement", "Brief evidence"]
        elif judge_type in ("flow", "technical"):
            ordering = ["Labeled responses in argument order", "Quick weighing preview"]
        else:
            ordering = ["Strategically most important first", "Balance breadth and depth"]
    elif stage == "summary":
        if judge_type in ("lay", "parent"):
            ordering = ["Reset the narrative", "Best argument with impact", "Weighing: why ours matters more"]
        elif judge_type in ("flow", "technical"):
            ordering = ["Extend all live arguments by label", "Answer all remaining offense", "Comparative weighing"]
        else:
            ordering = ["Key extensions with evidence", "Collapse to strongest voter", "Strategic weighing"]
    else:  # final_focus
        if judge_type in ("lay", "parent"):
            ordering = ["Story of the round", "One clear impact", "Comparative: why you win"]
        elif judge_type in ("flow", "technical"):
            ordering = ["Voter framing", "Extension status per argument", "Comparative weighing: 3 dimensions"]
        else:
            ordering = ["Best argument + strategic reason", "Comparative weighing", "Call to action"]

    # ── Weighing ──────────────────────────────────────────────────────────────
    if not has_weighing:
        changes.append(AdaptationChange(
            dimension="weighing",
            adapted=_voter_framing(judge_type),
            reason=f"No weighing detected. {judge_type.capitalize()} judge needs explicit comparison.",
        ))

    # ── Extension guidance ────────────────────────────────────────────────────
    if is_summary_or_ff:
        changes.append(AdaptationChange(
            dimension="extension",
            adapted=_extension_guidance(judge_type),
            reason=f"Extension format must match what a {judge_type} judge can track.",
        ))

    # ── Collapse ──────────────────────────────────────────────────────────────
    collapse = _collapse_recommendation(judge_type, argument_count) if is_summary_or_ff else None

    # ── Suggested phrasing ────────────────────────────────────────────────────
    phrasing: list[str] = []
    if is_ff:
        phrasing.append(_voter_framing(judge_type))
    if stage == "summary" and judge_type in ("lay", "parent"):
        phrasing.append("'Here's what you need to know about this round...'")
    if stage == "summary" and judge_type in ("flow", "technical"):
        phrasing.append("'Extending [label] — still true because — impacts [label].'")

    # ── Estimated time ────────────────────────────────────────────────────────
    time_map = {"rebuttal": 180, "summary": 150, "final_focus": 120}
    est_secs = time_map.get(stage, 150)

    required_extensions = argument_refs[:2] if (is_summary_or_ff and judge_type in ("flow", "technical", "coach")) else []

    return SpeechStageAdaptation(
        stage=stage,
        judge_type=judge_type,
        response_ordering=ordering,
        time_allocation_notes=_time_notes(judge_type, stage),
        evidence_vs_analytics_balance=(
            "Fewer cards, more analysis" if judge_type in ("lay", "parent")
            else "Evidence for every claim" if judge_type in ("technical",)
            else "Balance: evidence for major claims, analytics for responses"
        ),
        collapse_recommendation=collapse,
        required_extensions=required_extensions,
        voter_framing=_voter_framing(judge_type) if is_summary_or_ff else None,
        comparative_explanation=(
            "Compare magnitude, timeframe, and probability explicitly" if judge_type in ("flow", "technical")
            else "Explain which impact is more real and more immediate"
        ),
        technical_detail_level=(
            "high" if judge_type in ("technical",)
            else "moderate" if judge_type in ("flow", "coach")
            else "low"
        ),
        suggested_phrasing=phrasing,
        changes=changes,
        risks=risks,
        estimated_seconds=est_secs,
    )
