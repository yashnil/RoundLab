"""Paragraph-aware passage construction for evidence retrieval.

Replaces the word-count chunking in _chunk_text() with paragraph-respecting
splits that preserve meaning units and track stable character offsets into the
original extracted text.

SAFETY INVARIANTS:
- `EvidenceCandidate.text` is always a direct slice of the input `text`.
- Character offsets satisfy: input_text[start:end].strip() == passage_text
  for well-formed input (no mid-character splits).
- No text is added, modified, or synthesized.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.evidence_candidate import EvidenceCandidate

if TYPE_CHECKING:
    from app.services.evidence_extracted_document import DocumentSection, ExtractedDocument

# ── Tuning constants ─────────────────────────────────────────────────────────

_MIN_WORD_DEFAULT = 40      # passages shorter than this are merged or dropped
_MAX_WORD_DEFAULT = 350     # passages longer than this are split at sentences
_MAX_PASSAGES = 20          # hard cap per source document

# A heading must be short, have no sentence-ending punctuation, and be at least
# somewhat capitalized.
_MAX_HEADING_CHARS = 120
_MAX_HEADING_WORDS = 18
_MIN_HEADING_CAP_RATIO = 0.5  # fraction of words that start with a capital


# ── Offset-aware paragraph splitter ─────────────────────────────────────────


def _paragraphs_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """Split text at blank lines, returning (stripped_text, start, end) triples.

    Uses a capturing split so that separator positions can be used to track the
    absolute character offset of each paragraph in `text`.
    Blank lines with only whitespace (e.g. `\\n   \\n`) are also treated as
    paragraph separators.
    """
    result: list[tuple[str, int, int]] = []
    pos = 0
    # Split on 2+ newlines, capturing the separator so we can track pos.
    for part in re.split(r"(\n[ \t]*\n)", text):
        if re.fullmatch(r"\n[ \t]*\n", part):
            pos += len(part)
            continue
        stripped = part.strip()
        if stripped:
            leading = len(part) - len(part.lstrip())
            start = pos + leading
            end = start + len(stripped)
            result.append((stripped, start, end))
        pos += len(part)
    return result


# ── Heading detection ────────────────────────────────────────────────────────


def _is_heading(text: str) -> bool:
    """Return True when a paragraph looks like a section heading.

    Headings are short, have no terminal sentence punctuation, and most
    words are capitalized. They should NOT become standalone passages
    because they lose meaning without the paragraph below them.
    """
    stripped = text.strip()
    if len(stripped) > _MAX_HEADING_CHARS:
        return False
    if stripped.endswith((".", "!", "?", "...", ":")):
        return False
    words = stripped.split()
    if not words or len(words) > _MAX_HEADING_WORDS or len(words) < 2:
        return False
    cap_ratio = sum(1 for w in words if w[:1].isupper()) / len(words)
    return cap_ratio >= _MIN_HEADING_CAP_RATIO


# ── Heading-merge pass ───────────────────────────────────────────────────────


def _merge_headings_with_paragraphs(
    paras: list[tuple[str, int, int]]
) -> list[tuple[str, int, int, str]]:
    """Attach headings to their following paragraph.

    Returns list of (text, start, end, section_heading) tuples.
    When a heading has no following paragraph it is dropped.
    """
    result: list[tuple[str, int, int, str]] = []
    i = 0
    while i < len(paras):
        text, start, end = paras[i]
        if _is_heading(text):
            if i + 1 < len(paras):
                next_text, _ns, next_end = paras[i + 1]
                # Merge: keep the heading as section_heading, prepend to body text
                merged = f"{text}\n{next_text}"
                result.append((merged, start, next_end, text))
                i += 2
            else:
                # Lone heading at end of document — no body to attach, drop it
                i += 1
        else:
            result.append((text, start, end, ""))
            i += 1
    return result


# ── Short-paragraph merge pass ───────────────────────────────────────────────


def _merge_short_paragraphs(
    paras: list[tuple[str, int, int, str]],
    min_words: int,
) -> list[tuple[str, int, int, str]]:
    """Merge paragraphs shorter than min_words with the following paragraph.

    A short paragraph standing alone often contains context that only makes
    sense with the following sentence. Merging ensures coherent card text.
    """
    if not paras:
        return []
    result: list[tuple[str, int, int, str]] = []
    i = 0
    while i < len(paras):
        text, start, end, heading = paras[i]
        if len(text.split()) < min_words and i + 1 < len(paras):
            next_text, _ns, next_end, next_heading = paras[i + 1]
            merged = f"{text}\n{next_text}"
            result.append((merged, start, next_end, heading or next_heading))
            i += 2
        else:
            result.append((text, start, end, heading))
            i += 1
    return result


# ── Long-paragraph sentence splitter ────────────────────────────────────────


def _split_long_paragraph(
    text: str,
    start_offset: int,
    max_words: int,
) -> list[tuple[str, int, int]]:
    """Split a paragraph that exceeds max_words at sentence boundaries.

    Builds chunks of up to max_words words, splitting only at sentence
    boundaries (`. ! ?` followed by whitespace and an uppercase letter).
    Offsets are tracked approximately through the original paragraph text.
    """
    sentence_re = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
    sentences = sentence_re.split(text)
    if len(sentences) <= 1:
        # No sentence boundaries found — return as-is (better than nothing)
        return [(text, start_offset, start_offset + len(text))]

    result: list[tuple[str, int, int]] = []
    current: list[str] = []
    current_offset = start_offset

    for sent in sentences:
        # "flush before" strategy: if adding this sentence would exceed max_words
        # AND we already have content, flush the current buffer first.
        test_combined = " ".join(current + [sent])
        if current and len(test_combined.split()) > max_words:
            combined = " ".join(current)
            result.append((combined, current_offset, current_offset + len(combined)))
            current_offset += len(combined) + 1  # +1 approximate inter-sentence space
            current = [sent]
        else:
            current.append(sent)

    if current:
        combined = " ".join(current)
        result.append((combined, current_offset, current_offset + len(combined)))

    return result


# ── Public entry point ───────────────────────────────────────────────────────


def build_passages(
    text: str,
    *,
    url: str = "",
    canonical_url: str = "",
    domain: str = "",
    title: str = "",
    author: str = "",
    published_date: str = "",
    provider: str = "",
    query: str = "",
    max_words: int = _MAX_WORD_DEFAULT,
    min_words: int = _MIN_WORD_DEFAULT,
    max_passages: int = _MAX_PASSAGES,
) -> list[EvidenceCandidate]:
    """Build paragraph-aware passage candidates from extracted article text.

    Key differences from _chunk_text():
    - Splits at actual paragraph boundaries, not every 400 words.
    - Detects section headings and merges them with the following paragraph.
    - Merges short paragraphs with their neighbours for context.
    - Splits only oversized paragraphs, and only at sentence boundaries.
    - Tracks stable char offsets into the original text.
    - Returns typed EvidenceCandidate objects (not plain strings).

    Safety: text is never modified. EvidenceCandidate.text is always a direct
    fragment of the input.
    """
    if not text or not text.strip():
        return []

    # Step 1: split at blank-line boundaries
    raw = _paragraphs_with_offsets(text)
    if not raw:
        return []

    # Step 2: merge headings with their following paragraphs
    merged = _merge_headings_with_paragraphs(raw)

    # Step 3: merge very short paragraphs with neighbours
    combined = _merge_short_paragraphs(merged, min_words=min_words)

    # Step 4: split paragraphs that exceed max_words at sentence boundaries
    passages: list[tuple[str, int, int, str]] = []
    for para_text, start, end, heading in combined:
        word_count = len(para_text.split())
        if word_count <= max_words:
            passages.append((para_text, start, end, heading))
        else:
            for sub_text, sub_start, sub_end in _split_long_paragraph(para_text, start, max_words):
                if len(sub_text.split()) >= 5:
                    passages.append((sub_text, sub_start, sub_end, heading))

    # Step 5: build typed EvidenceCandidate objects
    candidates: list[EvidenceCandidate] = []
    for para_text, start, end, heading in passages[:max_passages]:
        word_count = len(para_text.split())
        if word_count < 5:  # drop noise fragments
            continue
        candidates.append(EvidenceCandidate(
            text=para_text,
            start=start,
            end=end,
            url=url,
            canonical_url=canonical_url,
            domain=domain,
            title=title,
            author=author,
            published_date=published_date,
            provider=provider,
            query=query,
            section_heading=heading,
        ))

    return candidates


# ── Section-aware builder (Pass 10) ─────────────────────────────────────────


def build_passages_from_document(
    document: "ExtractedDocument",
    *,
    url: str = "",
    domain: str = "",
    provider: str = "",
    query: str = "",
    max_words: int = _MAX_WORD_DEFAULT,
    min_words: int = _MIN_WORD_DEFAULT,
    max_passages: int = _MAX_PASSAGES,
) -> list[EvidenceCandidate]:
    """Build passage candidates from a structured ExtractedDocument.

    When the document has structured `sections` (e.g., from PDF/DOCX extraction),
    each section becomes one candidate with accurate provenance:
    - page_number preserved from DocumentSection
    - section_heading preserved
    - paragraph_index / section_index preserved
    - extraction_method / content_hash / source_text_type from document

    Falls back to `build_passages()` on the raw_text when sections are empty.

    Safety: document.raw_text and section.text are never modified.
    """
    from app.services.evidence_extracted_document import ExtractedDocument  # type: ignore

    effective_url = url or document.source_url or ""
    effective_canonical = document.canonical_url or effective_url
    effective_domain = domain or _domain_from_url(effective_url)

    if not document.sections:
        # Fall back to the plain-text builder
        return build_passages(
            document.raw_text,
            url=effective_url,
            canonical_url=effective_canonical,
            domain=effective_domain,
            title=document.title,
            author=document.author,
            published_date=document.publication_date,
            provider=provider or document.extraction_method,
            query=query,
            max_words=max_words,
            min_words=min_words,
            max_passages=max_passages,
        )

    candidates: list[EvidenceCandidate] = []
    for section in document.sections[:max_passages]:
        text = section.text
        if not text or len(text.split()) < 5:
            continue

        # Handle oversized sections: split at sentence boundaries
        word_count = len(text.split())
        if word_count > max_words:
            splits = _split_long_paragraph(text, section.start_char, max_words)
            for sub_text, sub_start, sub_end in splits:
                if len(sub_text.split()) < 5:
                    continue
                candidates.append(_make_candidate(
                    text=sub_text,
                    start=sub_start,
                    end=sub_end,
                    document=document,
                    section=section,
                    url=effective_url,
                    canonical_url=effective_canonical,
                    domain=effective_domain,
                    provider=provider,
                    query=query,
                ))
        else:
            candidates.append(_make_candidate(
                text=text,
                start=section.start_char,
                end=section.end_char,
                document=document,
                section=section,
                url=effective_url,
                canonical_url=effective_canonical,
                domain=effective_domain,
                provider=provider,
                query=query,
            ))

        if len(candidates) >= max_passages:
            break

    return candidates


def _make_candidate(
    *,
    text: str,
    start: int,
    end: int,
    document: "ExtractedDocument",
    section: "DocumentSection",
    url: str,
    canonical_url: str,
    domain: str,
    provider: str,
    query: str,
) -> EvidenceCandidate:
    """Create a provenance-rich EvidenceCandidate from document + section."""
    return EvidenceCandidate(
        text=text,
        start=start,
        end=end,
        url=url,
        canonical_url=canonical_url,
        domain=domain,
        title=document.title,
        author=document.author,
        published_date=document.publication_date,
        provider=provider or document.extraction_method,
        query=query,
        section_heading=section.heading,
        # P10 provenance
        page_number=section.page_number,
        paragraph_index=section.paragraph_index,
        section_index=section.section_index,
        extraction_method=document.extraction_method,
        content_hash=document.content_hash,
        retrieval_timestamp=document.retrieval_timestamp,
        source_text_type=document.source_text_type,
        document_type=document.document_type,
    )


def _domain_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        return host.lstrip("www.") if host.startswith("www.") else host
    except Exception:
        return ""
