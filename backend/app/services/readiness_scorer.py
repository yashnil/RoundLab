"""Pass 14 — Readiness Scoring.

Computes dimension scores (0-100) from gap lists and coverage results.
All arithmetic is deterministic. No LLM involved.

Scoring principles:
    - Missing data returns None (not 0) so the UI can render "not enough data"
    - Weights are documented and configurable via DEFAULT_WEIGHTS
    - Each dimension returns a DimensionScore with explanation and contributing gaps

Public interface:
    score_dimensions(report_data) -> ReadinessDimensions
    compute_composite(dimensions, weights) -> Optional[int]
"""

from __future__ import annotations

import math
from typing import Optional

from app.models.tournament_prep import (
    BlockfileCoverageResult,
    DimensionScore,
    EvidenceFreshnessAssessment,
    GapSeverity,
    PrepGap,
    ReadinessDimensions,
)

# ── Default dimension weights ─────────────────────────────────────────────────
# Documented here; tests can override.

DEFAULT_WEIGHTS: dict[str, float] = {
    "argument_coverage": 1.5,
    "evidence_quality": 1.2,
    "evidence_freshness": 1.0,
    "frontline_readiness": 1.3,
    "source_diversity": 0.8,
    "speech_stage_readiness": 1.0,
    "weighing_preparation": 0.9,
}

# Gap severity → score deduction
_SEVERITY_DEDUCTION: dict[str, int] = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
    "info": 0,
}


def _deduct_from_gaps(
    starting: int,
    gaps: list[PrepGap],
    categories: Optional[set[str]] = None,
) -> tuple[int, list[str]]:
    """
    Deduct points for relevant gaps from a starting score.
    Returns (final_score, [gap_ids_that_contributed]).
    """
    score = starting
    contributing: list[str] = []
    for gap in gaps:
        if categories and gap.gap_category not in categories:
            continue
        deduction = _SEVERITY_DEDUCTION.get(gap.severity, 0)
        if deduction > 0:
            score -= deduction
            if gap.id:
                contributing.append(gap.id)
    return max(0, score), contributing


# ── Dimension scorers ─────────────────────────────────────────────────────────

def _score_argument_coverage(
    gaps: list[PrepGap],
    total_arguments: int,
    blockfile_coverage: list[BlockfileCoverageResult],
) -> DimensionScore:
    dim = "argument_coverage"

    if total_arguments == 0 and not blockfile_coverage:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="No arguments or blockfiles found. Add arguments for this resolution to get a score.",
        )

    # Base score from coverage percentage
    if blockfile_coverage:
        avg_pct = sum(r.coverage_pct for r in blockfile_coverage) / len(blockfile_coverage)
        base = int(avg_pct)
    else:
        base = 60  # assume partial if arguments exist but no blockfiles

    # Deduct for argument-related gaps
    arg_gap_categories = {
        "missing_argument", "missing_claim_support", "missing_warrant",
        "missing_impact", "missing_uniqueness", "missing_link",
        "missing_internal_link",
    }
    score, contributing = _deduct_from_gaps(base, gaps, arg_gap_categories)

    covered_sections = sum(1 for r in blockfile_coverage if r.coverage_pct >= 80)
    total_sections = len(blockfile_coverage) or total_arguments or 1
    pct_label = f"{covered_sections}/{total_sections} sections above 80% coverage"

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=f"Argument coverage at {score}/100. {pct_label}.",
        contributing_gaps=contributing,
    )


def _score_evidence_quality(
    gaps: list[PrepGap],
    total_cards: int,
) -> DimensionScore:
    dim = "evidence_quality"

    if total_cards == 0:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="No cards saved to the library yet.",
        )

    quality_gap_categories = {
        "unsupported_card", "partial_support", "abstract_only",
        "weak_source", "duplicate_evidence",
    }
    score, contributing = _deduct_from_gaps(100, gaps, quality_gap_categories)

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=(
            f"Evidence quality at {score}/100 across {total_cards} card(s). "
            f"{len(contributing)} quality-related gap(s) detected."
        ),
        contributing_gaps=contributing,
    )


def _score_evidence_freshness(
    freshness_assessments: list[EvidenceFreshnessAssessment],
    gaps: list[PrepGap],
) -> DimensionScore:
    dim = "evidence_freshness"

    if not freshness_assessments:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="No cards assessed for freshness yet.",
        )

    # Count states
    counts: dict[str, int] = {}
    for a in freshness_assessments:
        counts[a.freshness_state] = counts.get(a.freshness_state, 0) + 1

    total = len(freshness_assessments)
    stale = counts.get("stale", 0)
    unknown = counts.get("freshness_unknown", 0)
    aging = counts.get("aging", 0)
    current = counts.get("current", 0) + counts.get("not_time_sensitive", 0) + counts.get("older_but_still_relevant", 0)

    # Stale cards are -15 each (capped), unknown are -5 each
    base = 100
    base -= min(stale * 15, 60)
    base -= min(unknown * 5, 20)
    base -= min(aging * 3, 15)
    score = max(0, base)

    freshness_gaps = [g for g in gaps if g.gap_category in ("stale_evidence", "freshness_unknown")]
    contributing = [g.id for g in freshness_gaps if g.id]

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=(
            f"Freshness at {score}/100. {current} current, {aging} aging, "
            f"{stale} stale, {unknown} unknown date."
        ),
        contributing_gaps=contributing,
    )


def _score_frontline_readiness(
    gaps: list[PrepGap],
    total_frontlines: int,
    frontline_results: Optional[list] = None,  # list[FrontlineReadinessResult]
) -> DimensionScore:
    dim = "frontline_readiness"

    if total_frontlines == 0:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="No frontlines found. Add frontlines to key sections to get a score.",
        )

    if frontline_results:
        # Count by readiness label
        ready = sum(1 for r in frontline_results if r.readiness_label == "ready")
        usable = sum(1 for r in frontline_results if r.readiness_label == "usable_with_gaps")
        underdeveloped = sum(1 for r in frontline_results if r.readiness_label == "underdeveloped")
        unsafe = sum(1 for r in frontline_results if r.readiness_label == "unsafe")
        total = len(frontline_results)

        base = int((ready * 100 + usable * 65 + underdeveloped * 30 + unsafe * 0) / total)
    else:
        fl_gaps = [g for g in gaps if g.gap_category == "frontline_underdeveloped"]
        deduction = sum(_SEVERITY_DEDUCTION.get(g.severity, 0) for g in fl_gaps)
        base = max(0, 100 - deduction)

    frontline_gap_categories = {"frontline_underdeveloped", "missing_response"}
    score, contributing = _deduct_from_gaps(base, gaps, frontline_gap_categories)

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=f"Frontline readiness at {score}/100 across {total_frontlines} frontline(s).",
        contributing_gaps=contributing,
    )


def _score_source_diversity(
    gaps: list[PrepGap],
    total_cards: int,
) -> DimensionScore:
    dim = "source_diversity"

    if total_cards == 0:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="No cards to assess diversity.",
        )

    diversity_gap_categories = {"insufficient_source_diversity", "duplicate_evidence"}
    score, contributing = _deduct_from_gaps(100, gaps, diversity_gap_categories)

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=f"Source diversity at {score}/100 across {total_cards} card(s).",
        contributing_gaps=contributing,
    )


def _score_speech_stage_readiness(
    gaps: list[PrepGap],
    total_frontlines: int,
) -> DimensionScore:
    dim = "speech_stage_readiness"

    speech_gap_categories = {
        "missing_summary_extension", "missing_final_focus_extension",
        "missing_response", "frontline_underdeveloped",
    }
    if not any(g.gap_category in speech_gap_categories for g in gaps) and total_frontlines == 0:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="Insufficient frontline data to assess speech stage readiness.",
        )

    score, contributing = _deduct_from_gaps(100, gaps, speech_gap_categories)

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=f"Speech stage readiness at {score}/100.",
        contributing_gaps=contributing,
    )


def _score_weighing_preparation(
    gaps: list[PrepGap],
    total_cards: int,
) -> DimensionScore:
    dim = "weighing_preparation"

    if total_cards == 0:
        return DimensionScore(
            dimension=dim,
            score=None,
            weight=DEFAULT_WEIGHTS[dim],
            explanation="No cards to assess weighing preparation.",
        )

    weighing_gap_categories = {"missing_weighing", "missing_impact"}
    score, contributing = _deduct_from_gaps(100, gaps, weighing_gap_categories)

    return DimensionScore(
        dimension=dim,
        score=score,
        weight=DEFAULT_WEIGHTS[dim],
        explanation=f"Weighing preparation at {score}/100.",
        contributing_gaps=contributing,
    )


# ── Composite scorer ──────────────────────────────────────────────────────────

def compute_composite(
    dimensions: ReadinessDimensions,
    weights: Optional[dict[str, float]] = None,
) -> Optional[int]:
    """
    Compute weighted average across all dimensions.
    Dimensions with score=None are excluded (not treated as 0).
    Returns None if no dimension has data.
    """
    weights = weights or DEFAULT_WEIGHTS
    dim_list = [
        dimensions.argument_coverage,
        dimensions.evidence_quality,
        dimensions.evidence_freshness,
        dimensions.frontline_readiness,
        dimensions.source_diversity,
        dimensions.speech_stage_readiness,
        dimensions.weighing_preparation,
    ]

    total_weight = 0.0
    weighted_sum = 0.0
    for d in dim_list:
        if d.score is None:
            continue
        w = weights.get(d.dimension, d.weight)
        weighted_sum += d.score * w
        total_weight += w

    if total_weight == 0:
        return None
    return min(100, max(0, round(weighted_sum / total_weight)))


# ── Main scoring entry point ──────────────────────────────────────────────────

def score_dimensions(
    gaps: list[PrepGap],
    total_cards: int = 0,
    total_arguments: int = 0,
    total_frontlines: int = 0,
    blockfile_coverage: Optional[list[BlockfileCoverageResult]] = None,
    freshness_assessments: Optional[list[EvidenceFreshnessAssessment]] = None,
    frontline_results: Optional[list] = None,
    weights: Optional[dict[str, float]] = None,
) -> ReadinessDimensions:
    """Compute all dimension scores from collected analysis data."""
    blockfile_coverage = blockfile_coverage or []
    freshness_assessments = freshness_assessments or []

    dims = ReadinessDimensions(
        argument_coverage=_score_argument_coverage(gaps, total_arguments, blockfile_coverage),
        evidence_quality=_score_evidence_quality(gaps, total_cards),
        evidence_freshness=_score_evidence_freshness(freshness_assessments, gaps),
        frontline_readiness=_score_frontline_readiness(gaps, total_frontlines, frontline_results),
        source_diversity=_score_source_diversity(gaps, total_cards),
        speech_stage_readiness=_score_speech_stage_readiness(gaps, total_frontlines),
        weighing_preparation=_score_weighing_preparation(gaps, total_cards),
    )

    # Apply configured weights
    if weights:
        for d in [
            dims.argument_coverage, dims.evidence_quality, dims.evidence_freshness,
            dims.frontline_readiness, dims.source_diversity,
            dims.speech_stage_readiness, dims.weighing_preparation,
        ]:
            d.weight = weights.get(d.dimension, d.weight)

    return dims
