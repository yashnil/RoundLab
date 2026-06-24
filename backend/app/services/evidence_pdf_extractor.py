"""PDF text extraction using PyMuPDF (fitz).

SAFETY INVARIANTS
- Extracted text is exact source output from PyMuPDF; never synthesized.
- Page numbers in DocumentSection are 1-based.
- Scanned/image-only PDFs produce a warning and empty text — no fabricated text.
- Malformed or password-protected PDFs return a failed ExtractedDocument.
- Content hash is computed after extraction.

PyMuPDF (package name `PyMuPDF`, import as `fitz`) is in requirements.txt.
If it is somehow unavailable, extract_pdf() returns a gracefully-failed doc.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_MIN_TEXT_CHARS_PER_PAGE = 50
_MAX_PAGES = 50  # safety cap; most academic papers ≤ 30 pages
_SCANNED_DETECT_SAMPLE_PAGES = 5


def _is_likely_scanned(pages_text: list[str]) -> bool:
    """Return True when the sampled pages have almost no extractable text.

    A scanned PDF will produce very short or empty text per page even though
    the page image contains dense text.
    """
    sample = pages_text[:_SCANNED_DETECT_SAMPLE_PAGES]
    if not sample:
        return True
    usable = [p for p in sample if len(p.strip()) >= _MIN_TEXT_CHARS_PER_PAGE]
    # If fewer than half of sampled pages have usable text → likely scanned
    return len(usable) < max(1, len(sample) // 2)


def extract_pdf(
    source: bytes | str,
    *,
    source_url: str = "",
    retrieval_timestamp: str = "",
) -> "ExtractedDocument":
    """Extract text from a PDF.

    Args:
        source: raw PDF bytes or a local file path.
        source_url: original URL for provenance.
        retrieval_timestamp: ISO-8601 UTC timestamp.

    Returns an ExtractedDocument.  On failure, `source_text_type` is
    "metadata_only" and `extraction_warnings` describes the problem.
    """
    from app.services.evidence_extracted_document import (
        DocumentSection,
        ExtractedDocument,
        finalize_document,
    )

    ts = retrieval_timestamp or datetime.now(timezone.utc).isoformat()

    doc = ExtractedDocument(
        source_url=source_url,
        document_type="pdf",
        extraction_method="pymupdf",
        extraction_version="",
        retrieval_timestamp=ts,
        http_content_type="application/pdf",
    )

    try:
        import fitz  # PyMuPDF
        doc.extraction_version = f"pymupdf-{fitz.version[0]}"
    except ImportError:
        doc.extraction_warnings.append("PyMuPDF (fitz) not available; PDF extraction skipped.")
        doc.source_text_type = "metadata_only"
        doc.is_metadata_only = True
        doc.extraction_confidence = 0.0
        return doc

    try:
        if isinstance(source, bytes):
            pdf = fitz.open(stream=source, filetype="pdf")
        else:
            pdf = fitz.open(str(source))
    except Exception as exc:
        doc.extraction_warnings.append(f"Could not open PDF: {exc}")
        doc.source_text_type = "metadata_only"
        doc.is_metadata_only = True
        doc.extraction_confidence = 0.0
        return doc

    try:
        page_count = len(pdf)
        doc.page_count = page_count

        # PDF document metadata
        pdf_meta = pdf.metadata or {}
        if pdf_meta.get("title"):
            doc.title = pdf_meta["title"].strip()
            doc.metadata_provenance["title"] = "pdf_metadata"
        if pdf_meta.get("author"):
            doc.author = pdf_meta["author"].strip()
            doc.metadata_provenance["author"] = "pdf_metadata"

        # Extract text page by page (up to _MAX_PAGES)
        pages_text: list[str] = []
        for i in range(min(page_count, _MAX_PAGES)):
            page = pdf[i]
            text = page.get_text("text")  # exact OCR-derived or vector text
            pages_text.append(text or "")

        if _is_likely_scanned(pages_text):
            doc.extraction_warnings.append(
                "PDF appears to be scanned/image-only and could not be read reliably. "
                "No text was fabricated."
            )
            doc.source_text_type = "metadata_only"
            doc.is_metadata_only = True
            doc.extraction_confidence = 0.0
            pdf.close()
            return finalize_document(doc)

        # Build sections (one section per page)
        all_text_parts: list[str] = []
        sections: list[DocumentSection] = []
        char_offset = 0
        section_idx = 0
        para_idx = 0

        for page_num_0based, page_text in enumerate(pages_text):
            cleaned = _clean_page_text(page_text)
            if not cleaned:
                continue

            start = char_offset
            all_text_parts.append(cleaned)
            char_offset += len(cleaned)

            if page_num_0based < page_count - 1:
                all_text_parts.append("\n\n")
                char_offset += 2

            section = DocumentSection(
                text=cleaned,
                start_char=start,
                end_char=start + len(cleaned),
                page_number=page_num_0based + 1,  # 1-based
                section_index=section_idx,
                paragraph_index=para_idx,
                parser_metadata={"page": page_num_0based + 1},
            )
            sections.append(section)
            section_idx += 1
            para_idx += 1

        pdf.close()

        raw_text = "".join(all_text_parts)
        if not raw_text.strip():
            doc.extraction_warnings.append("PDF extraction produced no usable text.")
            doc.source_text_type = "metadata_only"
            doc.is_metadata_only = True
            doc.extraction_confidence = 0.0
            return finalize_document(doc)

        doc.raw_text = raw_text
        doc.sections = sections
        doc.extraction_confidence = 0.9
        doc.source_text_type = "full_text" if page_count <= _MAX_PAGES else "partial_extraction"
        if page_count > _MAX_PAGES:
            doc.extraction_warnings.append(
                f"PDF has {page_count} pages; only first {_MAX_PAGES} extracted."
            )

        return finalize_document(doc)

    except Exception as exc:
        logger.warning("PDF extraction error for %s: %s", source_url, exc)
        doc.extraction_warnings.append(f"Unexpected extraction error: {exc}")
        doc.source_text_type = "metadata_only"
        doc.is_metadata_only = True
        doc.extraction_confidence = 0.0
        try:
            pdf.close()
        except Exception:
            pass
        return finalize_document(doc)


def _clean_page_text(text: str) -> str:
    """Normalize whitespace in page text without removing content."""
    # Collapse runs of spaces/tabs to a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
