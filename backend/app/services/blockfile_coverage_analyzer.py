"""Pass 14 — Blockfile Coverage Analysis.

Inspects blockfile sections and their entries to produce a coverage matrix.

Design:
- argument_type-aware: contentions need more components than responses
- never assumes every argument needs every component
- all logic is deterministic and testable without a DB
- coverage matrix links back to card_ids that satisfy each dimension

Public interface:
    analyze_blockfile_coverage(blockfile, sections, entries, cards) -> list[BlockfileCoverageResult]
"""

from __future__ import annotations

import re
from typing import Optional

from app.models.tournament_prep import (
    BlockfileCoverageResult,
    CoverageDimension,
    CoverageState,
    GapCategory,
)

# ── Dimension definitions by argument type ────────────────────────────────────

# For each argument type, which dimensions are applicable?
# "required" → missing = gap; "optional" → missing = info-only

_CONTENTION_DIMENSIONS: list[tuple[str, bool]] = [
    ("claim", True),
    ("uniqueness", False),      # not always needed in PF contentions
    ("link", False),
    ("internal_link", False),
    ("warrant", True),
    ("impact", True),
    ("magnitude", False),
    ("probability", False),
    ("timeframe", False),
    ("weighing", False),
    ("primary_source", False),
    ("summary_extension", False),
    ("final_focus_extension", False),
]

_RESPONSE_DIMENSIONS: list[tuple[str, bool]] = [
    ("response_claim", True),
    ("explanation", False),
    ("supporting_evidence", False),
    ("response_type", True),
    ("speech_suitability", False),
    ("offensive_option", False),   # turn or counterplan
    ("defensive_coverage", False),
]

_FRAMEWORK_DIMENSIONS: list[tuple[str, bool]] = [
    ("value_criterion", True),
    ("warrant", True),
    ("link_to_resolution", False),
    ("evidence_support", False),
]

_DEFAULT_DIMENSIONS: list[tuple[str, bool]] = [
    ("claim", True),
    ("warrant", False),
    ("evidence_support", False),
]

# Section type → argument role mapping
_SECTION_TO_ROLE: dict[str, str] = {
    "constructive": "contention",
    "contention": "contention",
    "uniqueness": "contention",
    "link": "contention",
    "internal_link": "contention",
    "impact": "contention",
    "responses": "response",
    "frontlines": "response",
    "turns": "response",
    "defense": "response",
    "framework": "framework",
    "weighing": "general",
    "extensions": "general",
    "crossfire": "general",
    "definitions": "general",
    "miscellaneous": "general",
}

# Keywords that satisfy each dimension
_DIM_KEYWORDS: dict[str, list[str]] = {
    "claim": ["claim", "contends", "argues", "demonstrates", "shows", "proves"],
    "warrant": ["because", "since", "therefore", "thus", "explains", "mechanism",
                "logic", "reason", "causally", "leads to", "results in"],
    "impact": ["impact", "harm", "benefit", "consequence", "result", "therefore",
               "ultimately", "lives", "people", "economy", "security"],
    "uniqueness": ["unique", "uniqueness", "status quo", "already", "baseline",
                   "currently", "now ", "today", "without the plan"],
    "link": ["link", "links to", "causes", "leads to", "triggers", "because of",
             "due to", "drives"],
    "internal_link": ["internal link", "internallink", "bridge", "internal"],
    "weighing": ["outweigh", "magnitude", "probability", "timeframe", "reversibility",
                 "scope", "breadth", "compared to", "more important"],
    "magnitude": ["million", "billion", "percent", "%", "thousands", "deaths",
                  "people affected", "large scale"],
    "probability": ["likely", "probability", "chance", "risk", "inevitably",
                    "certainly", "almost certainly"],
    "timeframe": ["immediate", "short.term", "long.term", "years", "decades",
                  "months", "quickly", "soon", "eventually"],
    "primary_source": ["journal", "peer.reviewed", "study", "research", "data",
                       "survey", "report", "published"],
    "summary_extension": ["extend", "summary extension", "across all speeches"],
    "final_focus_extension": ["final focus", "voter", "voting issue", "win the round"],
    # Response dimensions
    "response_claim": ["no link", "doesn't link", "doesn't apply", "turn", "mitigate",
                       "outweigh", "uniqueness", "non-unique"],
    "explanation": ["because", "since", "the reason", "this matters", "specifically"],
    "supporting_evidence": [],       # presence of entry cards is enough
    "response_type": [],             # checked via frontline response_type field
    "speech_suitability": [],        # checked via frontline metadata
    "offensive_option": ["turn", "double turn", "proves our side"],
    "defensive_coverage": ["defense", "defend", "mitigate", "block"],
    # Framework
    "value_criterion": ["value", "criterion", "standard", "judge"],
    "link_to_resolution": ["resolution", "topic", "policy", "plan"],
    "evidence_support": [],          # presence of entries
}


def _card_satisfies_dim(card: dict, dimension: str) -> bool:
    """Check if a card's tag or body satisfies a dimension using keyword heuristics."""
    if dimension in ("supporting_evidence", "response_type", "speech_suitability",
                     "evidence_support"):
        return True  # presence of the card is enough

    text = f"{card.get('tag', '')} {card.get('body_text', '')}".lower()
    keywords = _DIM_KEYWORDS.get(dimension, [])
    if not keywords:
        return bool(text.strip())
    return any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords)


def _get_dimensions_for_role(role: str) -> list[tuple[str, bool]]:
    if role == "contention":
        return _CONTENTION_DIMENSIONS
    if role == "response":
        return _RESPONSE_DIMENSIONS
    if role == "framework":
        return _FRAMEWORK_DIMENSIONS
    return _DEFAULT_DIMENSIONS


def _analyze_section(
    section: dict,
    entries: list[dict],
    cards: dict[str, dict],  # card_id → card dict
    frontlines: list[dict],
    responses: list[dict],
) -> BlockfileCoverageResult:
    """Analyze one section and return its coverage result."""
    section_id: str = section.get("id", "")
    section_title: str = section.get("title", "")
    section_type: str = section.get("section_type", "miscellaneous")
    role = _SECTION_TO_ROLE.get(section_type, "general")

    dimension_defs = _get_dimensions_for_role(role)
    section_cards = [
        cards[e["card_id"]]
        for e in entries
        if e.get("section_id") == section_id and e.get("card_id") in cards
    ]
    section_frontlines = [f for f in frontlines if f.get("section_id") == section_id]
    section_responses: list[dict] = []
    for fl in section_frontlines:
        section_responses.extend(
            r for r in responses if r.get("frontline_id") == fl.get("id")
        )

    dimensions: list[CoverageDimension] = []
    gaps: list[str] = []
    covered = 0
    total_applicable = 0

    for dim_name, is_required in dimension_defs:
        satisfying: list[str] = []

        # Check via frontline responses for response-role dimensions
        if dim_name == "response_type":
            if section_responses:
                satisfying = [r["id"] for r in section_responses[:3]]
        elif dim_name == "speech_suitability":
            suitable = [
                r["id"] for r in section_responses
                if r.get("speech_suitability") and len(r.get("speech_suitability", [])) > 0
            ]
            satisfying = suitable[:3]
        elif dim_name == "offensive_option":
            offensive = [
                r["id"] for r in section_responses
                if r.get("response_type") in ("turn", "counterplan")
            ]
            satisfying = offensive[:2]
        elif dim_name == "defensive_coverage":
            defensive = [
                r["id"] for r in section_responses
                if r.get("response_type") in (
                    "no_link", "link_defense", "impact_defense",
                    "uniqueness_takeout", "mitigation", "non_unique",
                )
            ]
            satisfying = defensive[:2]
        elif dim_name == "supporting_evidence":
            satisfying = [c["id"] for c in section_cards[:3]]
        elif dim_name == "evidence_support":
            satisfying = [c["id"] for c in section_cards[:3]]
        else:
            satisfying = [c["id"] for c in section_cards if _card_satisfies_dim(c, dim_name)]

        # Determine coverage state
        if satisfying:
            state: CoverageState = "covered"
            covered += 1
        elif not is_required:
            # Check if this dimension is truly not applicable
            if role == "response" and dim_name in ("magnitude", "probability", "timeframe"):
                state = "not_applicable"
            elif role == "contention" and dim_name in ("response_type", "speech_suitability"):
                state = "not_applicable"
            else:
                state = "missing"
                gaps.append(f"missing_{dim_name.replace(' ', '_')}")
        else:
            state = "missing"
            gaps.append(f"missing_{dim_name.replace(' ', '_')}")

        # Count only applicable dimensions
        if state != "not_applicable":
            total_applicable += 1

        dimensions.append(CoverageDimension(
            dimension=dim_name,
            state=state,
            evidence=satisfying,
        ))

    coverage_pct = (covered / total_applicable * 100) if total_applicable > 0 else 0.0

    return BlockfileCoverageResult(
        section_id=section_id,
        section_title=section_title,
        argument_type=role,
        dimensions=dimensions,
        covered_count=covered,
        total_applicable_count=total_applicable,
        coverage_pct=round(coverage_pct, 1),
        gaps=gaps,
    )


def analyze_blockfile_coverage(
    blockfile: dict,
    sections: list[dict],
    entries: list[dict],
    cards: dict[str, dict],
    frontlines: Optional[list[dict]] = None,
    responses: Optional[list[dict]] = None,
) -> list[BlockfileCoverageResult]:
    """
    Analyze coverage for all sections in a blockfile.

    Args:
        blockfile: blockfile row dict
        sections: list of section row dicts for this blockfile
        entries: list of entry row dicts (all entries across sections)
        cards: mapping from card_id → card dict
        frontlines: list of frontline row dicts
        responses: list of frontline_response row dicts

    Returns:
        list of BlockfileCoverageResult, one per top-level section
    """
    frontlines = frontlines or []
    responses = responses or []
    results: list[BlockfileCoverageResult] = []

    # Only analyze top-level sections (parent_section_id is None)
    top_sections = [s for s in sections if not s.get("parent_section_id")]

    for section in sorted(top_sections, key=lambda s: s.get("position", 0)):
        result = _analyze_section(section, entries, cards, frontlines, responses)
        results.append(result)

    return results


def summarize_coverage_gaps(results: list[BlockfileCoverageResult]) -> list[str]:
    """Return deduplicated list of gap categories across all sections."""
    seen: set[str] = set()
    gaps: list[str] = []
    for r in results:
        for g in r.gaps:
            if g not in seen:
                seen.add(g)
                gaps.append(g)
    return gaps
