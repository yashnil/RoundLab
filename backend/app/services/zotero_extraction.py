"""Optional Zotero Translation Server integration for citation metadata.

Gated entirely behind config (ZOTERO_TRANSLATION_SERVER_URL +
research_enable_zotero). When disabled or unreachable it returns None and the
caller falls back to other metadata sources. Never raises.
"""

import logging
import uuid
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ZoteroMetadata(BaseModel):
    title: str = ""
    author: str = ""          # "Last; Last2" or org name
    authors: list[str] = []
    year: str = ""
    publication: str = ""     # publicationTitle / websiteTitle
    doi: str = ""
    item_type: str = ""       # journalArticle | webpage | newspaperArticle | report ...
    is_academic: bool = False
    is_news: bool = False
    is_government: bool = False


def _classify_item_type(item_type: str) -> tuple[bool, bool, bool]:
    """Return (is_academic, is_news, is_government) flags from a Zotero itemType."""
    t = (item_type or "").lower()
    academic = t in ("journalarticle", "conferencepaper", "thesis", "preprint", "book", "booksection")
    news = t in ("newspaperarticle", "magazinearticle", "blogpost")
    government = t in ("report", "statute", "bill", "case", "hearing", "document")
    return academic, news, government


def _parse_zotero_item(item: dict) -> ZoteroMetadata:
    """Parse a single Zotero item dict into ZoteroMetadata. Never raises."""
    creators = item.get("creators") or []
    authors: list[str] = []
    for c in creators:
        if not isinstance(c, dict):
            continue
        if c.get("creatorType") not in (None, "author", "creator"):
            continue
        name = c.get("name") or " ".join(
            p for p in (c.get("firstName", ""), c.get("lastName", "")) if p
        ).strip()
        if name:
            authors.append(name.strip())

    author_display = ""
    if authors:
        # Prefer last names for the display string
        last_names = []
        for a in authors:
            if "," in a:
                last_names.append(a.split(",")[0].strip())
            else:
                parts = a.split()
                last_names.append(parts[-1] if parts else a)
        author_display = last_names[0] + (" et al." if len(last_names) > 1 else "")

    date = str(item.get("date", "") or "")
    year = ""
    import re as _re
    m = _re.search(r"(19|20)\d{2}", date)
    if m:
        year = m.group(0)

    publication = (
        item.get("publicationTitle")
        or item.get("websiteTitle")
        or item.get("blogTitle")
        or item.get("publisher")
        or ""
    )
    item_type = item.get("itemType", "") or ""
    academic, news, government = _classify_item_type(item_type)

    return ZoteroMetadata(
        title=str(item.get("title", "") or "").strip(),
        author=author_display,
        authors=authors,
        year=year,
        publication=str(publication).strip(),
        doi=str(item.get("DOI", "") or "").strip(),
        item_type=item_type,
        is_academic=academic,
        is_news=news,
        is_government=government,
    )


def extract_with_zotero(
    url: str,
    server_url: Optional[str] = None,
    timeout: float = 10.0,
) -> Optional[ZoteroMetadata]:
    """Query a Zotero Translation Server's /web endpoint for citation metadata.

    Returns None when disabled, unconfigured, or on any error.
    """
    from app.config import settings

    if not getattr(settings, "research_enable_zotero", False):
        return None
    server = (server_url or getattr(settings, "zotero_translation_server_url", None) or "").strip()
    if not server:
        return None

    try:
        import httpx

        endpoint = server.rstrip("/") + "/web"
        resp = httpx.post(
            endpoint,
            json={"url": url, "sessionID": uuid.uuid4().hex},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        items = data if isinstance(data, list) else [data]
        if not items or not isinstance(items[0], dict):
            return None
        return _parse_zotero_item(items[0])
    except Exception as exc:
        logger.debug("Zotero extraction failed for %s: %s", url[:60], exc)
        return None
