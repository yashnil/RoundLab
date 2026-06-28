"""Safe web article extraction for Research-to-Card Evidence Builder.

- Validates URLs to prevent SSRF (no private IPs, localhost, file://).
- Fetches with timeout and byte limit.
- Extracts article text via trafilatura (preferred) or BeautifulSoup fallback.
- Extracts metadata: title, author, publication, published_date.
- Never fabricates metadata — missing fields stay None.
"""

import ipaddress
import logging
import re
import socket
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.models.research import ArticleMetadata, ExtractedArticle

logger = logging.getLogger(__name__)

# ── Safety constants ──────────────────────────────────────────────────────────

_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
_TIMEOUT_SECONDS    = 15
_USER_AGENT         = (
    "Mozilla/5.0 (compatible; DissioBot/1.0; +https://dissio.app/bot)"
)

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_MIN_ARTICLE_CHARS = 200


# ── URL validation ─────────────────────────────────────────────────────────────

def validate_url(url: str) -> tuple[bool, str]:
    """Return (is_safe, reason). reason is '' when safe."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format."

    if parsed.scheme not in ("http", "https"):
        return False, "Only http:// and https:// URLs are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no hostname."

    # Reject obvious private patterns
    lowered = hostname.lower()
    if lowered in ("localhost", "127.0.0.1", "::1"):
        return False, "Internal hostname not allowed."
    if lowered.endswith(".local") or lowered.endswith(".internal"):
        return False, "Internal hostname not allowed."

    # Resolve hostname and check for private IP
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # DNS failure — allow (might be valid but temporarily unreachable)
        return True, ""

    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for net in _PRIVATE_NETWORKS:
            if addr in net:
                return False, f"URL resolves to a private IP address ({ip_str})."

    return True, ""


# ── Organization-as-author domain map (Part 3) ────────────────────────────────

# Maps a domain substring → the organization name to use as author when no
# human author is found. Never fabricates a human name — only credible orgs.
ORG_AUTHOR_DOMAINS: dict[str, str] = {
    "congress.gov": "U.S. Congress",
    "un.org": "United Nations",
    "unodc.org": "United Nations Office on Drugs and Crime",
    "iep.utm.edu": "Internet Encyclopedia of Philosophy",
    "plato.stanford.edu": "Stanford Encyclopedia of Philosophy",
    "carnegieendowment.org": "Carnegie Endowment for International Peace",
    "cfr.org": "Council on Foreign Relations",
    "rand.org": "RAND Corporation",
    "brookings.edu": "Brookings Institution",
    "amnesty.org": "Amnesty International",
    "hrw.org": "Human Rights Watch",
    "icrc.org": "International Committee of the Red Cross",
    "who.int": "World Health Organization",
    "imf.org": "International Monetary Fund",
    "worldbank.org": "World Bank",
    "oecd.org": "Organisation for Economic Co-operation and Development",
    "supremecourt.gov": "Supreme Court of the United States",
    "justice.gov": "U.S. Department of Justice",
    "state.gov": "U.S. Department of State",
    "gao.gov": "U.S. Government Accountability Office",
    "crsreports.congress.gov": "Congressional Research Service",
    "pewresearch.org": "Pew Research Center",
    "law.cornell.edu": "Cornell Legal Information Institute",
    "ohchr.org": "UN Office of the High Commissioner for Human Rights",
}


def organization_author_for_url(url: str) -> str:
    """Return an organization-as-author label for a known credible domain, or ''.

    Never fabricates a human author — only well-known institutional sources.
    """
    try:
        host = (urlparse(url).hostname or "").lower().lstrip(".")
    except Exception:
        return ""
    if not host:
        return ""
    host = host[4:] if host.startswith("www.") else host
    # Longest-match first so subdomains like crsreports.congress.gov win.
    for dom in sorted(ORG_AUTHOR_DOMAINS, key=len, reverse=True):
        if host == dom or host.endswith("." + dom) or host == dom.lstrip("."):
            return ORG_AUTHOR_DOMAINS[dom]
    return ""


def _parse_jsonld_metadata(soup) -> dict:
    """Parse schema.org JSON-LD blocks for article metadata.

    Returns a dict with any of: title, author, date, publication. Empty values
    are omitted. Never raises.
    """
    import json

    out: dict = {}
    _article_types = {"Article", "ScholarlyArticle", "NewsArticle", "WebPage", "BlogPosting", "Report"}

    def _author_name(node) -> str:
        if isinstance(node, str):
            return node.strip()
        if isinstance(node, dict):
            return str(node.get("name", "")).strip()
        if isinstance(node, list) and node:
            names = [_author_name(n) for n in node]
            names = [n for n in names if n]
            return names[0] if names else ""
        return ""

    def _consume(node) -> None:
        if not isinstance(node, dict):
            return
        node_type = node.get("@type", "")
        types = node_type if isinstance(node_type, list) else [node_type]
        if not any(t in _article_types for t in types):
            # Still allow extraction if it carries article-ish fields
            if not any(k in node for k in ("headline", "datePublished", "author")):
                return
        if "title" not in out:
            t = node.get("name") or node.get("headline")
            if t:
                out["title"] = str(t).strip()
        if "author" not in out:
            a = _author_name(node.get("author") or node.get("creator"))
            if a:
                out["author"] = a
        if "date" not in out:
            d = node.get("datePublished") or node.get("dateCreated")
            if d:
                out["date"] = str(d).split("T")[0]
        if "publication" not in out:
            pub = node.get("publisher")
            if isinstance(pub, dict):
                pub = pub.get("name")
            if pub:
                out["publication"] = str(pub).strip()

    try:
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = tag.string or tag.get_text() or ""
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            nodes = data if isinstance(data, list) else [data]
            for n in nodes:
                if isinstance(n, dict) and "@graph" in n:
                    for g in n.get("@graph", []):
                        _consume(g)
                else:
                    _consume(n)
    except Exception:
        pass
    return out


def extract_metadata_from_html(
    url: str,
    html_content: str,
    existing_metadata: Optional[dict] = None,
) -> dict:
    """Best-effort metadata cascade from HTML.

    Checks, in order: HTML/OG/academic meta tags → schema.org JSON-LD →
    organization-as-author heuristic. Returns a dict with keys: title, author,
    date, publication, and *_source provenance keys. Never fabricates a human
    author. Never raises.
    """
    md: dict = dict(existing_metadata or {})
    prov: dict = {}

    def _set(key: str, value: Optional[str], source: str) -> None:
        if value and str(value).strip() and not md.get(key):
            md[key] = str(value).strip()
            prov[key] = source

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup((html_content or "")[:300_000], "lxml")

        def _meta(attr: str, value: str) -> Optional[str]:
            tag = soup.find("meta", attrs={attr: value})
            if tag and tag.get("content"):
                return str(tag["content"]).strip() or None
            return None

        def _meta_all(name: str) -> list[str]:
            out: list[str] = []
            for tag in soup.find_all("meta", attrs={"name": name}):
                c = tag.get("content")
                if c and str(c).strip():
                    out.append(str(c).strip())
            return out

        # 1. Meta tags (OG + academic citation_* + dublin core)
        _set("title", _meta("property", "og:title"), "meta_tags")
        _set("title", _meta("name", "citation_title"), "meta_tags")
        _set("date", _meta("property", "article:published_time"), "meta_tags")
        _set("date", _meta("name", "citation_publication_date"), "meta_tags")
        _set("date", _meta("name", "citation_date"), "meta_tags")
        _set("date", _meta("name", "dc.date"), "meta_tags")
        citation_authors = _meta_all("citation_author")
        if citation_authors:
            _set("author", "; ".join(citation_authors), "meta_tags")
        _set("author", _meta("property", "article:author"), "meta_tags")
        _set("author", _meta("name", "author"), "meta_tags")
        _set("author", _meta("name", "dc.creator"), "meta_tags")
        _set("publication", _meta("name", "citation_journal_title"), "meta_tags")
        _set("publication", _meta("property", "og:site_name"), "meta_tags")
        _set("publication", _meta("name", "dc.publisher"), "meta_tags")

        # Normalize date to YYYY-MM-DD
        if md.get("date") and "T" in md["date"]:
            md["date"] = md["date"].split("T")[0]

        # 2. Schema.org JSON-LD
        jsonld = _parse_jsonld_metadata(soup)
        for k in ("title", "author", "date", "publication"):
            _set(k, jsonld.get(k), "schema_org")
    except ImportError:
        pass
    except Exception:
        pass

    # 3. Organization-as-author heuristic (only when no human author found)
    if not md.get("author"):
        org = organization_author_for_url(url)
        if org:
            md["author"] = org
            prov["author"] = "organization_heuristic"

    md["provenance"] = prov
    return md


# ── HTML metadata extraction ───────────────────────────────────────────────────

def _extract_metadata_from_html(html: str, url: str) -> ArticleMetadata:
    """Extract title/author/publication/date from HTML meta tags and OG tags.
    Falls back gracefully — never fabricates values."""
    warnings: list[str] = []

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html[:200_000], "lxml")

        def _meta(name_attr: str, value: str) -> str | None:
            """Look up a meta tag by name= or property= attribute."""
            tag = soup.find("meta", attrs={name_attr: value})
            if tag and tag.get("content"):
                return str(tag["content"]).strip() or None
            return None

        title = (
            _meta("property", "og:title")
            or _meta("name", "twitter:title")
            or (soup.title.string.strip() if soup.title and soup.title.string else None)
        )

        author = (
            _meta("name", "author")
            or _meta("property", "article:author")
            or _meta("name", "twitter:creator")
        )

        publication = (
            _meta("property", "og:site_name")
            or _meta("name", "publisher")
        )

        published_date = (
            _meta("property", "article:published_time")
            or _meta("name", "date")
            or _meta("name", "pubdate")
            or _meta("property", "og:article:published_time")
        )
        # Truncate to date only if datetime
        if published_date and "T" in published_date:
            published_date = published_date.split("T")[0]

        canonical = _meta("property", "og:url") or url
        excerpt = _meta("property", "og:description") or _meta("name", "description")
        lang = soup.find("html")
        language = lang.get("lang") if lang else None

        return ArticleMetadata(
            title=title,
            author=author,
            publication=publication,
            published_date=published_date,
            url=url,
            canonical_url=canonical,
            language=language,
            excerpt=excerpt,
            warnings=warnings,
        )
    except ImportError:
        warnings.append("bs4 not available; metadata from URL only.")
        return ArticleMetadata(url=url, warnings=warnings)
    except Exception as exc:
        warnings.append(f"Metadata extraction error: {exc}")
        return ArticleMetadata(url=url, warnings=warnings)


def _build_article_metadata(html: str, url: str) -> ArticleMetadata:
    """Build ArticleMetadata using the deepest available cascade.

    Combines the rich metadata cascade (OpenGraph + academic citation_* meta +
    Dublin Core + schema.org JSON-LD + organization-as-author heuristic) from
    extract_metadata_from_html with the structural fields (canonical URL,
    excerpt, language) from the basic meta-tag reader. The richer cascade wins
    for title/author/publication/date because it understands scholarly markup;
    the basic reader supplies page-structure fields the cascade does not return.

    Never fabricates: any field still missing stays None.
    """
    base = _extract_metadata_from_html(html, url)
    warnings = list(base.warnings)

    rich: dict = {}
    try:
        rich = extract_metadata_from_html(url, html, {})
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("rich metadata cascade failed: %s", exc)

    def _pick(rich_key: str, base_val: Optional[str]) -> Optional[str]:
        rv = rich.get(rich_key)
        if rv and str(rv).strip():
            return str(rv).strip()
        return base_val

    published_date = _pick("date", base.published_date)
    if published_date and "T" in published_date:
        published_date = published_date.split("T")[0]

    prov = rich.get("provenance", {}) or {}
    if prov:
        # Record where the strongest fields came from (useful for debugging extraction).
        srcs = ", ".join(f"{k}:{v}" for k, v in prov.items() if v)
        if srcs:
            warnings.append(f"metadata_provenance: {srcs}")

    return ArticleMetadata(
        title=_pick("title", base.title),
        author=_pick("author", base.author),
        publication=_pick("publication", base.publication),
        published_date=published_date,
        url=url,
        canonical_url=base.canonical_url or url,
        language=base.language,
        excerpt=base.excerpt,
        warnings=warnings,
    )


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_text_trafilatura(html: str, url: str) -> tuple[str, float]:
    """Extract article text using trafilatura. Returns (text, confidence)."""
    try:
        import trafilatura  # type: ignore

        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
        )
        if text and len(text) >= _MIN_ARTICLE_CHARS:
            return text, 0.85
        return "", 0.0
    except ImportError:
        return "", 0.0
    except Exception:
        return "", 0.0


def _extract_text_beautifulsoup(html: str) -> tuple[str, float]:
    """Fallback: extract article text using BeautifulSoup heuristics."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html[:200_000], "lxml")

        # Remove boilerplate elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "form", "noscript", "iframe", "figure",
                         "figcaption", "button", "input"]):
            tag.decompose()

        # Try article/main/content areas first
        for selector in ["article", "main", '[role="main"]',
                         ".article-body", ".post-content", ".entry-content",
                         ".content", "#content", ".story-body"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) >= _MIN_ARTICLE_CHARS:
                    return _normalize_text(text), 0.55

        # Fall back to all paragraphs
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        text = "\n\n".join(p for p in paragraphs if len(p) > 40)
        if len(text) >= _MIN_ARTICLE_CHARS:
            return _normalize_text(text), 0.40

        return "", 0.0
    except ImportError:
        return "", 0.0
    except Exception:
        return "", 0.0


def _normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks."""
    # Collapse runs of spaces/tabs but keep newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Main extraction entry point ───────────────────────────────────────────────

def extract_article(url: str) -> ExtractedArticle:
    """Fetch and extract an article from a URL.

    Returns ExtractedArticle with status='failed' if fetch or extraction fails.
    Raises ValueError for unsafe URLs.
    """
    safe, reason = validate_url(url)
    if not safe:
        raise ValueError(reason)

    # ── Fetch ─────────────────────────────────────────────────────────────
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=_TIMEOUT_SECONDS,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise ValueError(
                    f"Unsupported content type: {content_type}. "
                    "Only HTML and plain-text pages are supported."
                )
            raw = resp.content[:_MAX_DOWNLOAD_BYTES]
            html = raw.decode(resp.encoding or "utf-8", errors="replace")
    except ValueError:
        raise
    except httpx.HTTPStatusError as exc:
        return ExtractedArticle(
            url=url,
            metadata=ArticleMetadata(url=url),
            extracted_text="",
            extraction_method="failed",
            extraction_confidence=0.0,
            status="failed",
            error=f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}",
        )
    except httpx.TimeoutException:
        return ExtractedArticle(
            url=url,
            metadata=ArticleMetadata(url=url),
            extracted_text="",
            extraction_method="failed",
            extraction_confidence=0.0,
            status="failed",
            error="Request timed out. The server did not respond in time.",
        )
    except Exception as exc:
        return ExtractedArticle(
            url=url,
            metadata=ArticleMetadata(url=url),
            extracted_text="",
            extraction_method="failed",
            extraction_confidence=0.0,
            status="failed",
            error=str(exc),
        )

    # ── Metadata (deep cascade: OG + citation_* + Dublin Core + JSON-LD + org) ─
    metadata = _build_article_metadata(html, url)

    # ── Text extraction ───────────────────────────────────────────────────
    text, confidence = _extract_text_trafilatura(html, url)
    method = "trafilatura"

    if not text:
        text, confidence = _extract_text_beautifulsoup(html)
        method = "beautifulsoup"

    if not text:
        return ExtractedArticle(
            url=url,
            metadata=metadata,
            extracted_text="",
            extraction_method="failed",
            extraction_confidence=0.0,
            status="failed",
            error="Could not extract article text from this page. Try pasting the text manually.",
        )

    status = "ok" if len(text) >= 500 else "partial"
    if len(text) < _MIN_ARTICLE_CHARS:
        return ExtractedArticle(
            url=url,
            metadata=metadata,
            extracted_text=text,
            extraction_method=method,
            extraction_confidence=confidence,
            status="partial",
            error="Article text is too short to cut a reliable card.",
        )

    return ExtractedArticle(
        url=url,
        metadata=metadata,
        extracted_text=text,
        extraction_method=method,
        extraction_confidence=confidence,
        status=status,
    )


def extract_article_from_paste(
    pasted_text: str,
    url: str | None = None,
    title: str | None = None,
    author: str | None = None,
    publication: str | None = None,
    published_date: str | None = None,
) -> ExtractedArticle:
    """Wrap pasted text as an ExtractedArticle without fetching anything.

    Applies the same chrome stripping as URL extraction so pasted repository
    text (Digital Commons, ScholarWorks, etc.) is cleaned before cutting.
    """
    from app.services.card_cutting import strip_page_chrome
    text = strip_page_chrome(_normalize_text(pasted_text))
    meta = ArticleMetadata(
        title=title,
        author=author,
        publication=publication,
        published_date=published_date,
        url=url or "",
    )
    if len(text) < _MIN_ARTICLE_CHARS:
        return ExtractedArticle(
            url=url or "",
            metadata=meta,
            extracted_text=text,
            extraction_method="paste",
            extraction_confidence=1.0,
            status="partial",
            error="Pasted text is very short.",
        )
    return ExtractedArticle(
        url=url or "",
        metadata=meta,
        extracted_text=text,
        extraction_method="paste",
        extraction_confidence=1.0,
        status="ok",
    )
