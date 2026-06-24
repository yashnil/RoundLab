"""Trusted-source domain registry for evidence search.

Configuration-driven list of domains whose publications are generally credible
for debate evidence. Used by the source router and targeted search to generate
bounded domain-restricted queries.

IMPORTANT DISTINCTIONS
- Being in this registry establishes a CREDIBILITY PRIOR for the domain, not
  for any specific page. Relevance and claim support are always evaluated
  independently by the existing pipeline.
- Credibility tier affects the source quality gate in research_search.py.
  This registry does not bypass that gate.
- "is_primary" marks official government, court, or intergovernmental sources.
  Primary status raises source priority in ranking but does not skip validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceEntry:
    """One trusted domain entry in the registry."""
    domain: str
    category: str          # see _CATEGORIES below
    credibility_tier: str  # "high" | "medium"
    is_primary: bool       # True for official/authoritative primary sources
    query_hints: tuple[str, ...] = ()     # words that improve targeted searches
    site_restriction: str = ""            # prebuilt "site:domain.tld" fragment


_CATEGORIES = frozenset({
    "government_us",
    "court_legislative",
    "international_org",
    "university",
    "peer_reviewed",
    "research_institute",
})

_REGISTRY: list[SourceEntry] = [
    # ── United States government ─────────────────────────────────────────────
    SourceEntry("cdc.gov", "government_us", "high", True,
                ("health statistics", "disease", "public health"), "site:cdc.gov"),
    SourceEntry("census.gov", "government_us", "high", True,
                ("census data", "population", "demographics"), "site:census.gov"),
    SourceEntry("bls.gov", "government_us", "high", True,
                ("employment", "labor statistics", "wages"), "site:bls.gov"),
    SourceEntry("gao.gov", "government_us", "high", True,
                ("audit", "oversight", "report"), "site:gao.gov"),
    SourceEntry("whitehouse.gov", "government_us", "high", True,
                ("executive order", "policy"), "site:whitehouse.gov"),
    SourceEntry("justice.gov", "government_us", "high", True,
                ("crime", "law enforcement", "prosecution"), "site:justice.gov"),
    SourceEntry("hhs.gov", "government_us", "high", True,
                ("health", "public health", "social services"), "site:hhs.gov"),
    SourceEntry("epa.gov", "government_us", "high", True,
                ("environment", "pollution", "climate"), "site:epa.gov"),
    SourceEntry("nih.gov", "government_us", "high", True,
                ("health research", "medical study", "clinical"), "site:nih.gov"),
    SourceEntry("ftc.gov", "government_us", "high", True,
                ("consumer protection", "trade", "antitrust"), "site:ftc.gov"),
    SourceEntry("fbi.gov", "government_us", "high", True,
                ("crime statistics", "uniform crime report"), "site:fbi.gov"),
    SourceEntry("cbo.gov", "government_us", "high", True,
                ("budget", "economic analysis", "cost estimate"), "site:cbo.gov"),
    SourceEntry("dod.gov", "government_us", "high", True,
                ("defense", "military", "national security"), "site:defense.gov"),
    SourceEntry("state.gov", "government_us", "high", True,
                ("foreign policy", "diplomacy", "international"), "site:state.gov"),
    # ── Court and legislative ────────────────────────────────────────────────
    SourceEntry("congress.gov", "court_legislative", "high", True,
                ("legislation", "act", "bill", "hearing"), "site:congress.gov"),
    SourceEntry("supremecourt.gov", "court_legislative", "high", True,
                ("ruling", "decision", "opinion"), "site:supremecourt.gov"),
    SourceEntry("govinfo.gov", "court_legislative", "high", True,
                ("federal register", "CFR", "code of federal regulations"), "site:govinfo.gov"),
    # ── International organizations ──────────────────────────────────────────
    SourceEntry("un.org", "international_org", "high", True,
                ("report", "resolution", "data"), "site:un.org"),
    SourceEntry("who.int", "international_org", "high", True,
                ("health", "global health", "report"), "site:who.int"),
    SourceEntry("worldbank.org", "international_org", "high", True,
                ("data", "development", "poverty"), "site:worldbank.org"),
    SourceEntry("imf.org", "international_org", "high", True,
                ("economic", "fiscal", "monetary"), "site:imf.org"),
    SourceEntry("oecd.org", "international_org", "high", False,
                ("report", "statistics", "analysis"), "site:oecd.org"),
    SourceEntry("amnesty.org", "international_org", "medium", False,
                ("human rights", "report"), "site:amnesty.org"),
    # ── Research institutes ──────────────────────────────────────────────────
    SourceEntry("rand.org", "research_institute", "high", False,
                ("study", "report", "analysis"), "site:rand.org"),
    SourceEntry("brookings.edu", "research_institute", "high", False,
                ("policy", "analysis", "report"), "site:brookings.edu"),
    SourceEntry("pewresearch.org", "research_institute", "high", False,
                ("survey", "data", "research"), "site:pewresearch.org"),
    SourceEntry("cfr.org", "research_institute", "high", False,
                ("foreign policy", "analysis"), "site:cfr.org"),
    SourceEntry("urban.org", "research_institute", "high", False,
                ("policy", "social", "research"), "site:urban.org"),
    SourceEntry("cato.org", "research_institute", "medium", False,
                ("policy", "analysis"), "site:cato.org"),
    SourceEntry("heritage.org", "research_institute", "medium", False,
                ("policy", "report"), "site:heritage.org"),
    SourceEntry("americanprogress.org", "research_institute", "medium", False,
                ("policy", "report"), "site:americanprogress.org"),
    # ── Peer-reviewed publishers ─────────────────────────────────────────────
    SourceEntry("ncbi.nlm.nih.gov", "peer_reviewed", "high", False,
                ("study", "clinical", "research"), "site:ncbi.nlm.nih.gov"),
    SourceEntry("pubmed.ncbi.nlm.nih.gov", "peer_reviewed", "high", False,
                ("study", "trial", "research"), "site:pubmed.ncbi.nlm.nih.gov"),
    SourceEntry("nature.com", "peer_reviewed", "high", False,
                ("research", "study", "findings"), "site:nature.com"),
    SourceEntry("science.org", "peer_reviewed", "high", False,
                ("research", "study"), "site:science.org"),
    SourceEntry("jstor.org", "peer_reviewed", "high", False,
                ("journal", "article"), "site:jstor.org"),
    SourceEntry("journals.plos.org", "peer_reviewed", "high", False,
                ("open access", "study"), "site:journals.plos.org"),
]


def get_all_entries() -> list[SourceEntry]:
    """Return all registry entries."""
    return list(_REGISTRY)


def get_entries_by_category(category: str) -> list[SourceEntry]:
    """Return registry entries for a specific category."""
    return [e for e in _REGISTRY if e.category == category]


def get_high_credibility_entries() -> list[SourceEntry]:
    """Return entries with credibility_tier='high'."""
    return [e for e in _REGISTRY if e.credibility_tier == "high"]


def get_primary_sources() -> list[SourceEntry]:
    """Return entries where is_primary=True."""
    return [e for e in _REGISTRY if e.is_primary]


def get_domain_credibility(domain: str) -> tuple[str, bool]:
    """Return (credibility_tier, is_primary) for a domain.

    Returns ('unknown', False) when domain is not in the registry.
    Matches 'sub.domain.tld' against 'domain.tld' registry entries.
    """
    norm = domain.lower().lstrip("www.")
    for entry in _REGISTRY:
        if norm == entry.domain or norm.endswith("." + entry.domain):
            return entry.credibility_tier, entry.is_primary
    return "unknown", False


def build_site_queries(
    base_queries: list[str],
    categories: list[str],
    max_queries: int = 3,
) -> list[str]:
    """Generate site-restricted query strings for the given registry categories.

    Takes the first base query and combines it with the site_restriction of
    the most authoritative matching registry entries. Bounds output to
    max_queries total results.
    """
    if not base_queries:
        return []
    base = base_queries[0]
    entries = [
        e for e in _REGISTRY
        if e.category in categories and e.site_restriction and e.credibility_tier == "high"
    ]
    # Prefer primary sources first
    entries.sort(key=lambda e: (not e.is_primary, e.domain))
    result: list[str] = []
    for entry in entries[:max_queries]:
        result.append(f"{base} {entry.site_restriction}")
    return result
