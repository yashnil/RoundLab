"""Pass 14 — Frontline Readiness Analysis.

Evaluates each frontline for completeness and safety.
All logic is deterministic — no LLM.

Public interface:
    analyze_frontline(frontline, responses, cards) -> FrontlineReadinessResult
    analyze_frontlines_batch(frontlines, responses_by_fl, cards) -> list[FrontlineReadinessResult]
    classify_readiness(result) -> FrontlineReadiness

Readiness states:
    ready             — well-structured, usable in rounds
    usable_with_gaps  — can be used but has notable gaps
    underdeveloped    — missing a response or critical component
    unsafe            — contains contradicted / unsupported evidence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.models.tournament_prep import FrontlineReadiness

# Response types that count as offensive
_OFFENSIVE_TYPES = {"turn", "counterplan"}

# Response types that count as defensive
_DEFENSIVE_TYPES = {
    "no_link", "link_defense", "impact_defense",
    "uniqueness_takeout", "mitigation", "non_unique",
}

# Unsafe support verdicts for linked evidence
_UNSAFE_VERDICTS = {"unsupported", "contradicted"}


@dataclass
class FrontlineReadinessResult:
    """Full readiness analysis for a single frontline."""
    frontline_id: str
    frontline_title: Optional[str] = None
    opponent_claim: Optional[str] = None

    # Readiness flags
    has_clear_opponent_claim: bool = False
    has_opponent_warrant: bool = False
    has_opponent_impact: bool = False
    has_at_least_one_response: bool = False
    has_response_type_diversity: bool = False
    has_evidence_backed_response: bool = False
    has_offensive_option: bool = False
    has_defensive_coverage: bool = False
    best_first_response_selected: bool = False
    rebuttal_suitable: bool = False
    summary_suitable: bool = False
    final_focus_viable: bool = False
    has_unsafe_evidence: bool = False
    has_stale_evidence_linked: bool = False
    has_source_diversity: bool = False

    # Detail
    response_count: int = 0
    response_types: list[str] = field(default_factory=list)
    unsafe_card_ids: list[str] = field(default_factory=list)
    top_missing: Optional[str] = None
    readiness_label: Optional[FrontlineReadiness] = None
    notes: list[str] = field(default_factory=list)


def analyze_frontline(
    frontline: dict,
    responses: list[dict],
    cards: Optional[dict[str, dict]] = None,
    *,
    stale_card_ids: Optional[set[str]] = None,
) -> FrontlineReadinessResult:
    """
    Evaluate readiness of a single frontline.

    Args:
        frontline: frontline row dict
        responses: list of response row dicts for this frontline
        cards: optional mapping card_id → card dict (for evidence quality checks)
        stale_card_ids: optional set of card_ids that have freshness warnings
    """
    cards = cards or {}
    stale_card_ids = stale_card_ids or set()

    fl_id: str = frontline.get("id", "")
    result = FrontlineReadinessResult(
        frontline_id=fl_id,
        frontline_title=frontline.get("title"),
        opponent_claim=frontline.get("opponent_claim"),
    )

    # ── Opponent claim completeness ───────────────────────────────────────────
    result.has_clear_opponent_claim = bool(
        frontline.get("opponent_claim", "").strip()
    )
    result.has_opponent_warrant = bool(
        frontline.get("opponent_warrant", "").strip()
    )
    result.has_opponent_impact = bool(
        frontline.get("opponent_impact", "").strip()
    )

    if not result.has_clear_opponent_claim:
        result.notes.append("Opponent claim is blank — add the argument you're answering.")

    # ── Response analysis ─────────────────────────────────────────────────────
    result.response_count = len(responses)
    result.has_at_least_one_response = result.response_count > 0

    response_types = [r.get("response_type", "") for r in responses if r.get("response_type")]
    result.response_types = response_types

    # Type diversity: at least 2 distinct types
    distinct_types = set(response_types)
    result.has_response_type_diversity = len(distinct_types) >= 2

    # Offensive option (turn or counterplan)
    result.has_offensive_option = any(t in _OFFENSIVE_TYPES for t in response_types)

    # Defensive coverage
    result.has_defensive_coverage = any(t in _DEFENSIVE_TYPES for t in response_types)

    # Evidence-backed responses (non-analytical)
    non_analytical = [r for r in responses if not r.get("is_analytical", False)]
    result.has_evidence_backed_response = len(non_analytical) > 0

    # Best-first: P1 response exists
    priorities = [r.get("priority", 99) for r in responses]
    result.best_first_response_selected = 1 in priorities

    # ── Speech suitability ────────────────────────────────────────────────────
    all_speeches: set[str] = set()
    for r in responses:
        for sp in r.get("speech_suitability", []):
            all_speeches.add(sp)

    result.rebuttal_suitable = "rebuttal" in all_speeches
    result.summary_suitable = "summary" in all_speeches
    result.final_focus_viable = "final_focus" in all_speeches

    # ── Evidence safety checks ────────────────────────────────────────────────
    unsafe_ids: list[str] = []
    stale_linked = False
    institutions: set[str] = set()
    domains: set[str] = set()

    # Check cards linked to responses
    for r in responses:
        for linked_card_id in r.get("linked_card_ids", []):
            card = cards.get(linked_card_id)
            if card:
                verdict = card.get("support_verdict") or card.get("claim_supported")
                if verdict in _UNSAFE_VERDICTS or verdict is False:
                    unsafe_ids.append(linked_card_id)
                if linked_card_id in stale_card_ids:
                    stale_linked = True
                # Track diversity
                pub = card.get("publication") or ""
                domain = card.get("source_domain") or ""
                if pub:
                    institutions.add(pub.lower()[:40])
                if domain:
                    domains.add(domain.lower())

    result.has_unsafe_evidence = len(unsafe_ids) > 0
    result.unsafe_card_ids = unsafe_ids
    result.has_stale_evidence_linked = stale_linked
    result.has_source_diversity = len(institutions) >= 2 or len(domains) >= 2

    # ── Classify overall readiness ────────────────────────────────────────────
    result.readiness_label = classify_readiness(result)
    result.top_missing = _identify_top_missing(result)

    return result


def classify_readiness(result: FrontlineReadinessResult) -> FrontlineReadiness:
    """Classify readiness level from the result flags."""
    if result.has_unsafe_evidence:
        return "unsafe"
    if not result.has_at_least_one_response:
        return "underdeveloped"
    if not result.has_clear_opponent_claim:
        return "underdeveloped"
    if (
        result.has_evidence_backed_response
        and result.has_defensive_coverage
        and result.rebuttal_suitable
        and result.best_first_response_selected
    ):
        return "ready"
    # Has responses but gaps
    return "usable_with_gaps"


def _identify_top_missing(result: FrontlineReadinessResult) -> Optional[str]:
    """Return the single most important missing element."""
    if result.has_unsafe_evidence:
        return "Unsafe evidence linked — review or replace contradicted/unsupported cards."
    if not result.has_at_least_one_response:
        return "No responses added. Add at least one response to use this frontline."
    if not result.has_clear_opponent_claim:
        return "Opponent claim is missing. Define what argument this frontline answers."
    if not result.has_evidence_backed_response and not any(
        r for r in []  # non-analytical check already done
    ):
        pass
    if not result.rebuttal_suitable:
        return "No responses are tagged for rebuttal — mark at least one for the first rebuttal."
    if not result.best_first_response_selected:
        return "No P1 (priority 1) response set — mark the best response as P1."
    if not result.has_offensive_option:
        return "No offensive option (turn/counterplan). Consider adding one when the argument allows it."
    if not result.has_response_type_diversity:
        return "All responses are the same type. Vary your approach to be more adaptable."
    if result.has_stale_evidence_linked:
        return "Some linked evidence may be stale. Check for newer sources."
    return None


def analyze_frontlines_batch(
    frontlines: list[dict],
    responses_by_fl: dict[str, list[dict]],
    cards: Optional[dict[str, dict]] = None,
    *,
    stale_card_ids: Optional[set[str]] = None,
) -> list[FrontlineReadinessResult]:
    """Analyze a list of frontlines. responses_by_fl maps frontline_id → responses."""
    return [
        analyze_frontline(
            fl,
            responses_by_fl.get(fl.get("id", ""), []),
            cards,
            stale_card_ids=stale_card_ids,
        )
        for fl in frontlines
    ]
