"""Academic and primary-source evidence search orchestration (Pass 9).

Orchestrates the Pass 9 source-routing → provider search → normalization →
deduplication → Crossref enrichment → conversion pipeline.

Integration point: called from api/research.py after the Tavily/Exa supplement
to add academic and primary-source results to the all_results pool.

SAFETY INVARIANTS
- Only results with a usable URL or sufficiently long abstract are returned.
- Metadata-only records (no abstract ≥ 150 chars and no URL) are excluded.
- Counter-evidence role queries are routed to 'counterevidence' lane only
  and do not trigger academic provider calls.
- Provider failures never crash the caller — empty list is returned.
- `seen_urls` deduplication prevents academic results from duplicating
  URLs already retrieved via Tavily/Exa.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DEFAULT_MAX_PER_PROVIDER = 3
_MIN_ABSTRACT_LEN = 150


def gather_academic_results(
    queries: list[str],
    *,
    semantic_scholar_key: str | None = None,
    openalex_email: str | None = None,
    max_per_provider: int = _DEFAULT_MAX_PER_PROVIDER,
    seen_urls: set[str] | None = None,
    evidence_roles: list[str] | None = None,
) -> tuple[list[dict], "P9SearchMeta"]:
    """Search academic providers and return pipeline-compatible search-result dicts.

    Steps:
    1. Route each query to source lanes via evidence_source_router.
    2. For queries in 'academic_research' lane: call OpenAlex + Semantic Scholar.
    3. Collect all ProviderResult objects.
    4. Deduplicate by DOI then normalized title.
    5. Enrich with Crossref (per-request DOI cache).
    6. Exclude metadata-only records without usable text.
    7. Convert survivors to pipeline search-result dicts.
    8. Deduplicate against seen_urls.
    9. Return (dicts, P9SearchMeta).

    Returns ([], P9SearchMeta()) on complete failure — never raises.
    """
    from app.services.evidence_provider_result import P9SearchMeta
    from app.services.evidence_source_router import route_queries, aggregate_lanes
    from app.services.evidence_metadata_enricher import (
        deduplicate_provider_results,
        enrich_with_crossref,
        normalize_doi,
        to_search_result_dict,
    )
    from app.services.providers.openalex import search_openalex
    from app.services.providers.semantic_scholar import search_semantic_scholar

    meta = P9SearchMeta()

    if not queries:
        return [], meta

    _seen = seen_urls if seen_urls is not None else set()
    roles = evidence_roles or []

    # ── 1. Route queries ──────────────────────────────────────────────────────
    routing = route_queries(queries, roles)
    all_lanes = aggregate_lanes(routing)
    meta.lanes_selected = sorted(all_lanes)

    if "academic_research" not in all_lanes:
        return [], meta

    # Queries that should hit academic providers
    academic_queries = [q for q, lanes in routing.items() if "academic_research" in lanes]

    # ── 2. Call providers ─────────────────────────────────────────────────────
    all_provider_results: list = []

    for q in academic_queries[:3]:  # bound: at most 3 queries per provider set
        role_idx = queries.index(q) if q in queries else 0
        role = roles[role_idx] if role_idx < len(roles) else ""

        # OpenAlex
        meta.providers_attempted += 1
        try:
            oa_results = search_openalex(
                q,
                contact_email=openalex_email,
                max_results=max_per_provider,
                evidence_role=role,
            )
            all_provider_results.extend(oa_results)
            meta.academic_found += len(oa_results)
        except Exception as exc:
            logger.warning("OpenAlex call failed for query '%s': %s", q[:60], exc)
            meta.provider_failures.append(f"openalex: {type(exc).__name__}")

        # Semantic Scholar
        meta.providers_attempted += 1
        try:
            ss_results = search_semantic_scholar(
                q,
                api_key=semantic_scholar_key,
                max_results=max_per_provider,
                evidence_role=role,
            )
            all_provider_results.extend(ss_results)
            meta.academic_found += len(ss_results)
        except Exception as exc:
            logger.warning("Semantic Scholar call failed for query '%s': %s", q[:60], exc)
            meta.provider_failures.append(f"semantic_scholar: {type(exc).__name__}")

    if not all_provider_results:
        return [], meta

    # ── 3-4. Deduplicate by DOI then title ───────────────────────────────────
    deduped, doi_removed = deduplicate_provider_results(all_provider_results)
    meta.doi_matches_found = doi_removed

    # ── 5. Crossref enrichment (per-request cache) ────────────────────────────
    doi_cache: dict = {}
    deduped, crossref_count = enrich_with_crossref(
        deduped,
        cache=doi_cache,
        contact_email=openalex_email,
    )
    meta.crossref_enrichments = crossref_count

    # ── 6-7. Convert to pipeline dicts, exclude metadata-only ────────────────
    result_dicts: list[dict] = []
    source_dist: dict[str, int] = {}

    for r in deduped:
        d = to_search_result_dict(r, min_abstract_len=_MIN_ABSTRACT_LEN)
        if d is None:
            meta.metadata_only_excluded += 1
            continue
        if r.is_primary:
            meta.primary_source_candidates += 1
        stype = r.source_type or "academic"
        source_dist[stype] = source_dist.get(stype, 0) + 1
        result_dicts.append(d)

    meta.source_type_distribution = source_dist

    # ── 8. Dedup against seen_urls ────────────────────────────────────────────
    from app.services.research_search import canonicalize_url

    final: list[dict] = []
    new_doi_seen: set[str] = set()

    # Extract DOIs from already-seen URLs (doi.org links from Tavily/Exa)
    seen_dois: set[str] = set()
    for canonical in _seen:
        if "doi.org/" in canonical:
            d = canonical.split("doi.org/")[-1].rstrip("/").lower()
            if d.startswith("10."):
                seen_dois.add(d)

    for d in result_dicts:
        url = d.get("url", "")
        doi = d.get("_doi", "") or ""
        if not url:
            continue

        # DOI-based dedup with existing results
        if doi and doi.lower() in seen_dois:
            continue
        if doi and doi.lower() in new_doi_seen:
            continue

        c = canonicalize_url(url)
        if c in _seen:
            continue

        final.append(d)
        if doi:
            new_doi_seen.add(doi.lower())
            seen_dois.add(doi.lower())
        # Note: we do NOT add to _seen here; caller does that

    # ── 9. Build summary ─────────────────────────────────────────────────────
    parts: list[str] = []
    if "academic_research" in all_lanes:
        parts.append("Searched academic indexes")
    if "government_primary" in all_lanes:
        parts.append("government sources")
    if "institutional_report" in all_lanes:
        parts.append("research institutes")
    if parts:
        meta.specialized_summary = (
            f"{', '.join(parts)}."
            + (f" Found {len(final)} unique academic record(s)." if final else
               " No accessible passages found.")
        )

    return final, meta
