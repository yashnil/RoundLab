"""Typed ExtractedDocument model shared across all parser backends.

Every extractor (HTML/PDF/DOCX/plain-text) produces an ExtractedDocument.
Downstream consumers (passage builder, card cutter, snapshot store) receive
this common model regardless of which parser was used.

SAFETY INVARIANTS
- `raw_text` is exact, immutable extraction output; never synthesized.
- `normalized_text` may have whitespace collapsed but MUST NOT have content
  added, removed, or substituted.
- Sections carry absolute `start_char`/`end_char` offsets into `raw_text`.
- `source_text_type` is set by the extractor, not inferred after the fact.
- `extraction_warnings` records problems; it never removes data.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional


# ── Source-text classification ────────────────────────────────────────────────

SOURCE_TEXT_TYPES = (
    "full_text",          # complete article / document body
    "abstract_only",      # only an abstract is available (academic record)
    "snippet_only",       # only a short search snippet
    "partial_extraction", # extraction succeeded but may be incomplete
    "metadata_only",      # title/authors/date only, no usable body text
)


# ── DocumentSection ───────────────────────────────────────────────────────────

@dataclass
class DocumentSection:
    """One coherent section of an extracted document.

    For HTML: a run of paragraphs under a heading.
    For PDF: a run of text blocks on one page.
    For DOCX: a paragraph or group of paragraphs under a style-heading.
    """

    # Exact source text (immutable after construction)
    text: str = ""

    # Stable character offsets into ExtractedDocument.raw_text
    start_char: int = 0
    end_char: int = 0

    # Structural context
    heading: str = ""                 # immediately preceding heading, if any
    page_number: Optional[int] = None # PDF page (1-based), None for HTML/DOCX
    paragraph_index: int = 0          # 0-based index in document
    section_index: int = 0            # 0-based section index

    # Optional PDF-specific spatial metadata
    bounding_box: Optional[tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)

    # Parser-specific metadata (e.g., DOCX style, PDF block type)
    parser_metadata: dict = field(default_factory=dict)


# ── ExtractedDocument ─────────────────────────────────────────────────────────

@dataclass
class ExtractedDocument:
    """The canonical output of any parser backend.

    Consumers that previously received `(str, ArticleMetadata)` should migrate
    to this model.  The `raw_text` field replaces the old text string.  The
    `sections` list is optional but enables section-aware passage construction
    in `build_passages_from_document()`.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    source_url: str = ""            # the URL that was fetched
    canonical_url: str = ""         # after redirect / OG-url / HTTP Link header

    # ── Document type ─────────────────────────────────────────────────────────
    document_type: str = "html"     # "html" | "pdf" | "docx" | "text" | "unknown"

    # ── Bibliographic metadata ────────────────────────────────────────────────
    title: str = ""
    author: str = ""
    publication_date: str = ""
    publisher: str = ""

    # ── Content ───────────────────────────────────────────────────────────────
    raw_text: str = ""              # IMMUTABLE: exact extraction output
    normalized_text: str = ""       # whitespace-normalized for display only
    sections: list[DocumentSection] = field(default_factory=list)

    # ── Extraction provenance ─────────────────────────────────────────────────
    extraction_method: str = ""     # "trafilatura" | "beautifulsoup" | "pymupdf"
                                    # | "python_docx" | "firecrawl" | "snippet"
    extraction_version: str = ""
    retrieval_timestamp: str = ""   # ISO-8601 UTC

    # ── Content fingerprint ───────────────────────────────────────────────────
    content_hash: str = ""          # SHA-256 of raw_text; empty until computed

    # ── HTTP metadata ─────────────────────────────────────────────────────────
    http_content_type: str = ""
    http_status: int = 0

    # ── Document structure ────────────────────────────────────────────────────
    page_count: Optional[int] = None  # PDF only

    # ── Quality signals ───────────────────────────────────────────────────────
    extraction_warnings: list[str] = field(default_factory=list)
    extraction_confidence: float = 1.0  # 0.0–1.0
    source_text_type: str = "full_text"
    is_metadata_only: bool = False

    # ── Metadata provenance ───────────────────────────────────────────────────
    # Maps field name → source label, e.g. {"title": "json_ld", "author": "meta_tags"}
    metadata_provenance: dict[str, str] = field(default_factory=dict)

    # ── Provider back-link (from Pass 9 academic providers) ───────────────────
    # Preserves _source_priority, _doi, _provider so we don't lose P9 signals
    provider_metadata: dict = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_content_hash(text: str) -> str:
    """Return SHA-256 hex digest of text encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def finalize_document(doc: ExtractedDocument) -> ExtractedDocument:
    """Compute content_hash and normalized_text if not already set.

    Call this after setting `raw_text` in any extractor.
    """
    import re

    if doc.raw_text and not doc.content_hash:
        doc.content_hash = compute_content_hash(doc.raw_text)

    if doc.raw_text and not doc.normalized_text:
        # Collapse runs of spaces/tabs; collapse 3+ blank lines to 2.
        t = re.sub(r"[ \t]+", " ", doc.raw_text)
        t = re.sub(r"\n{3,}", "\n\n", t)
        doc.normalized_text = t.strip()

    return doc
