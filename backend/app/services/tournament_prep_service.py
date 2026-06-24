"""Pass 14 — Tournament Prep Orchestrator.

Top-level service that assembles readiness reports by combining:
- Library data from Pass 13 (arguments, blockfiles, frontlines, cards)
- Freshness assessments (Pass 14 freshness service)
- Coverage analysis (Pass 14 blockfile coverage)
- Frontline readiness analysis
- Readiness scoring

Does NOT make any LLM calls — all analysis is deterministic.
Caches reports when the library has not changed (library_watermark unchanged).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.models.tournament_prep import (
    EvidenceFreshnessAssessment,
    GapCategory,
    GapSeverity,
    PrepGap,
    PrepReadinessReport,
    PrepWorkspaceRow,
)
from app.services.blockfile_coverage_analyzer import (
    analyze_blockfile_coverage,
    summarize_coverage_gaps,
)
from app.services.evidence_freshness import (
    assess_freshness_batch,
    freshness_needs_attention,
)
from app.services.frontline_readiness_analyzer import analyze_frontlines_batch
from app.services.readiness_scorer import compute_composite, score_dimensions
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ── Diversity thresholds ───────────────────────────────────────────────────────
_DIVERSITY_INSTITUTION_THRESHOLD = 3  # flag if fewer distinct institutions


def _load_library_data(
    user_id: str,
    resolution_id: Optional[str],
    side: str,
) -> dict:
    """Load all relevant library entities for analysis. Returns a data bundle."""
    sb = get_supabase()
    data: dict = {
        "arguments": [],
        "blockfiles": [],
        "sections": [],
        "entries": [],
        "cards": {},
        "frontlines": [],
        "responses": [],
        "library_metadata": [],
    }

    # Arguments
    q = sb.table("arguments").select("*").eq("user_id", user_id)
    if resolution_id:
        q = q.eq("resolution_id", resolution_id)
    if side != "both":
        q = q.eq("side", side)
    result = q.execute()
    data["arguments"] = result.data or []

    # Blockfiles
    q = sb.table("blockfiles").select("*").eq("user_id", user_id)
    if resolution_id:
        q = q.eq("resolution_id", resolution_id)
    if side != "both":
        q = q.eq("side", side)
    result = q.execute()
    data["blockfiles"] = result.data or []

    blockfile_ids = [bf["id"] for bf in data["blockfiles"]]

    # Sections
    if blockfile_ids:
        q = sb.table("blockfile_sections").select("*").in_("blockfile_id", blockfile_ids)
        result = q.execute()
        data["sections"] = result.data or []

    section_ids = [s["id"] for s in data["sections"]]

    # Entries
    if section_ids:
        q = sb.table("blockfile_entries").select("*").in_("section_id", section_ids)
        result = q.execute()
        data["entries"] = result.data or []

    # Unique card IDs
    card_ids = list({e["card_id"] for e in data["entries"] if e.get("card_id")})

    # Cards + library metadata
    if card_ids:
        # Batch in chunks of 100 (Supabase in_ limit)
        for i in range(0, len(card_ids), 100):
            chunk = card_ids[i:i + 100]
            res = sb.table("evidence_cards").select("*").in_("id", chunk).execute()
            for row in res.data or []:
                data["cards"][row["id"]] = row
        # Library metadata (support_verdict, tags, etc.)
        for i in range(0, len(card_ids), 100):
            chunk = card_ids[i:i + 100]
            res = sb.table("library_card_metadata").select("*").in_("card_id", chunk).execute()
            for row in res.data or []:
                # Merge metadata into card dict
                cid = row["card_id"]
                if cid in data["cards"]:
                    data["cards"][cid].update({
                        "support_verdict": row.get("support_verdict"),
                        "library_tags": row.get("tags", []),
                    })
            data["library_metadata"].extend(res.data or [])

    # Frontlines
    if section_ids:
        q = sb.table("frontlines").select("*").eq("user_id", user_id)
        result = q.execute()
        data["frontlines"] = [f for f in (result.data or []) if f.get("section_id") in section_ids]

    # Responses
    frontline_ids = [f["id"] for f in data["frontlines"]]
    if frontline_ids:
        for i in range(0, len(frontline_ids), 100):
            chunk = frontline_ids[i:i + 100]
            res = sb.table("frontline_responses").select("*").in_("frontline_id", chunk).execute()
            data["responses"].extend(res.data or [])

    return data


def _detect_diversity_gaps(
    cards: dict[str, dict],
    blockfile_id: Optional[str] = None,
) -> list[PrepGap]:
    """Detect insufficient source diversity."""
    gaps: list[PrepGap] = []
    if not cards:
        return gaps

    institutions: dict[str, int] = {}
    seen_bodies: dict[str, str] = {}  # body hash → card_id (for duplicate detection)

    for cid, card in cards.items():
        pub = (card.get("publication") or card.get("source_domain") or "").lower()[:50]
        if pub:
            institutions[pub] = institutions.get(pub, 0) + 1

        # Simple duplicate detection: first 100 chars of body
        body_key = (card.get("body_text") or "")[:100].strip().lower()
        if body_key and len(body_key) > 30:
            if body_key in seen_bodies:
                gaps.append(PrepGap(
                    gap_category="duplicate_evidence",
                    severity="low",
                    title=f"Duplicate evidence: {card.get('tag', cid)[:60]}",
                    reason="Two cards appear to contain the same source text.",
                    card_id=cid,
                    blockfile_id=blockfile_id,
                    recommended_action="Remove the duplicate and keep the best-cut version.",
                    estimated_minutes=5,
                ))
            else:
                seen_bodies[body_key] = cid

    # Insufficient diversity
    if len(institutions) < _DIVERSITY_INSTITUTION_THRESHOLD and len(cards) >= 5:
        top_pub, top_count = max(institutions.items(), key=lambda x: x[1]) if institutions else ("", 0)
        if top_count >= 3:
            gaps.append(PrepGap(
                gap_category="insufficient_source_diversity",
                severity="medium",
                title="Over-reliance on one publication",
                reason=f"'{top_pub}' accounts for {top_count} of your cards. "
                       "Judges may discount your case if all evidence comes from one source.",
                blockfile_id=blockfile_id,
                recommended_action="Find cards from at least 2 additional independent sources.",
                estimated_minutes=30,
            ))

    return gaps


def _detect_quality_gaps(cards: dict[str, dict]) -> list[PrepGap]:
    """Detect weak, unsupported, and abstract-only cards."""
    gaps: list[PrepGap] = []
    for cid, card in cards.items():
        verdict = card.get("support_verdict")
        tag = card.get("tag", cid)[:60]

        if verdict in ("unsupported", "contradicted"):
            gaps.append(PrepGap(
                gap_category="unsupported_card",
                severity="high",
                title=f"Unsafe card: {tag}",
                reason=f"This card has a '{verdict}' support verdict. "
                       "It may be misrepresented or not support the tag.",
                card_id=cid,
                recommended_action="Review and either replace the card or update the tag.",
                estimated_minutes=10,
            ))
        elif verdict == "partially_supported":
            gaps.append(PrepGap(
                gap_category="partial_support",
                severity="medium",
                title=f"Partially supported: {tag}",
                reason="This card only partially supports its tag. "
                       "An opponent may indict it on cross-examination.",
                card_id=cid,
                recommended_action="Find stronger evidence or narrow the tag.",
                estimated_minutes=15,
            ))

        body = card.get("body_text", "")
        if body and len(body.split()) < 30:
            gaps.append(PrepGap(
                gap_category="abstract_only",
                severity="low",
                title=f"Abstract-only card: {tag}",
                reason="This card appears to be very short (abstract-only). "
                       "Judges may not find it persuasive without more context.",
                card_id=cid,
                recommended_action="Expand the card with the full relevant passage.",
                estimated_minutes=15,
            ))

    return gaps


def _detect_frontline_gaps(frontline_results: list) -> list[PrepGap]:
    """Convert frontline readiness results into prep gaps."""
    gaps: list[PrepGap] = []
    for result in frontline_results:
        title = result.frontline_title or result.frontline_id[:8]

        if result.readiness_label == "unsafe":
            gaps.append(PrepGap(
                gap_category="unsupported_card",
                severity="critical",
                title=f"Unsafe frontline: {title}",
                reason=f"This frontline links to contradicted or unsupported evidence: "
                       f"{', '.join(result.unsafe_card_ids[:3])}",
                frontline_id=result.frontline_id,
                recommended_action="Replace or remove unsafe linked evidence.",
                estimated_minutes=10,
            ))
        elif result.readiness_label == "underdeveloped":
            gaps.append(PrepGap(
                gap_category="frontline_underdeveloped",
                severity="high",
                title=f"Underdeveloped frontline: {title}",
                reason=result.top_missing or "Missing key component.",
                frontline_id=result.frontline_id,
                recommended_action="Add at least one response with rebuttal suitability.",
                estimated_minutes=20,
            ))
        elif result.readiness_label == "usable_with_gaps" and result.top_missing:
            gaps.append(PrepGap(
                gap_category="missing_response",
                severity="medium",
                title=f"Frontline gap: {title}",
                reason=result.top_missing,
                frontline_id=result.frontline_id,
                recommended_action="Address the gap identified above.",
                estimated_minutes=15,
            ))

    return gaps


def _detect_coverage_gaps(
    coverage_results: list,
    blockfile_id: Optional[str] = None,
) -> list[PrepGap]:
    """Convert coverage matrix gaps into PrepGap objects."""
    gaps: list[PrepGap] = []
    for result in coverage_results:
        for gap_cat in result.gaps:
            severity: GapSeverity = "medium"
            # Missing required dimensions are high severity
            if gap_cat in ("missing_warrant", "missing_impact", "missing_claim"):
                severity = "high"
            elif gap_cat in ("missing_weighing", "missing_summary_extension"):
                severity = "low"

            gaps.append(PrepGap(
                gap_category=gap_cat if gap_cat in (
                    "missing_argument", "missing_claim_support", "missing_warrant",
                    "missing_impact", "missing_uniqueness", "missing_link",
                    "missing_internal_link", "missing_response", "missing_counterevidence",
                    "missing_weighing", "missing_summary_extension", "missing_final_focus_extension",
                ) else "missing_argument",
                severity=severity,
                title=f"{gap_cat.replace('_', ' ').title()} in '{result.section_title}'",
                reason=f"Section '{result.section_title}' is missing the {gap_cat.replace('_', ' ')} component.",
                section_id=result.section_id,
                blockfile_id=blockfile_id,
                recommended_action=f"Add evidence or content that addresses the {gap_cat.replace('_', ' ')} dimension.",
                estimated_minutes=20,
            ))
    return gaps


def generate_readiness_report(
    workspace: PrepWorkspaceRow,
    *,
    today=None,
    force_refresh: bool = False,
) -> PrepReadinessReport:
    """
    Generate a full readiness report for a workspace.

    This is the main orchestration function. All analysis is deterministic.
    """
    from datetime import date
    today = today or date.today()
    now = datetime.utcnow().isoformat()

    user_id = workspace.user_id
    resolution_id = workspace.resolution_id
    side = workspace.side

    # Load all library data
    data = _load_library_data(user_id, resolution_id, side)

    arguments = data["arguments"]
    blockfiles = data["blockfiles"]
    sections = data["sections"]
    entries = data["entries"]
    cards = data["cards"]
    frontlines = data["frontlines"]
    responses = data["responses"]

    # ── Resolution title ──────────────────────────────────────────────────────
    resolution_title: Optional[str] = None
    if resolution_id:
        try:
            res = get_supabase().table("resolutions").select("title").eq("id", resolution_id).limit(1).execute()
            if res.data:
                resolution_title = res.data[0].get("title")
        except Exception:
            pass

    # ── Freshness assessments ─────────────────────────────────────────────────
    cards_list = list(cards.values())
    freshness_assessments = assess_freshness_batch(cards_list, today=today)

    stale_card_ids = {
        a.card_id for a in freshness_assessments if freshness_needs_attention(a)
    }

    # ── Blockfile coverage ────────────────────────────────────────────────────
    all_coverage_results = []
    for bf in blockfiles:
        bf_sections = [s for s in sections if s.get("blockfile_id") == bf["id"]]
        coverage = analyze_blockfile_coverage(
            bf, bf_sections, entries, cards, frontlines, responses
        )
        for r in coverage:
            r.argument_id = None  # ensure no stale ref
        all_coverage_results.extend(coverage)

    # ── Frontline readiness ───────────────────────────────────────────────────
    responses_by_fl: dict[str, list[dict]] = {}
    for r in responses:
        fl_id = r.get("frontline_id", "")
        responses_by_fl.setdefault(fl_id, []).append(r)

    frontline_results = analyze_frontlines_batch(
        frontlines, responses_by_fl, cards, stale_card_ids=stale_card_ids
    )

    # ── Gap detection ─────────────────────────────────────────────────────────
    gaps: list[PrepGap] = []

    # Freshness gaps
    for assessment in freshness_assessments:
        if assessment.freshness_state == "stale":
            tag = assessment.card_tag or assessment.card_id[:8]
            gaps.append(PrepGap(
                gap_category="stale_evidence",
                severity="medium",
                title=f"Stale evidence: {tag[:60]}",
                reason=assessment.explanation,
                card_id=assessment.card_id,
                recommended_action="Find a more recent source or verify this claim remains accurate.",
                estimated_minutes=20,
            ))
        elif assessment.freshness_state == "freshness_unknown":
            tag = assessment.card_tag or assessment.card_id[:8]
            gaps.append(PrepGap(
                gap_category="freshness_unknown",
                severity="low",
                title=f"No date: {tag[:60]}",
                reason=assessment.explanation,
                card_id=assessment.card_id,
                recommended_action="Add a publication date to this card.",
                estimated_minutes=5,
            ))

    # Coverage gaps from blockfiles
    gaps.extend(_detect_coverage_gaps(all_coverage_results))

    # Frontline gaps
    gaps.extend(_detect_frontline_gaps(frontline_results))

    # Quality gaps
    gaps.extend(_detect_quality_gaps(cards))

    # Diversity gaps
    gaps.extend(_detect_diversity_gaps(cards))

    # ── Scoring ───────────────────────────────────────────────────────────────
    dimensions = score_dimensions(
        gaps=gaps,
        total_cards=len(cards),
        total_arguments=len(arguments),
        total_frontlines=len(frontlines),
        blockfile_coverage=all_coverage_results,
        freshness_assessments=freshness_assessments,
        frontline_results=frontline_results,
    )
    composite = compute_composite(dimensions)

    # ── Summary fields ────────────────────────────────────────────────────────
    critical_gaps = [g for g in gaps if g.severity in ("critical", "high")]
    stale_cards_list = [a for a in freshness_assessments if a.freshness_state == "stale"]
    unsafe_cards = [
        g.card_id for g in gaps
        if g.gap_category == "unsupported_card" and g.card_id
    ]

    # Strongest arguments: blockfile coverage >= 80%
    strongest = [
        r.section_title or r.section_id
        for r in all_coverage_results
        if r.coverage_pct >= 80.0 and r.section_title
    ][:3]

    # Weakest frontlines
    weakest_fl = [
        (r.frontline_title or r.frontline_id)
        for r in frontline_results
        if r.readiness_label in ("underdeveloped", "unsafe")
    ][:3]

    # Next actions
    next_actions: list[str] = []
    if critical_gaps:
        next_actions.append(critical_gaps[0].recommended_action or critical_gaps[0].title)
    if stale_cards_list:
        next_actions.append(f"Update {len(stale_cards_list)} stale card(s).")
    if not frontlines:
        next_actions.append("Add frontlines to your blockfile sections.")
    elif weakest_fl:
        next_actions.append(f"Develop frontline: {weakest_fl[0]}")
    next_actions = next_actions[:5]

    report = PrepReadinessReport(
        workspace_id=workspace.id,
        user_id=user_id,
        resolution_id=resolution_id,
        resolution_title=resolution_title,
        side=side,
        generated_at=now,
        tournament_date=workspace.tournament_date,
        dimensions=dimensions,
        composite_score=composite,
        gaps=gaps,
        critical_gaps=critical_gaps,
        stale_cards=stale_cards_list,
        unsafe_cards=unsafe_cards,
        strongest_arguments=strongest,
        weakest_frontlines=weakest_fl,
        blockfile_coverage=all_coverage_results,
        freshness_assessments=freshness_assessments,
        next_recommended_actions=next_actions,
        total_cards=len(cards),
        total_arguments=len(arguments),
        total_frontlines=len(frontlines),
        total_blockfiles=len(blockfiles),
    )

    return report
