"""Evidence card extraction from parsed document chunks.

Two extraction modes, chosen per-chunk:

1. STRUCTURED — for chunks produced by CARD N section splitting.
   Parses explicit `Tag:`, `Author:`, `Source:`, `Date:`, and
   `Claim supported:` fields.  Never invents missing values.

2. HEURISTIC — for generic paragraph chunks without explicit markers.
   Uses regex patterns to detect author names, years, known institutions,
   and TAG-style labels.

Safety rule: missing author / year / source remain None;
attribution_complete is False when either is absent.

Optional LLM call produces a one-sentence claim_summary for heuristic
cards where no "Claim supported:" line was found.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import openai
from pydantic import BaseModel

from app.config import settings
from app.services.document_parsing import TextChunk

logger = logging.getLogger(__name__)


# ── Minimum length constants ───────────────────────────────────────────────────

# Structured CARD sections can be short (body only, metadata stripped)
_MIN_CARD_CHARS_STRUCTURED = 40
# Unstructured heuristic chunks need more content to avoid extracting headings
_MIN_CARD_CHARS_HEURISTIC = 100


# ── Structured field patterns ──────────────────────────────────────────────────

# Matches "Tag:", "TAG:", "tag:" at the start of a line
_FIELD_TAG_RE = re.compile(r"^Tag\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_FIELD_AUTHOR_RE = re.compile(r"^Author\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_FIELD_SOURCE_RE = re.compile(r"^Source\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_FIELD_DATE_RE = re.compile(r"^Date\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)

# "Claim supported:" section — captures everything after the colon to end of text
_CLAIM_SUPPORTED_RE = re.compile(
    r"^Claim\s+supported\s*:\s*\n?(.*)",
    re.MULTILINE | re.IGNORECASE | re.DOTALL,
)

# Metadata field lines to remove when extracting the card body
_METADATA_LINE_RE = re.compile(
    r"^(?:Tag|Author|Source|Date)\s*:.*$\n?",
    re.MULTILINE | re.IGNORECASE,
)

# Detects a "CARD N" heading (used to choose extraction mode)
_CARD_HEADING_RE = re.compile(r"^CARD\s+\d+\s*$", re.IGNORECASE)


# ── Heuristic patterns (fallback for unstructured documents) ───────────────────

# Year: standalone 4-digit number in the range 1900–2099
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

# Author pattern: "Smith 2023", "Smith and Jones 2023", "Jones et al. 2023"
_AUTHOR_RE = re.compile(
    r"^([A-Z][a-zA-Z\-']{1,30}(?:\s+(?:and|&)\s+[A-Z][a-zA-Z\-']{1,30})?)"
    r"(?:,\s+[A-Z][a-z]+)?(?:\s+et\s+al\.?)?\s+"
    r"(?:(?:19|20)\d{2})",
    re.MULTILINE,
)

# TAG-style label lines
_TAG_RE = re.compile(
    r"(?:^TAG\s*:\s*(.+)$|^\[([^\]]+)\]$|^([A-Z][A-Z0-9\s\-]{2,60})\s*:)",
    re.MULTILINE | re.IGNORECASE,
)

# Known publication / institution names
_KNOWN_SOURCE_RE = re.compile(
    r"(?:Foreign Affairs|Journal of [A-Z]\w+|Brookings|RAND|Carnegie|Heritage|"
    r"Harvard|MIT|Stanford|Oxford|Nature|Science|Reuters|AP(?!\w)|BBC|"
    r"Washington Post|New York Times|Wall Street Journal|"
    r"International Security|American Economic Review|"
    r"Proceedings of|Policy Review|National Review|"
    r"Foreign Policy|CSIS|Peterson Institute|IMF|World Bank|"
    r"Congressional Research Service|CRS|CBO|GAO)",
    re.IGNORECASE,
)


# ── LLM claim summary ──────────────────────────────────────────────────────────

class _ClaimSummaryOutput(BaseModel):
    claim_summary: str
    """One sentence explaining exactly what this evidence supports. No invented facts."""


def _generate_claim_summary(card_text: str) -> Optional[str]:
    """Ask the LLM to summarize what this evidence actually supports.

    Strict constraint: do not use outside knowledge.
    Returns None if the LLM call fails or API key is absent.
    """
    if not settings.openai_api_key:
        return None

    prompt = (
        "You are reviewing a debate evidence card. "
        "Write ONE sentence explaining exactly what this evidence proves or supports, "
        "based ONLY on its text — do not add outside knowledge or invent claims.\n\n"
        f"Evidence card:\n{card_text[:1500]}"
    )

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format=_ClaimSummaryOutput,
            max_tokens=100,
        )
        result = response.choices[0].message.parsed
        return result.claim_summary if result else None
    except Exception as exc:
        logger.warning("evidence_extraction: claim_summary LLM failed | %s", exc)
        return None


# ── Card output type ───────────────────────────────────────────────────────────

class ExtractedCard:
    """An evidence card extracted from a document chunk (pre-DB insert)."""

    __slots__ = (
        "tag", "author", "source", "year",
        "card_text", "claim_summary", "attribution_complete",
        "chunk_index",
    )

    def __init__(
        self,
        *,
        tag: Optional[str],
        author: Optional[str],
        source: Optional[str],
        year: Optional[int],
        card_text: str,
        claim_summary: Optional[str],
        attribution_complete: bool,
        chunk_index: int,
    ) -> None:
        self.tag = tag
        self.author = author
        self.source = source
        self.year = year
        self.card_text = card_text
        self.claim_summary = claim_summary
        self.attribution_complete = attribution_complete
        self.chunk_index = chunk_index


# ── Structured extraction (CARD N chunks) ─────────────────────────────────────

def _body_from_structured(text: str) -> str:
    """Strip metadata field lines and 'Claim supported:' section; return card body."""
    body = _METADATA_LINE_RE.sub("", text)
    # Remove "Claim supported:" and everything after it
    body = re.sub(
        r"Claim\s+supported\s*:.*",
        "",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _extract_structured_card(
    text: str,
    heading: Optional[str],
    chunk_index: int,
) -> Optional[ExtractedCard]:
    """Extract from a structured 'CARD N'-format section.

    Parses explicit Tag/Author/Source/Date/Claim fields.
    Never invents missing values.
    """
    # ── Structured fields ──────────────────────────────────────────────────────
    m = _FIELD_TAG_RE.search(text)
    tag = m.group(1).strip() if m else None

    m = _FIELD_AUTHOR_RE.search(text)
    author = m.group(1).strip() if m else None

    m = _FIELD_SOURCE_RE.search(text)
    source = m.group(1).strip() if m else None

    m = _FIELD_DATE_RE.search(text)
    date_str = m.group(1).strip() if m else None

    # Year from Date field first, fallback to any year in text
    year: Optional[int] = None
    if date_str:
        ym = _YEAR_RE.search(date_str)
        if ym:
            year = int(ym.group(1))
    if year is None:
        ym = _YEAR_RE.search(text)
        if ym:
            year = int(ym.group(1))

    # ── Claim summary from "Claim supported:" ─────────────────────────────────
    claim_summary: Optional[str] = None
    m = _CLAIM_SUPPORTED_RE.search(text)
    if m:
        claim_summary = m.group(1).strip() or None

    # ── Card body (without metadata and claim lines) ───────────────────────────
    body = _body_from_structured(text)
    if not body:
        body = text  # fallback: keep the full text

    if len(body) < _MIN_CARD_CHARS_STRUCTURED and not (tag or author or source):
        return None

    attribution_complete = bool(author and year)

    return ExtractedCard(
        tag=tag,
        author=author,
        source=source,
        year=year,
        card_text=body,
        claim_summary=claim_summary,
        attribution_complete=attribution_complete,
        chunk_index=chunk_index,
    )


# ── Heuristic extraction (generic paragraph chunks) ───────────────────────────

def _extract_heuristic(
    text: str,
    heading: Optional[str],
    chunk_index: int,
) -> Optional[ExtractedCard]:
    """Heuristic extraction for chunks without explicit CARD markers."""
    if len(text) < _MIN_CARD_CHARS_HEURISTIC:
        return None

    # Tag
    tag: Optional[str] = None
    if heading:
        tag = heading.strip()
    else:
        m = _TAG_RE.search(text)
        if m:
            tag = (m.group(1) or m.group(2) or m.group(3) or "").strip() or None

    # Author
    author: Optional[str] = None
    m = _AUTHOR_RE.search(text)
    if m:
        author = m.group(1).strip()

    # Year
    year: Optional[int] = None
    m = _YEAR_RE.search(text)
    if m:
        year = int(m.group(1))

    # Source from known-institution list
    source: Optional[str] = None
    m = _KNOWN_SOURCE_RE.search(text)
    if m:
        source = m.group(0).strip()

    attribution_complete = bool(author and year)

    return ExtractedCard(
        tag=tag,
        author=author,
        source=source,
        year=year,
        card_text=text,
        claim_summary=None,  # LLM call happens later
        attribution_complete=attribution_complete,
        chunk_index=chunk_index,
    )


# ── Dispatcher ─────────────────────────────────────────────────────────────────

def _extract_from_chunk(chunk: TextChunk) -> Optional[ExtractedCard]:
    """Choose structured or heuristic extraction based on chunk heading."""
    text = chunk.chunk_text.strip()
    is_card_chunk = bool(
        chunk.heading and _CARD_HEADING_RE.match(chunk.heading.strip())
    )

    if is_card_chunk:
        return _extract_structured_card(text, chunk.heading, chunk.chunk_index)
    return _extract_heuristic(text, chunk.heading, chunk.chunk_index)


# ── Public entry point ─────────────────────────────────────────────────────────

def extract_evidence_cards(
    chunks: list[TextChunk],
    *,
    generate_summaries: bool = True,
) -> list[ExtractedCard]:
    """Extract evidence cards from a list of parsed chunks.

    For CARD-marker chunks: uses structured field parsing; claim_summary comes
    from the 'Claim supported:' field (no LLM call needed).

    For heuristic chunks: uses regex patterns; optionally calls the LLM to
    produce a claim_summary when generate_summaries=True.

    Safety: missing author / year / source remain None; never invented.
    """
    cards: list[ExtractedCard] = []

    for chunk in chunks:
        card = _extract_from_chunk(chunk)
        if card is None:
            continue

        # For heuristic cards without a claim summary, optionally call LLM
        is_card_chunk = bool(
            chunk.heading and _CARD_HEADING_RE.match(chunk.heading.strip())
        )
        if generate_summaries and not is_card_chunk and card.claim_summary is None:
            card.claim_summary = _generate_claim_summary(card.card_text)

        cards.append(card)
        logger.debug(
            "evidence_extraction: card | idx=%d tag=%r author=%r year=%s complete=%s",
            card.chunk_index,
            card.tag,
            card.author,
            card.year,
            card.attribution_complete,
        )

    logger.info(
        "evidence_extraction: done | chunks=%d cards=%d",
        len(chunks),
        len(cards),
    )
    return cards
