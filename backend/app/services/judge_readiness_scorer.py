"""Pass 15 — Judge Readiness Scoring.

Separate dimension from evidence quality (never merged).
Deterministic arithmetic scoring over structured analysis data.
None = no data (not 0).
"""

from __future__ import annotations

from typing import Optional

from app.models.judge_adaptation import (
    AdaptationRisk,
    JudgeReadinessDimensionScore,
    JudgeReadinessReport,
    JudgeType,
)

_SEVERITY_DEDUCTION = {
    "critical": 30,
    "high": 18,
    "medium": 10,
    "low": 4,
}


def _dim_score(
    name: str,
    base: int,
    deductions: int,
    explanation: str,
    contributing_risks: list[str],
    has_data: bool = True,
) -> JudgeReadinessDimensionScore:
    if not has_data:
        return JudgeReadinessDimensionScore(
            dimension=name,
            score=None,
            explanation=f"No data available for {name}.",
            contributing_risks=[],
        )
    score = max(0, min(100, base - deductions))
    return JudgeReadinessDimensionScore(
        dimension=name,
        score=score,
        explanation=explanation,
        contributing_risks=contributing_risks,
    )


def _deduct_from_risks(
    risks: list[AdaptationRisk],
    categories: Optional[set[str]] = None,
) -> tuple[int, list[str]]:
    total = 0
    refs: list[str] = []
    for r in risks:
        if categories is None or r.category in categories:
            total += _SEVERITY_DEDUCTION.get(r.level, 0)
            refs.append(r.description[:80])
    return total, refs


def score_judge_readiness(
    judge_type: JudgeType,
    source_type: str,
    source_id: str,
    user_id: str,
    *,
    risks: list[AdaptationRisk],
    has_changes: bool = True,
    change_count: int = 0,
    has_extensions: bool = True,
    has_weighing: bool = True,
    response_count: int = 0,
    evidence_count: int = 0,
) -> JudgeReadinessReport:
    """
    Compute 8-dimension judge readiness score.

    Separate from evidence quality/freshness dimensions.
    Returns JudgeReadinessReport with composite_score.
    """
    # ── 1. Clarity ────────────────────────────────────────────────────────────
    clarity_risks = {"jargon_overflow", "under_explanation", "narrative_over_flow"}
    clarity_ded, clarity_refs = _deduct_from_risks(risks, clarity_risks)
    clarity_base = 100 if not change_count else max(40, 100 - change_count * 8)
    clarity = _dim_score(
        "clarity",
        clarity_base,
        clarity_ded,
        f"Clarity score for {judge_type} judge based on jargon and explanation checks.",
        clarity_refs,
        has_data=has_changes or bool(risks),
    )

    # ── 2. Organization ───────────────────────────────────────────────────────
    org_ded, org_refs = _deduct_from_risks(risks, {"dropped_argument_uncovered"})
    org_base = 100 if judge_type in ("lay", "parent") else 80 if not has_extensions else 100
    organization = _dim_score(
        "organization",
        org_base,
        org_ded,
        "Organization score based on argument labels and structure.",
        org_refs,
        has_data=True,
    )

    # ── 3. Extension completeness ─────────────────────────────────────────────
    ext_ded, ext_refs = _deduct_from_risks(risks, {"missing_extension"})
    ext_base = 100 if has_extensions else 55
    ext = _dim_score(
        "extension_completeness",
        ext_base,
        ext_ded,
        "Extension completeness for this judge type.",
        ext_refs,
        has_data=(source_type in ("summary", "final_focus") or has_extensions),
    )

    # ── 4. Evidence explanation ───────────────────────────────────────────────
    evid_ded, evid_refs = _deduct_from_risks(risks, {
        "evidence_without_analysis", "unsafe_card_used", "stale_card_used"
    })
    evid_base = 100 if evidence_count > 0 else 60
    evidence_explanation = _dim_score(
        "evidence_explanation",
        evid_base,
        evid_ded,
        "Evidence explanation quality for this judge type.",
        evid_refs,
        has_data=evidence_count > 0,
    )

    # ── 5. Weighing fit ───────────────────────────────────────────────────────
    weigh_base = 100 if has_weighing else 40
    weigh_ded, weigh_refs = _deduct_from_risks(risks, {"warrant_collapsed"})
    weighing_fit = _dim_score(
        "weighing_fit",
        weigh_base,
        weigh_ded,
        "Weighing appropriateness for this judge type.",
        weigh_refs,
        has_data=True,
    )

    # ── 6. Jargon fit ─────────────────────────────────────────────────────────
    jargon_ded, jargon_refs = _deduct_from_risks(risks, {"jargon_overflow"})
    jargon_base = 100 if judge_type in ("technical", "coach") else 85
    jargon_fit = _dim_score(
        "jargon_fit",
        jargon_base,
        jargon_ded,
        f"Jargon appropriateness for {judge_type} judge.",
        jargon_refs,
        has_data=True,
    )

    # ── 7. Strategic focus ────────────────────────────────────────────────────
    strat_ded, strat_refs = _deduct_from_risks(risks, {"causal_overstatement", "source_qualification_inflated"})
    strat_base = 90
    strategic_focus = _dim_score(
        "strategic_focus",
        strat_base,
        strat_ded,
        "Strategic soundness of adaptation for this judge type.",
        strat_refs,
        has_data=True,
    )

    # ── 8. Speech stage legality ──────────────────────────────────────────────
    legal_ded, legal_refs = _deduct_from_risks(risks, {
        "new_argument_late_speech", "missing_extension"
    })
    legal_base = 100 if not legal_ded else 60
    speech_stage_legality = _dim_score(
        "speech_stage_legality",
        legal_base,
        legal_ded,
        "Compliance with PF speech-stage rules (no new content in final focus).",
        legal_refs,
        has_data=(source_type in ("summary", "final_focus", "rebuttal") or bool(legal_ded)),
    )

    # ── Composite ─────────────────────────────────────────────────────────────
    dims = [
        clarity, organization, ext, evidence_explanation,
        weighing_fit, jargon_fit, strategic_focus, speech_stage_legality,
    ]
    scored = [d for d in dims if d.score is not None]
    if scored:
        composite = int(sum(d.score for d in scored) / len(scored))
    else:
        composite = None

    critical = [r for r in risks if r.level == "critical"]
    if critical and composite is not None:
        composite = max(0, composite - len(critical) * 15)

    return JudgeReadinessReport(
        user_id=user_id,
        judge_type=judge_type,
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        clarity=clarity,
        organization=organization,
        extension_completeness=ext,
        evidence_explanation=evidence_explanation,
        weighing_fit=weighing_fit,
        jargon_fit=jargon_fit,
        strategic_focus=strategic_focus,
        speech_stage_legality=speech_stage_legality,
        composite_score=composite,
        risks=risks,
    )
