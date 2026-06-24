"""OpenAlex academic search adapter.

OpenAlex (https://openalex.org) is a free, open scholarly index.
No API key required; a contact email enables the 'polite pool' with higher
rate limits. See https://docs.openalex.org for API details.

SAFETY INVARIANTS
- Abstracts are exact text reconstructed from OpenAlex inverted index;
  no words are added or changed.
- API key / email / credentials never appear in returned ProviderResult fields.
- Malformed or incomplete records are skipped, never crash the caller.
- Network timeout is bounded (TIMEOUT_SECONDS). A timeout returns [].
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openalex.org/works"
_TIMEOUT = 8.0
_DEFAULT_MAX = 5
_SELECT_FIELDS = (
    "id,title,abstract_inverted_index,authorships,"
    "publication_date,doi,primary_location,cited_by_count,open_access"
)


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Rebuild abstract text from OpenAlex inverted index.

    OpenAlex stores abstracts as a mapping of word → list of positions.
    Reconstruction inserts each word at its recorded position.
    """
    if not inverted_index:
        return ""
    try:
        pos_map: dict[int, str] = {}
        for word, positions in inverted_index.items():
            for p in positions:
                if isinstance(p, int) and p >= 0:
                    pos_map[p] = word
        if not pos_map:
            return ""
        max_pos = max(pos_map)
        return " ".join(pos_map.get(i, "") for i in range(max_pos + 1)).strip()
    except Exception:
        return ""


def _normalize_doi(raw: str | None) -> str | None:
    """Strip DOI URL prefix, returning bare '10.xxxx/...' or None."""
    if not raw:
        return None
    doi = raw.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "doi.org/"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi if doi.startswith("10.") else None


def _parse_record(record: dict[str, Any], query: str, evidence_role: str) -> "ProviderResult | None":
    """Parse one OpenAlex work record into a ProviderResult.

    Returns None when the record lacks enough usable data.
    """
    from app.services.evidence_provider_result import ProviderResult

    try:
        title = record.get("title") or ""
        if not title:
            return None

        abstract = _reconstruct_abstract(record.get("abstract_inverted_index"))

        authors: list[str] = []
        for a in (record.get("authorships") or [])[:5]:
            name = (a.get("author") or {}).get("display_name", "")
            if name:
                authors.append(name)

        pub_date = record.get("publication_date") or ""
        year: int | None = None
        if pub_date and len(pub_date) >= 4:
            try:
                year = int(pub_date[:4])
            except ValueError:
                pass

        doi = _normalize_doi(record.get("doi"))
        canonical_url = f"https://doi.org/{doi}" if doi else ""

        primary_loc = record.get("primary_location") or {}
        landing_url = primary_loc.get("landing_page_url") or canonical_url

        open_access = record.get("open_access") or {}
        oa_url: str | None = None
        if open_access.get("is_oa"):
            oa_url = open_access.get("oa_url") or None
        # Also check primary_location pdf_url
        if not oa_url:
            oa_url = primary_loc.get("pdf_url") or None

        citation_count: int | None = record.get("cited_by_count")

        # Extract venue from primary_location source
        source = primary_loc.get("source") or {}
        venue = source.get("display_name") or ""

        provider_id = record.get("id") or ""

        is_abstract = bool(abstract) and not bool(oa_url)
        is_metadata_only = not bool(abstract) and not bool(oa_url)

        return ProviderResult(
            provider="openalex",
            provider_id=provider_id,
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
        logger.debug("OpenAlex record parse error (skipping): %s", exc)
        return None


def search_openalex(
    query: str,
    *,
    contact_email: str | None = None,
    max_results: int = _DEFAULT_MAX,
    evidence_role: str = "",
) -> list["ProviderResult"]:
    """Search OpenAlex for academic works matching the query.

    Returns up to max_results ProviderResult objects. Returns [] on network
    error, timeout, or API failure — never raises.

    contact_email is used in the User-Agent header for the polite pool;
    it is never stored in or returned from ProviderResult.
    """
    try:
        import httpx
    except ImportError:
        logger.debug("httpx not installed; OpenAlex unavailable")
        return []

    params: dict[str, str | int] = {
        "search": query,
        "per_page": min(max_results, 10),
        "select": _SELECT_FIELDS,
        "sort": "relevance_score:desc",
    }

    headers: dict[str, str] = {}
    if contact_email:
        # Polite pool: include email in User-Agent, never in result
        headers["User-Agent"] = f"RoundLab/1.0 (mailto:{contact_email})"

    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            response = client.get(_BASE_URL, params=params, headers=headers)
            if response.status_code != 200:
                logger.warning("OpenAlex returned HTTP %d", response.status_code)
                return []
            data = response.json()
    except Exception as exc:
        logger.warning("OpenAlex request failed: %s", type(exc).__name__)
        return []

    results: list[ProviderResult] = []
    for record in (data.get("results") or []):
        parsed = _parse_record(record, query, evidence_role)
        if parsed is not None:
            results.append(parsed)
        if len(results) >= max_results:
            break

    return results
