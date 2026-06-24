"""HTML → ExtractedDocument wrapper.

Calls the existing `extract_article()` / `extract_article_from_paste()` and
wraps their output in ExtractedDocument, adding:
- structured sections (one per paragraph group)
- explicit metadata_provenance tracking
- content_hash
- source_text_type

This preserves full backward compatibility with the existing extraction logic
while making the output available to the new section-aware passage builder.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def article_to_document(
    article: "ExtractedArticle",
    *,
    retrieval_timestamp: str = "",
) -> "ExtractedDocument":
    """Convert an ExtractedArticle into an ExtractedDocument.

    Used when the existing `extract_article()` path is the extraction backend.
    Builds paragraph-level sections from the extracted_text so that
    `build_passages_from_document()` can consume them.
    """
    from app.services.evidence_extracted_document import (
        DocumentSection,
        ExtractedDocument,
        finalize_document,
    )

    ts = retrieval_timestamp or datetime.now(timezone.utc).isoformat()

    # Determine source_text_type from status
    if article.status == "failed" or not article.extracted_text:
        source_text_type = "metadata_only"
    elif article.extraction_confidence >= 0.8:
        source_text_type = "full_text"
    elif article.status == "partial":
        source_text_type = "partial_extraction"
    else:
        source_text_type = "full_text"

    meta = article.metadata

    # Build metadata_provenance from existing warnings (which encode provenance)
    metadata_provenance: dict[str, str] = {}
    for warn in (meta.warnings or []):
        if warn.startswith("metadata_provenance:"):
            for item in warn.replace("metadata_provenance:", "").split(","):
                item = item.strip()
                if ":" in item:
                    k, v = item.split(":", 1)
                    metadata_provenance[k.strip()] = v.strip()

    doc = ExtractedDocument(
        source_url=article.url,
        canonical_url=(meta.canonical_url or article.url),
        document_type="html",
        title=meta.title or "",
        author=meta.author or "",
        publication_date=meta.published_date or "",
        publisher=meta.publication or "",
        raw_text=article.extracted_text,
        extraction_method=article.extraction_method,
        retrieval_timestamp=ts,
        http_content_type="text/html",
        extraction_confidence=article.extraction_confidence,
        source_text_type=source_text_type,
        is_metadata_only=(source_text_type == "metadata_only"),
        metadata_provenance=metadata_provenance,
        extraction_warnings=list(meta.warnings or []),
    )

    # Build paragraph sections with stable char offsets
    if article.extracted_text:
        doc.sections = _build_sections_from_text(article.extracted_text)

    # Copy article error as warning
    if article.error:
        doc.extraction_warnings.append(f"extraction_error: {article.error}")

    return finalize_document(doc)


def _build_sections_from_text(text: str) -> list["DocumentSection"]:
    """Build DocumentSection list from plain extracted text.

    Splits on blank lines (paragraph boundaries).  Returns a list of sections
    with accurate start_char/end_char offsets into the full text.
    """
    import re
    from app.services.evidence_extracted_document import DocumentSection

    sections: list[DocumentSection] = []
    pos = 0
    section_idx = 0
    para_idx = 0

    for part in re.split(r"(\n[ \t]*\n)", text):
        if re.fullmatch(r"\n[ \t]*\n", part):
            pos += len(part)
            continue

        stripped = part.strip()
        if not stripped:
            pos += len(part)
            continue

        leading = len(part) - len(part.lstrip())
        start = pos + leading
        end = start + len(stripped)

        sections.append(DocumentSection(
            text=stripped,
            start_char=start,
            end_char=end,
            section_index=section_idx,
            paragraph_index=para_idx,
        ))
        section_idx += 1
        para_idx += 1
        pos += len(part)

    return sections
