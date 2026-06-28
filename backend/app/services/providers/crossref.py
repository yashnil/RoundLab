"""Crossref DOI metadata lookup adapter.

Crossref (https://www.crossref.org) provides authoritative bibliographic
metadata for registered DOIs. No API key required; a contact email in the
User-Agent header enables the polite pool.

USAGE PATTERN
- Use this adapter to VERIFY and ENRICH metadata for records that already have
  a DOI. Do not use it for broad discovery.
- Cache results by DOI within a request to avoid repeated fetches.
- When Crossref lacks a field, keep the original provider value.

SAFETY INVARIANTS
- Crossref returns bibliographic metadata only — no abstract or full text.
- Never overwrite a non-empty field with an empty Crossref value.
- Network timeout is bounded. Returns None on failure.
- No credentials stored in ProviderResult.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.crossref.org/works"
_TIMEOUT = 6.0


def _first(lst: list[Any], default: Any = "") -> Any:
    """Return the first non-empty item from a list, or default."""
    for item in lst:
        if item:
            return item
    return default


def _parse_crossref_message(msg: dict[str, Any]) -> "ProviderResult | None":
    """Parse a Crossref works message into a ProviderResult."""
    from app.services.evidence_provider_result import ProviderResult

    try:
        doi_raw = msg.get("DOI") or ""
        doi = doi_raw.strip() if doi_raw.startswith("10.") else None

        title_list = msg.get("title") or []
        title = _first(title_list)

        authors: list[str] = []
        for a in (msg.get("author") or [])[:5]:
            family = a.get("family") or ""
            given = a.get("given") or ""
            name = f"{given} {family}".strip() if given else family
            if name:
                authors.append(name)

        # Year: prefer 'published' over 'issued'
        year: int | None = None
        for date_key in ("published", "issued", "published-print", "published-online"):
            date_parts = (msg.get(date_key) or {}).get("date-parts")
            if date_parts and date_parts[0]:
                try:
                    year = int(date_parts[0][0])
                    break
                except (TypeError, ValueError, IndexError):
                    pass

        container_titles = msg.get("container-title") or []
        venue = _first(container_titles)
        if not venue:
            venue = msg.get("publisher") or ""

        canonical_url = f"https://doi.org/{doi}" if doi else ""
        landing_url = msg.get("URL") or canonical_url

        return ProviderResult(
            provider="crossref",
            provider_id=doi or "",
            title=title,
            abstract="",   # Crossref does not return abstracts
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            canonical_url=canonical_url,
            landing_url=landing_url,
            open_access_url=None,
            source_type="academic",
            is_metadata_only=True,  # Crossref is always metadata-only
        )
    except Exception as exc:
        logger.debug("Crossref message parse error: %s", exc)
        return None


def lookup_crossref_doi(
    doi: str,
    *,
    contact_email: str | None = None,
) -> "ProviderResult | None":
    """Fetch authoritative bibliographic metadata for a DOI from Crossref.

    Returns a ProviderResult with bibliographic fields only (no abstract).
    Returns None on network error, timeout, 404, or parse failure.
    contact_email is used only for the User-Agent polite-pool header.
    """
    try:
        import httpx
    except ImportError:
        return None

    clean_doi = doi.strip()
    if not clean_doi.startswith("10."):
        return None

    url = f"{_BASE_URL}/{clean_doi}"
    headers: dict[str, str] = {}
    if contact_email:
        headers["User-Agent"] = f"Dissio/1.0 (mailto:{contact_email})"

    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                logger.warning("Crossref returned HTTP %d for DOI %s", response.status_code, clean_doi)
                return None
            data = response.json()
    except Exception as exc:
        logger.warning("Crossref request failed for DOI %s: %s", clean_doi, type(exc).__name__)
        return None

    message = data.get("message") or {}
    if not message:
        return None

    return _parse_crossref_message(message)
