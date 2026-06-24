"""Pass 15 — Frontline Adaptation for Judge Types.

Determines response ordering, condensation, expansion, and evidence-reading
decisions based on the judge profile. Does not alter response content.
"""

from __future__ import annotations

from typing import Optional

from app.models.judge_adaptation import (
    AdaptationChange,
    AdaptationRisk,
    FrontlineAdaptation,
    JudgeType,
)
from app.services.adaptation_risk_checker import (
    check_all_risks,
    check_unsafe_card,
    check_stale_card,
)

# Response types considered offensive
_OFFENSIVE_TYPES = frozenset({"turn", "straight_turn", "concede_and_turn"})
# Response types considered defensive
_DEFENSIVE_TYPES = frozenset({"non_unique", "no_link", "impact_defense", "block", "direct_refutation"})
# Response types that are analytical (no evidence needed)
_ANALYTICAL_TYPES = frozenset({"analytical", "logical_analogy", "common_sense"})


def _response_type(r: dict) -> str:
    return r.get("response_type", "")


def adapt_frontline_for_judge(
    frontline: dict,
    responses: list[dict],
    cards: Optional[dict[str, dict]] = None,
    *,
    stale_card_ids: Optional[set[str]] = None,
    judge_type: JudgeType = "flow",
) -> FrontlineAdaptation:
    """
    Generate judge-specific frontline presentation guidance.

    Args:
        frontline: frontline row dict
        responses: ordered list of response row dicts
        cards: optional mapping card_id → card dict
        stale_card_ids: optional set of card IDs with freshness warnings
        judge_type: target judge type

    Returns:
        FrontlineAdaptation with no evidence body text included.
    """
    cards = cards or {}
    stale_card_ids = stale_card_ids or set()

    fl_id = frontline.get("id", "")
    changes: list[AdaptationChange] = []
    risks: list[AdaptationRisk] = []

    # ── Collect linked card risks ─────────────────────────────────────────────
    for r in responses:
        for cid in r.get("linked_card_ids", []):
            card = cards.get(cid, {})
            risks.extend(check_unsafe_card(card.get("support_verdict"), judge_type, cid))
            if cid in stale_card_ids:
                risks.extend(check_stale_card("stale", judge_type, cid))

    # ── Sort responses by priority ────────────────────────────────────────────
    sorted_by_priority = sorted(responses, key=lambda r: r.get("priority", 99))

    # Judge-specific ordering logic
    if judge_type in ("lay", "parent"):
        # Lead with the most intuitive/direct response
        direct = [r for r in sorted_by_priority if _response_type(r) in ("direct_refutation",)]
        intuitive = [r for r in sorted_by_priority if _response_type(r) in _DEFENSIVE_TYPES]
        other = [r for r in sorted_by_priority if r not in direct and r not in intuitive]
        ordered = (direct + intuitive + other)[:3]  # cap at 3 for lay
        condensed = [r.get("id", "") for r in sorted_by_priority[3:]]
        changes.append(AdaptationChange(
            dimension="response_ordering",
            adapted="Lead with the most intuitive answer. Cap at 2-3 responses.",
            reason=f"{judge_type.capitalize()} judges lose track of many shallow responses.",
        ))
        if len(responses) > 3:
            changes.append(AdaptationChange(
                dimension="response_count",
                original=f"{len(responses)} responses",
                adapted="2-3 clearest responses",
                reason="More than 3 responses overwhelm a non-flow judge.",
            ))
        read_evidence = any(
            not r.get("is_analytical", False)
            for r in ordered
        )
        analytic_sufficient = not read_evidence

    elif judge_type == "flow":
        ordered = sorted_by_priority  # keep all, preserve priority order
        condensed = []
        changes.append(AdaptationChange(
            dimension="response_labels",
            adapted="Label each response clearly: 'First, [label]. Second, [label].'",
            reason="Flow judges track argument labels and will drop unlabeled responses.",
        ))
        read_evidence = True
        analytic_sufficient = all(_response_type(r) in _ANALYTICAL_TYPES for r in responses)

    elif judge_type == "technical":
        # Concession-exploiting responses first, then defensive
        offensive = [r for r in sorted_by_priority if _response_type(r) in _OFFENSIVE_TYPES]
        defensive = [r for r in sorted_by_priority if r not in offensive]
        ordered = offensive + defensive
        condensed = []
        changes.append(AdaptationChange(
            dimension="concession_exploitation",
            adapted="Identify explicit concessions first. Then handle defensive coverage.",
            reason="Technical judges reward precise exploitation of concessions and drops.",
        ))
        changes.append(AdaptationChange(
            dimension="offense_defense_separation",
            adapted="Clearly separate turns (offense) from defensive responses.",
            reason="Technical judges distinguish terminal defense from mitigation separately.",
        ))
        read_evidence = True
        analytic_sufficient = False

    elif judge_type == "coach":
        # Recommend strategically best structure
        ordered = sorted_by_priority
        condensed = []
        changes.append(AdaptationChange(
            dimension="strategic_structure",
            adapted="Use the most strategically sound structure: direct answer → evidence → turn if available → comparative impact.",
            reason="Coach judges reward educational debate habits, not shortcuts.",
        ))
        read_evidence = True
        analytic_sufficient = False

    else:
        ordered = sorted_by_priority
        condensed = []
        read_evidence = True
        analytic_sufficient = False

    recommended_order = [r.get("id", str(i)) for i, r in enumerate(ordered)]
    lead_reason = changes[0].reason if changes else None

    # ── Identify responses to expand ──────────────────────────────────────────
    expand = []
    for r in ordered[:3]:
        if r.get("is_analytical") and judge_type in ("flow", "technical", "coach"):
            expand.append(r.get("id", ""))  # analytical responses need brief evidence cite

    # ── Extension requirements ────────────────────────────────────────────────
    must_extend_summary: list[str] = []
    must_extend_ff: list[str] = []
    for r in ordered[:2]:
        rt = _response_type(r)
        if rt in _OFFENSIVE_TYPES:
            must_extend_summary.append(r.get("id", ""))
            must_extend_ff.append(r.get("id", ""))
        elif rt in ("direct_refutation", "impact_defense") and judge_type in ("flow", "technical"):
            must_extend_summary.append(r.get("id", ""))

    # ── Offensive carry ───────────────────────────────────────────────────────
    offensive = [r for r in ordered if _response_type(r) in _OFFENSIVE_TYPES]
    carry_rec = None
    if offensive:
        best = offensive[0]
        carry_rec = (
            f"The '{_response_type(best)}' response ({best.get('id', '')}) "
            "is the best offensive option to carry into summary and final focus."
        )

    # ── Estimated time ────────────────────────────────────────────────────────
    base_secs = len(ordered) * 25 + (15 if read_evidence else 0)

    return FrontlineAdaptation(
        frontline_id=fl_id,
        judge_type=judge_type,
        recommended_response_order=recommended_order,
        lead_response_reason=lead_reason,
        responses_to_condense=condensed,
        responses_to_expand=expand,
        responses_needing_evidence=[r.get("id", "") for r in ordered if not r.get("is_analytical", False)][:2],
        analytic_responses_sufficient=analytic_sufficient,
        read_evidence=read_evidence,
        offensive_carry_recommendation=carry_rec,
        must_extend_in_summary=must_extend_summary,
        must_extend_in_final_focus=must_extend_ff,
        estimated_rebuttal_seconds=min(base_secs, 120),
        changes=changes,
        risks=risks,
    )
