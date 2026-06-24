"""Deterministic parser routing for the Evidence Studio extraction pipeline.

Given a URL, an HTTP Content-Type header, and optional response bytes,
`route_extraction()` returns the best document type to use for extraction.

Routing priority (first match wins):
  1. Explicit Content-Type header from HTTP response
  2. URL file extension
  3. Magic bytes (first 8 bytes of response body)
  4. Default → "html"

The router is stateless and pure-deterministic — no network calls.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

# ── Known MIME types ──────────────────────────────────────────────────────────

_PDF_TYPES = frozenset({
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "application/vnd.pdf",
})

_DOCX_TYPES = frozenset({
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",  # might be .doc; we fall back gracefully
})

_HTML_TYPES = frozenset({
    "text/html",
    "application/xhtml+xml",
    "application/xhtml",
})

_TEXT_TYPES = frozenset({
    "text/plain",
    "text/markdown",
    "text/csv",
})

# ── File extension → document type ───────────────────────────────────────────

_EXT_TO_TYPE: dict[str, str] = {
    ".pdf":  "pdf",
    ".docx": "docx",
    ".doc":  "docx",
    ".htm":  "html",
    ".html": "html",
    ".txt":  "text",
    ".md":   "text",
    ".rst":  "text",
}

# ── Magic bytes ───────────────────────────────────────────────────────────────

_PDF_MAGIC   = b"%PDF"
_DOCX_MAGIC  = b"PK\x03\x04"   # ZIP-based container (DOCX/XLSX/PPTX)
_HTML_MAGIC1 = b"<!DOC"
_HTML_MAGIC2 = b"<html"


# ── Public interface ──────────────────────────────────────────────────────────

def route_extraction(
    url: str,
    *,
    content_type: str = "",
    first_bytes: bytes | None = None,
) -> str:
    """Return the document type to use for extraction.

    Returns one of: "pdf", "docx", "html", "text", "unknown".

    Priority:
      1. HTTP Content-Type (if non-empty and recognizable)
      2. URL file extension
      3. Magic bytes from response body
      4. "html" as default (most URLs are HTML)
    """

    # ── 1. Content-Type ───────────────────────────────────────────────────────
    if content_type:
        ct_lower = content_type.split(";")[0].strip().lower()
        if ct_lower in _PDF_TYPES:
            return "pdf"
        if ct_lower in _DOCX_TYPES:
            return "docx"
        if ct_lower in _HTML_TYPES:
            return "html"
        if ct_lower in _TEXT_TYPES:
            return "text"

    # ── 2. File extension ─────────────────────────────────────────────────────
    ext = _url_extension(url)
    if ext in _EXT_TO_TYPE:
        return _EXT_TO_TYPE[ext]

    # ── 3. Magic bytes ────────────────────────────────────────────────────────
    if first_bytes:
        head = first_bytes[:8]
        if head.startswith(_PDF_MAGIC):
            return "pdf"
        if head.startswith(_DOCX_MAGIC):
            return "docx"
        if head[:5].lower() in (b"<!doc", b"<html"):
            return "html"

    # ── 4. Default ────────────────────────────────────────────────────────────
    return "html"


def _url_extension(url: str) -> str:
    """Extract the lowercase file extension from a URL path, or ''."""
    try:
        path = urlparse(url).path
        _, ext = os.path.splitext(path)
        return ext.lower()
    except Exception:
        return ""


def is_pdf_url(url: str) -> bool:
    """Quick check: does the URL appear to point to a PDF (by extension)?"""
    return _url_extension(url) == ".pdf"


def is_docx_url(url: str) -> bool:
    """Quick check: does the URL appear to point to a DOCX (by extension)?"""
    return _url_extension(url) in (".docx", ".doc")
