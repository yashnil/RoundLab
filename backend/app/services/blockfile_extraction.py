"""
Deterministic block/frontline entry extractor.

Parses debate-format text for sections starting with:
  AT: / A/T: / Answer to: / Block: / Frontline: / Turn: /
  Defense: / Weighing: / Overview:

Sub-fields parsed within each section:
  Tag: / Response: / Warrant: / Evidence: / Impact: / Weighing:

Falls back to heading-based chunk entries for unstructured files.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

from app.models.document import DocumentChunkRow
from app.models.blockfile import BlockEntryCreate


# ── Regex patterns ────────────────────────────────────────────────────────────

# Section header patterns — each maps (regex, entry_type)
_SECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'^\s*(?:AT|A/T|Answer\s+to)\s*:\s*(.+)', re.IGNORECASE), "block"),
    (re.compile(r'^\s*Block\s*:\s*(.+)',                   re.IGNORECASE), "block"),
    (re.compile(r'^\s*Frontline\s*[-—:]\s*(.+)',           re.IGNORECASE), "frontline"),
    (re.compile(r'^\s*Turn\s*:\s*(.+)',                    re.IGNORECASE), "turn"),
    (re.compile(r'^\s*Defense\s*:\s*(.+)',                 re.IGNORECASE), "defense"),
    (re.compile(r'^\s*Weighing\s*[-—:]\s*(.*)',            re.IGNORECASE), "weighing"),
    (re.compile(r'^\s*Overview\s*[-—:]\s*(.*)',            re.IGNORECASE), "overview"),
]

# Sub-field patterns inside a section
_SUB_FIELDS: dict[str, re.Pattern[str]] = {
    "tag":      re.compile(r'^\s*Tag\s*:\s*(.+)',      re.IGNORECASE),
    "response": re.compile(r'^\s*Response\s*:\s*(.+)', re.IGNORECASE),
    "warrant":  re.compile(r'^\s*Warrant\s*:\s*(.+)',  re.IGNORECASE),
    "evidence": re.compile(r'^\s*Evidence\s*:\s*(.+)', re.IGNORECASE),
    "impact":   re.compile(r'^\s*Impact\s*:\s*(.+)',   re.IGNORECASE),
    "weighing": re.compile(r'^\s*Weighing\s*:\s*(.+)', re.IGNORECASE),
    "author":   re.compile(r'^\s*Author\s*:\s*(.+)',   re.IGNORECASE),
    "source":   re.compile(r'^\s*Source\s*:\s*(.+)',   re.IGNORECASE),
    "date":     re.compile(r'^\s*Date\s*:\s*(.+)',     re.IGNORECASE),
}

_DASH_HEADING = re.compile(
    r'^\s*(?:AT|A/T|Answer to|Block|Frontline|Turn|Defense|Weighing|Overview)'
    r'\s*[-—:]\s*(.+)',
    re.IGNORECASE,
)


@dataclass
class _Section:
    entry_type: str
    opponent_claim: str
    lines: list[str] = field(default_factory=list)
    chunk_id: Optional[str] = None


def _detect_section_header(line: str) -> Optional[tuple[str, str]]:
    """Return (entry_type, label_text) if line matches a section header."""
    for pattern, etype in _SECTION_PATTERNS:
        m = pattern.match(line)
        if m:
            label = m.group(1).strip().strip(":")
            return etype, label
    return None


def _parse_section_to_entry(section: _Section, user_id: str,
                             document_id: Optional[str],
                             topic: Optional[str],
                             side: Optional[str]) -> Optional[BlockEntryCreate]:
    """Convert a parsed section into a BlockEntryCreate."""
    text = "\n".join(section.lines).strip()
    if len(text) < 20:
        return None

    # Parse sub-fields
    sub: dict[str, list[str]] = {k: [] for k in _SUB_FIELDS}
    current_sub: Optional[str] = None
    remainder: list[str] = []

    for raw_line in section.lines:
        matched = False
        for field_name, pat in _SUB_FIELDS.items():
            m = pat.match(raw_line)
            if m:
                current_sub = field_name
                sub[field_name].append(m.group(1).strip())
                matched = True
                break
        if not matched:
            stripped = raw_line.strip()
            if stripped:
                if current_sub:
                    sub[current_sub].append(stripped)
                else:
                    remainder.append(stripped)

    def _join(key: str) -> Optional[str]:
        val = " ".join(sub[key]).strip()
        return val or None

    response_text = (
        _join("response")
        or (text[:2000] if not any(sub.values()) else None)
        or " ".join(remainder).strip()
        or text[:2000]
    )

    tag = _join("tag") or section.opponent_claim[:120]

    return BlockEntryCreate(
        user_id=user_id,
        document_id=document_id,
        source_chunk_id=section.chunk_id,
        entry_type=section.entry_type,
        side=side,
        tag=tag,
        opponent_claim=section.opponent_claim[:500] if section.opponent_claim else None,
        response_text=response_text[:4000],
        warrant_text=_join("warrant"),
        evidence_text=_join("evidence"),
        impact_text=_join("impact"),
        weighing_text=_join("weighing"),
        author=_join("author"),
        source=_join("source"),
        date=_join("date"),
        topic=topic,
    )


def _extract_structured(
    full_text: str,
    user_id: str,
    document_id: Optional[str],
    topic: Optional[str],
    side: Optional[str],
) -> list[BlockEntryCreate]:
    """Line-by-line scan for section headers."""
    entries: list[BlockEntryCreate] = []
    current: Optional[_Section] = None

    for raw_line in full_text.splitlines():
        result = _detect_section_header(raw_line)
        if result:
            # Close previous section
            if current is not None:
                entry = _parse_section_to_entry(current, user_id, document_id, topic, side)
                if entry:
                    entries.append(entry)
            current = _Section(entry_type=result[0], opponent_claim=result[1])
        elif current is not None:
            current.lines.append(raw_line)

    # Close last section
    if current is not None:
        entry = _parse_section_to_entry(current, user_id, document_id, topic, side)
        if entry:
            entries.append(entry)

    return entries


def _extract_from_chunks(
    chunks: list[DocumentChunkRow],
    user_id: str,
    document_id: Optional[str],
    inferred_role: str,
    topic: Optional[str],
    side: Optional[str],
) -> list[BlockEntryCreate]:
    """Fallback: treat each chunk as one entry when no structured sections found."""
    entries: list[BlockEntryCreate] = []
    for chunk in chunks:
        text = chunk.chunk_text.strip()
        if len(text) < 40:
            continue

        # Try to detect a section header in chunk heading
        heading = chunk.heading or ""
        entry_type = "unknown"
        opponent_claim = heading[:120] if heading else ""

        if heading:
            result = _detect_section_header(heading)
            if result:
                entry_type, opponent_claim = result[0], result[1]
            elif re.search(r'\b(?:block|frontline|AT)\b', heading, re.IGNORECASE):
                entry_type = "block" if re.search(r'\bat\b|block', heading, re.IGNORECASE) else "frontline"
                opponent_claim = heading.strip()

        # Determine entry_type from inferred document role
        if entry_type == "unknown" and inferred_role in ("blockfile", "frontline"):
            entry_type = "frontline" if inferred_role == "frontline" else "block"

        entries.append(BlockEntryCreate(
            user_id=user_id,
            document_id=document_id,
            source_chunk_id=chunk.id if hasattr(chunk, "id") else None,
            entry_type=entry_type,
            side=side,
            tag=opponent_claim[:120] if opponent_claim else None,
            opponent_claim=opponent_claim[:500] if opponent_claim else None,
            response_text=text[:4000],
            topic=topic,
        ))

    return entries


def extract_block_entries(
    chunks: list[DocumentChunkRow],
    full_text: str,
    user_id: str,
    document_id: Optional[str] = None,
    document_role: Optional[str] = None,
    topic: Optional[str] = None,
    side: Optional[str] = None,
) -> list[BlockEntryCreate]:
    """
    Main entry point. Tries structured parsing first, falls back to chunk-based.

    Args:
        chunks: Parsed chunks from the document (already in DB).
        full_text: Full concatenated document text.
        user_id: Owner's user_id.
        document_id: FK to documents table.
        document_role: Hint about role ('blockfile', 'frontline', 'mixed', etc.).
        topic: Optional topic tag to store on each entry.
        side: Optional debate side ('pro', 'con', etc.).

    Returns:
        List of BlockEntryCreate objects ready for insertion.
    """
    # Determine inferred role for fallback
    inferred_role = document_role or "mixed"

    # Try structured line-by-line parse on the full text
    structured = _extract_structured(full_text, user_id, document_id, topic, side)
    if structured:
        return structured

    # Try structured parse on chunk text as well (some parsers join differently)
    chunk_full = "\n".join(c.chunk_text for c in chunks)
    if chunk_full != full_text:
        structured = _extract_structured(chunk_full, user_id, document_id, topic, side)
        if structured:
            return structured

    # Fallback: chunk-based entries
    return _extract_from_chunks(chunks, user_id, document_id, inferred_role, topic, side)


def build_embedding_text(entry: BlockEntryCreate) -> str:
    """Build the text to embed for a block entry. Used for semantic search."""
    parts = [
        entry.tag or "",
        entry.opponent_claim or "",
        entry.response_text or "",
        entry.warrant_text or "",
        entry.evidence_text or "",
        entry.impact_text or "",
        entry.weighing_text or "",
    ]
    return " ".join(p.strip() for p in parts if p.strip())[:8000]
