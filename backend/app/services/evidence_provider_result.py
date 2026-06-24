"""Normalized provider result model for academic and institutional adapters.

All adapters (OpenAlex, Semantic Scholar, Crossref) normalize their raw API
responses into ProviderResult before returning. Provider-specific shapes never
escape adapter boundaries.

SAFETY INVARIANTS
- `abstract` is always exact source text from the provider — never synthesized.
- `is_metadata_only=True` when no usable full text is available. Such records
  may enrich citation metadata but must never become evidence cards.
- Credentials, API keys, and authorization headers never enter ProviderResult fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderResult:
    """Normalized result from an academic or institutional search adapter."""

    # Required — which adapter produced this
    provider: str  # "openalex" | "semantic_scholar" | "crossref"

    # Bibliographic identity
    provider_id: str = ""
    title: str = ""
    abstract: str = ""           # exact abstract text from the source; never synthesized
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: str = ""              # journal name or publisher

    # DOI — normalized to bare form, e.g. "10.1234/xyz" (no prefix)
    doi: Optional[str] = None

    # URLs
    canonical_url: str = ""      # doi.org/… when DOI is available
    landing_url: str = ""        # provider landing page
    open_access_url: Optional[str] = None  # direct full-text URL when available

    # Metadata signals
    citation_count: Optional[int] = None
    source_type: str = "academic"   # "academic" | "government" | "institutional" | "web"
    is_primary: bool = False         # True for official government/primary sources
    is_metadata_only: bool = False   # True when only bibliographic metadata available
    is_abstract: bool = False        # True when usable text is abstract-only

    # Search provenance (never contains API keys or credentials)
    query: str = ""
    evidence_role: str = ""
    raw_score: Optional[float] = None

    # Crossref enrichment tracking
    crossref_verified_fields: list[str] = field(default_factory=list)


@dataclass
class P9SearchMeta:
    """Trace metadata collected during the Pass 9 academic search step.

    Consumed by build_search_trace() to populate P9-specific trace fields.
    """
    lanes_selected: list[str] = field(default_factory=list)
    providers_attempted: int = 0
    academic_found: int = 0
    doi_matches_found: int = 0
    crossref_enrichments: int = 0
    metadata_only_excluded: int = 0
    primary_source_candidates: int = 0
    trusted_domain_searches: int = 0
    provider_failures: list[str] = field(default_factory=list)
    source_type_distribution: dict[str, int] = field(default_factory=dict)
    specialized_summary: str = ""
