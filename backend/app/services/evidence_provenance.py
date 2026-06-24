"""Passage provenance tracking.

Provides:
- PassageProvenance  : typed provenance record attached to each evidence candidate
- compute_content_hash : deterministic SHA-256 of exact text
- validate_passage_offsets : confirm start/end into document.raw_text
- validate_card_body_offsets : confirm card body is an exact substring of passage

SAFETY INVARIANTS
- No credential, cookie, or authorization data may appear in PassageProvenance.
- PassageProvenance.raw_text_snapshot is bounded to ≤ 500 chars.
- Offset validation never modifies text.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PassageProvenance:
    """Provenance record for one EvidenceCandidate passage.

    Attached to EvidenceCandidate.provenance after passage construction.
    Forwarded into card metadata when a card is cut from this passage.
    """

    # ── Document identity ─────────────────────────────────────────────────────
    source_url: str = ""
    canonical_url: str = ""
    document_type: str = ""        # "html" | "pdf" | "docx" | "text"
    content_hash: str = ""         # SHA-256 of parent document's raw_text
    retrieval_timestamp: str = ""

    # ── Position within document ──────────────────────────────────────────────
    start_char: int = 0
    end_char: int = 0
    page_number: Optional[int] = None   # PDF only (1-based); None for HTML/DOCX
    section_heading: str = ""
    paragraph_index: int = 0
    section_index: int = 0

    # ── Extraction method ─────────────────────────────────────────────────────
    extraction_method: str = ""    # "trafilatura" | "pymupdf" | "python_docx" | …
    extraction_version: str = ""

    # ── Source-text classification ────────────────────────────────────────────
    source_text_type: str = "full_text"  # full_text | abstract_only | partial_extraction | …

    # ── Bounded excerpt for display (never full copyrighted text) ─────────────
    raw_text_snapshot: str = ""    # first 500 chars of passage text

    # ── Warnings from extraction ──────────────────────────────────────────────
    extraction_warnings: list[str] = field(default_factory=list)


def compute_content_hash(text: str) -> str:
    """Return SHA-256 hex digest of text (UTF-8 encoded)."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def validate_passage_offsets(
    document_text: str,
    passage_text: str,
    start: int,
    end: int,
) -> tuple[bool, str]:
    """Return (valid, message).

    Checks that document_text[start:end].strip() == passage_text.
    """
    if start < 0 or end > len(document_text) or start > end:
        return False, f"Offset ({start},{end}) out of range for document length {len(document_text)}."
    slice_text = document_text[start:end].strip()
    if slice_text != passage_text:
        return (
            False,
            f"Passage text does not match document at offset ({start},{end}). "
            f"Expected length {len(passage_text)}, got length {len(slice_text)}.",
        )
    return True, ""


def validate_card_body_in_document(
    document_text: str,
    card_body: str,
) -> tuple[bool, str]:
    """Return (valid, message).

    Checks that `card_body` is an exact substring of `document_text`.
    A card body is always derived from an exact passage slice, so this
    confirms the chain of custody has not been broken.
    """
    # Card body may have ellipses ("[…]") from the cut engine; remove them
    # to extract individual spans and check each one.
    import re
    _ELLIPSIS_PATTERN = re.compile(r"\s*\[[…\.]+\]\s*", re.UNICODE)
    spans = [s.strip() for s in _ELLIPSIS_PATTERN.split(card_body) if s.strip()]

    if not spans:
        return False, "Card body is empty after stripping ellipsis markers."

    for span in spans:
        if span not in document_text:
            return (
                False,
                f"Card body span '{span[:60]}…' is not an exact substring of the document.",
            )
    return True, ""


def make_provenance(
    document: "ExtractedDocument",
    section: "DocumentSection",
) -> PassageProvenance:
    """Create a PassageProvenance from an ExtractedDocument + DocumentSection."""
    return PassageProvenance(
        source_url=document.source_url,
        canonical_url=document.canonical_url,
        document_type=document.document_type,
        content_hash=document.content_hash,
        retrieval_timestamp=document.retrieval_timestamp,
        start_char=section.start_char,
        end_char=section.end_char,
        page_number=section.page_number,
        section_heading=section.heading,
        paragraph_index=section.paragraph_index,
        section_index=section.section_index,
        extraction_method=document.extraction_method,
        extraction_version=document.extraction_version,
        source_text_type=document.source_text_type,
        raw_text_snapshot=section.text[:500],
        extraction_warnings=list(document.extraction_warnings),
    )
