"""Metadata enrichment for academic provider results.

Provides three independent, testable operations:

1. `normalize_doi`              — canonical bare DOI or None
2. `deduplicate_provider_results` — collapse by DOI then normalized title
3. `enrich_with_crossref`      — merge Crossref metadata without overwriting
4. `to_search_result_dict`     — convert ProviderResult → pipeline search-result dict

SAFETY INVARIANTS
- `body_text` / `abstract` from the original provider is never modified.
- Crossref enrichment NEVER overwrites a non-empty field with an empty value.
- Metadata-only records (no usable text) return None from to_search_result_dict.
- No credential fields are ever included in the output dict.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.evidence_provider_result import ProviderResult

logger = logging.getLogger(__name__)

_MIN_SNIPPET_LEN = 150   # abstract must be at least this long to be a snippet fallback
_SOURCE_PRIORITY_ACADEMIC = 2
_SOURCE_PRIORITY_PRIMARY = 3


# ── DOI normalization ─────────────────────────────────────────────────────────

def normalize_doi(doi_str: str | None) -> str | None:
    """Return a canonical bare DOI string (e.g. '10.1234/xyz') or None.

    Strips common URL prefixes and validates that the DOI starts with '10.'.
    """
    if not doi_str:
        return None
    doi = doi_str.strip()
    for prefix in (
        "https://doi.org/", "http://doi.org/",
        "doi.org/", "doi:",
    ):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi if doi.startswith("10.") else None


def _normalized_title(title: str) -> str:
    """Lowercase, punctuation-stripped title for dedup comparison."""
    return re.sub(r"[^\w]", "", title.lower())


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate_provider_results(
    results: list["ProviderResult"],
) -> tuple[list["ProviderResult"], int]:
    """Collapse duplicate records by DOI (first) then normalized title.

    When duplicates are found, the FIRST occurrence is kept (providers are
    called in priority order so the first occurrence is generally better).
    Returns (deduplicated_list, number_removed).
    """
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    kept: list["ProviderResult"] = []
    removed = 0

    for r in results:
        doi = normalize_doi(r.doi)
        if doi:
            if doi in seen_dois:
                removed += 1
                continue
            seen_dois.add(doi)
        else:
            ntitle = _normalized_title(r.title)
            if ntitle and ntitle in seen_titles:
                removed += 1
                continue
            if ntitle:
                seen_titles.add(ntitle)
        kept.append(r)

    return kept, removed


# ── Crossref enrichment ───────────────────────────────────────────────────────

def enrich_with_crossref(
    results: list["ProviderResult"],
    *,
    cache: dict[str, "ProviderResult | None"] | None = None,
    contact_email: str | None = None,
) -> tuple[list["ProviderResult"], int]:
    """Enrich provider results using Crossref metadata when a DOI is present.

    Rules:
    - Only records with a normalized DOI are enriched.
    - Each DOI is fetched once per call; subsequent results use the cache.
    - A field is enriched only when the Crossref value is non-empty AND the
      existing value is empty or None.
    - Abstract and open_access_url are NOT taken from Crossref (it has neither).
    - crossref_verified_fields records which fields were actually updated.

    Returns (enriched_results, total_enrichments_applied).
    """
    from app.services.providers.crossref import lookup_crossref_doi

    if cache is None:
        cache = {}

    enriched_count = 0

    for result in results:
        doi = normalize_doi(result.doi)
        if not doi:
            continue

        # Fetch from cache or network
        if doi not in cache:
            cache[doi] = lookup_crossref_doi(doi, contact_email=contact_email)

        cr = cache[doi]
        if cr is None:
            continue

        fields_updated: list[str] = []

        # Apply enrichment: never overwrite a non-empty value with empty
        if not result.title and cr.title:
            result.title = cr.title
            fields_updated.append("title")
        if not result.authors and cr.authors:
            result.authors = list(cr.authors)
            fields_updated.append("authors")
        if result.year is None and cr.year is not None:
            result.year = cr.year
            fields_updated.append("year")
        if not result.venue and cr.venue:
            result.venue = cr.venue
            fields_updated.append("venue")
        if not result.canonical_url and cr.canonical_url:
            result.canonical_url = cr.canonical_url
            fields_updated.append("canonical_url")
        if not result.landing_url and cr.landing_url:
            result.landing_url = cr.landing_url
            fields_updated.append("landing_url")

        if fields_updated:
            result.crossref_verified_fields = list(
                set(result.crossref_verified_fields) | set(fields_updated)
            )
            enriched_count += 1
            logger.debug("Crossref enriched DOI %s: %s", doi, fields_updated)

    return results, enriched_count


# ── Conversion to pipeline search-result dict ─────────────────────────────────

def to_search_result_dict(
    result: "ProviderResult",
    *,
    min_abstract_len: int = _MIN_SNIPPET_LEN,
) -> dict | None:
    """Convert a ProviderResult into a search-result dict for the existing pipeline.

    Returns None when the record has no usable URL AND no abstract long enough
    to serve as a snippet fallback (would contribute nothing to the pipeline).

    The returned dict is compatible with generate_candidate_cards():
    - 'url'           : preferred URL (open_access_url > landing_url > canonical)
    - 'content'       : abstract text (snippet fallback path)
    - '_provider'     : adapter name (shows up in providers_used diagnostics)
    - '_doi'          : normalized DOI for dedup checks
    - '_source_type'  : "academic" | "government" | "institutional"
    - '_is_academic'  : True
    - '_is_abstract'  : True when content derives from abstract only
    - '_source_priority': 3 for primary sources, 2 for academic/institutional
    - '_title'        : title for logging / diagnostics only (not card metadata)
    """
    doi = normalize_doi(result.doi)

    # Determine the best URL to hand to the extraction pipeline
    url = (
        result.open_access_url
        or result.landing_url
        or result.canonical_url
        or (f"https://doi.org/{doi}" if doi else "")
    )

    abstract = result.abstract or ""

    # Exclude metadata-only records that can't serve as snippet fallback.
    # is_metadata_only means the provider reports no accessible full text;
    # if the abstract is also too short, there is nothing usable for card cutting.
    if result.is_metadata_only and len(abstract) < min_abstract_len:
        return None

    # Records with no usable URL at all (including DOI-derived) cannot be extracted.
    if not url:
        return None

    priority = _SOURCE_PRIORITY_PRIMARY if result.is_primary else _SOURCE_PRIORITY_ACADEMIC

    return {
        "url": url,
        "content": abstract,                 # snippet fallback in generate_candidate_cards
        "_provider": result.provider,
        "_doi": doi,
        "_source_type": result.source_type,
        "_is_academic": True,
        "_is_abstract": result.is_abstract or (bool(abstract) and not result.open_access_url),
        "_source_priority": priority,
        "_title": result.title,              # diagnostics only
        "_crossref_enriched": bool(result.crossref_verified_fields),
    }
