"""Semantic Scholar academic search adapter.

Semantic Scholar (https://www.semanticscholar.org) provides free API access.
An optional API key increases rate limits from 100 req/5min to 1 req/sec.
See https://api.semanticscholar.org for details.

SAFETY INVARIANTS
- Abstracts are exact source text from Semantic Scholar; never synthesized.
- API key never appears in returned ProviderResult fields.
- Malformed records are skipped without crashing.
- Network timeout is bounded. A timeout returns [].
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_TIMEOUT = 8.0
_DEFAULT_MAX = 5
_FIELDS = (
    "title,abstract,authors,year,externalIds,"
    "citationCount,openAccessPdf,publicationVenue,isOpenAccess"
)


def _normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    doi = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "doi.org/"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi if doi.startswith("10.") else None


def _parse_record(record: dict[str, Any], query: str, evidence_role: str) -> "ProviderResult | None":
    """Parse one Semantic Scholar paper record into a ProviderResult."""
    from app.services.evidence_provider_result import ProviderResult

    try:
        title = record.get("title") or ""
        if not title:
            return None

        abstract = (record.get("abstract") or "").strip()

        authors: list[str] = []
        for a in (record.get("authors") or [])[:5]:
            if not isinstance(a, dict):
                continue
            name = a.get("name", "")
            if name:
                authors.append(name)

        year: int | None = record.get("year")
        if year and not isinstance(year, int):
            try:
                year = int(year)
            except (TypeError, ValueError):
                year = None

        external_ids = record.get("externalIds") or {}
        doi = _normalize_doi(external_ids.get("DOI"))
        canonical_url = f"https://doi.org/{doi}" if doi else ""

        # Build landing URL: prefer DOI URL, fallback to S2 paper page
        paper_id = record.get("paperId") or ""
        landing_url = canonical_url or (
            f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""
        )

        # Open access URL
        oa_pdf = record.get("openAccessPdf") or {}
        oa_url: str | None = oa_pdf.get("url") or None

        citation_count: int | None = record.get("citationCount")

        venue_data = record.get("publicationVenue") or {}
        venue = venue_data.get("name") or ""

        is_abstract = bool(abstract) and not bool(oa_url)
        is_metadata_only = not bool(abstract) and not bool(oa_url)

        return ProviderResult(
            provider="semantic_scholar",
            provider_id=paper_id,
            title=title,
            abstract=abstract,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            canonical_url=canonical_url,
            landing_url=landing_url,
            open_access_url=oa_url,
            citation_count=citation_count,
            source_type="academic",
            is_primary=False,
            is_metadata_only=is_metadata_only,
            is_abstract=is_abstract,
            query=query,
            evidence_role=evidence_role,
        )
    except Exception as exc:
        logger.debug("Semantic Scholar record parse error (skipping): %s", exc)
        return None


def search_semantic_scholar(
    query: str,
    *,
    api_key: str | None = None,
    max_results: int = _DEFAULT_MAX,
    evidence_role: str = "",
) -> list["ProviderResult"]:
    """Search Semantic Scholar for papers matching the query.

    Returns up to max_results ProviderResult objects. Returns [] on failure.
    api_key is used only for auth header; never stored in ProviderResult.
    """
    try:
        import httpx
    except ImportError:
        logger.debug("httpx not installed; Semantic Scholar unavailable")
        return []

    params: dict[str, str | int] = {
        "query": query,
        "limit": min(max_results, 10),
        "fields": _FIELDS,
    }

    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key  # key stays in headers; never in result

    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            response = client.get(_BASE_URL, params=params, headers=headers)
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limited (429)")
                return []
            if response.status_code != 200:
                logger.warning("Semantic Scholar returned HTTP %d", response.status_code)
                return []
            data = response.json()
    except Exception as exc:
        logger.warning("Semantic Scholar request failed: %s", type(exc).__name__)
        return []

    results: list[ProviderResult] = []
    for record in (data.get("data") or []):
        parsed = _parse_record(record, query, evidence_role)
        if parsed is not None:
            results.append(parsed)
        if len(results) >= max_results:
            break

    return results
