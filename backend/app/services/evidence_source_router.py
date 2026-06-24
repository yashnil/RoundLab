"""Deterministic source router for evidence queries.

Classifies each query into one or more source lanes based on evidence role
and keyword signals in the query text. No LLM calls; all routing rules are
explicit keyword-matching.

Source lanes
  general_web          — standard Tavily/Exa web search (always included)
  academic_research    — OpenAlex + Semantic Scholar academic indexes
  government_primary   — registry-targeted site: queries for gov/org sources
  institutional_report — registry-targeted queries for think tanks / institutes
  counterevidence      — counter-argument role queries only

Design constraints
- Max 3 lanes per query (general_web + 2 specialized) to bound search cost.
- Each specialized lane is ADDITIVE — general_web is always included.
- counter-evidence role gets ONLY counterevidence + general_web; no academic.
- All routing is deterministic: same query + role → same lanes always.
"""

from __future__ import annotations

import re

# ── Keyword signal sets ───────────────────────────────────────────────────────

_ACADEMIC_SINGLE = frozenset({
    "study", "studies", "research", "experiment", "trial", "evidence",
    "meta-analysis", "randomized", "controlled", "clinical", "epidemiology",
    "epidemiolog", "published", "journal", "findings", "statistic",
    "statistics", "correlat", "association", "causal", "causation",
})

# Multi-word signals (checked via substring match on lowercased query)
_ACADEMIC_PHRASES = (
    "meta-analysis", "meta analysis", "systematic review",
    "associated with", "association between", "effect of", "impact of",
    "causes ", "correlated with", "data show", "evidence shows",
    "peer-reviewed", "peer reviewed", "law review",
)

_GOVERNMENT_SINGLE = frozenset({
    "government", "federal", "census", "cdc", "fda", "epa", "gao", "nih",
    "official", "policy", "legislation", "congress", "court", "ruling",
    "statute", "regulation", "national", "bureau",
})

_GOVERNMENT_PHRASES = (
    "crime rate", "crime statistics", "law enforcement",
    "public health", "national data", "government data",
    "court decision", "supreme court",
)

_INSTITUTIONAL_SINGLE = frozenset({
    "report", "survey", "institute", "brookings", "rand", "pew",
    "gallup", "think tank",
})

_INSTITUTIONAL_PHRASES = (
    "policy analysis", "policy report", "industry data",
    "industry report", "white paper",
)

# Evidence roles that strongly suggest academic sources
_ACADEMIC_ROLES = frozenset({
    "causal_mechanism", "impact", "credible_source",
    "mechanism_support", "impact_support", "authority_support",
})

# Counter-evidence roles
_COUNTER_ROLES = frozenset({
    "counter_argument", "counter_evidence", "counterevidence",
})


def _tokens(query: str) -> frozenset[str]:
    """Return lowercase word tokens from the query."""
    return frozenset(re.sub(r"[^\w\s]", " ", query.lower()).split())


def route_query(query: str, evidence_role: str = "") -> list[str]:
    """Return the ordered list of source lanes for one query.

    Always returns 'general_web'. Counter-evidence role gets only
    ['counterevidence', 'general_web'] and no academic/government lanes.
    Specialized lanes are appended in priority order (academic > government >
    institutional) with a hard cap of 2 specialized lanes per query.
    """
    if evidence_role in _COUNTER_ROLES:
        return ["counterevidence", "general_web"]

    lanes: list[str] = ["general_web"]
    ql = query.lower()
    toks = _tokens(query)

    # ── Academic lane ─────────────────────────────────────────────────────────
    academic = bool(toks & _ACADEMIC_SINGLE)
    if not academic:
        academic = any(ph in ql for ph in _ACADEMIC_PHRASES)
    if not academic:
        academic = evidence_role in _ACADEMIC_ROLES
    if academic:
        lanes.append("academic_research")

    # ── Government/primary lane ───────────────────────────────────────────────
    gov = bool(toks & _GOVERNMENT_SINGLE)
    if not gov:
        gov = any(ph in ql for ph in _GOVERNMENT_PHRASES)
    if gov:
        lanes.append("government_primary")

    # ── Institutional lane (only when academic lane not already selected) ─────
    if "academic_research" not in lanes:
        inst = bool(toks & _INSTITUTIONAL_SINGLE)
        if not inst:
            inst = any(ph in ql for ph in _INSTITUTIONAL_PHRASES)
        if inst:
            lanes.append("institutional_report")

    # Cap at general_web + 2 specialized
    return lanes[:3]


def route_queries(
    queries: list[str],
    evidence_roles: list[str] | None = None,
) -> dict[str, list[str]]:
    """Route multiple queries, returning a mapping from query → lanes.

    evidence_roles, when provided, must align positionally with queries.
    """
    roles = evidence_roles or []
    return {
        q: route_query(q, roles[i] if i < len(roles) else "")
        for i, q in enumerate(queries)
    }


def aggregate_lanes(routing: dict[str, list[str]]) -> set[str]:
    """Return the union of all source lanes across all queries."""
    result: set[str] = set()
    for lane_list in routing.values():
        result.update(lane_list)
    return result
