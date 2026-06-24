"""Structured citation models — Pass 12.

CitationRecord is the canonical internal representation for all evidence card
citations.  Rendered strings (MLA, APA, …) are derived from it; they are never
the source of truth.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field

# ── Confidence tiers ─────────────────────────────────────────────────────────
# Ordered weakest → strongest for precedence comparisons.
CONFIDENCE_UNKNOWN = "unknown"
CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"
CONFIDENCE_VERIFIED = "verified"

_CONFIDENCE_RANK: dict[str, int] = {
    CONFIDENCE_UNKNOWN: 0,
    CONFIDENCE_LOW: 1,
    CONFIDENCE_MEDIUM: 2,
    CONFIDENCE_HIGH: 3,
    CONFIDENCE_VERIFIED: 4,
}


def confidence_rank(tier: str) -> int:
    return _CONFIDENCE_RANK.get(tier, 0)


# ── Metadata source labels ───────────────────────────────────────────────────
SRC_USER_EDIT = "user_edit"
SRC_CROSSREF = "crossref"
SRC_OPENALEX = "openalex"
SRC_SEMANTIC_SCHOLAR = "semantic_scholar"
SRC_JSON_LD = "json_ld"
SRC_CITATION_META = "citation_meta"
SRC_OG = "og"
SRC_PDF_PARSER = "pdf_parser"
SRC_DOCX_PARSER = "docx_parser"
SRC_PROVIDER = "provider_metadata"
SRC_VISIBLE_TEXT = "visible_text"
SRC_URL = "url_inference"
SRC_DOMAIN = "domain_inference"
SRC_NONE = "none"

# Default confidence tier per source
_SOURCE_CONFIDENCE: dict[str, str] = {
    SRC_USER_EDIT: CONFIDENCE_VERIFIED,
    SRC_CROSSREF: CONFIDENCE_VERIFIED,
    SRC_OPENALEX: CONFIDENCE_HIGH,
    SRC_SEMANTIC_SCHOLAR: CONFIDENCE_HIGH,
    SRC_JSON_LD: CONFIDENCE_HIGH,
    SRC_CITATION_META: CONFIDENCE_HIGH,
    SRC_PDF_PARSER: CONFIDENCE_MEDIUM,
    SRC_DOCX_PARSER: CONFIDENCE_MEDIUM,
    SRC_OG: CONFIDENCE_MEDIUM,
    SRC_PROVIDER: CONFIDENCE_MEDIUM,
    SRC_VISIBLE_TEXT: CONFIDENCE_MEDIUM,
    SRC_URL: CONFIDENCE_LOW,
    SRC_DOMAIN: CONFIDENCE_LOW,
    SRC_NONE: CONFIDENCE_UNKNOWN,
}


def default_confidence(source: str) -> str:
    return _SOURCE_CONFIDENCE.get(source, CONFIDENCE_UNKNOWN)


# ── Source types (CSL-JSON compatible names) ─────────────────────────────────
STYPE_JOURNAL_ARTICLE = "article-journal"
STYPE_CONFERENCE = "paper-conference"
STYPE_BOOK = "book"
STYPE_CHAPTER = "chapter"
STYPE_REPORT = "report"
STYPE_GOV_REPORT = "government-report"
STYPE_WEBPAGE = "webpage"
STYPE_NEWS = "article-newspaper"
STYPE_MAGAZINE = "article-magazine"
STYPE_LEGAL_CASE = "legal_case"
STYPE_STATUTE = "legislation"
STYPE_DATASET = "dataset"
STYPE_THESIS = "thesis"
STYPE_WORKING_PAPER = "working-paper"
STYPE_DOCUMENT = "document"  # conservative fallback

_VALID_SOURCE_TYPES = {
    STYPE_JOURNAL_ARTICLE, STYPE_CONFERENCE, STYPE_BOOK, STYPE_CHAPTER,
    STYPE_REPORT, STYPE_GOV_REPORT, STYPE_WEBPAGE, STYPE_NEWS, STYPE_MAGAZINE,
    STYPE_LEGAL_CASE, STYPE_STATUTE, STYPE_DATASET, STYPE_THESIS,
    STYPE_WORKING_PAPER, STYPE_DOCUMENT,
}


def is_valid_source_type(t: str) -> bool:
    return t in _VALID_SOURCE_TYPES


# ── Citation completeness states ─────────────────────────────────────────────
COMPLETENESS_COMPLETE = "complete"
COMPLETENESS_USABLE = "usable_with_warnings"
COMPLETENESS_INCOMPLETE = "incomplete"
COMPLETENESS_UNVERIFIED = "unverified"


# ── Sub-models ───────────────────────────────────────────────────────────────

class CitationPerson(BaseModel):
    """A structured name for an author or editor."""
    given: str = ""
    family: str = ""
    literal: str = ""           # full name when parsing is impossible/org
    suffix: str = ""
    is_organization: bool = False

    def display_name(self) -> str:
        if self.is_organization:
            return self.literal or self.family or self.given
        if self.family and self.given:
            return f"{self.given} {self.family}"
        return self.literal or self.family or self.given

    def surname(self) -> str:
        """Return best surname-like label for short citation."""
        if self.is_organization:
            return self.literal or self.family
        if self.family:
            return self.family
        if self.literal:
            return self.literal.split()[-1]
        return self.given

    def mla_name(self) -> str:
        """'Last, First Suffix' per MLA 9."""
        if self.is_organization:
            return self.literal
        parts = [f"{self.family}, {self.given}".strip(", ")]
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(p for p in parts if p)

    def apa_name(self) -> str:
        """'Last, F. M.' per APA 7."""
        if self.is_organization:
            return self.literal
        given_initials = " ".join(
            p[0].upper() + "." for p in self.given.split() if p
        )
        base = self.family
        if given_initials:
            base += f", {given_initials}"
        if self.suffix:
            base += f" {self.suffix}"
        return base

    def bibtex_name(self) -> str:
        """'Family, Given' for BibTeX author field."""
        if self.is_organization:
            return "{" + self.literal + "}"
        if self.family and self.given:
            return f"{self.family}, {self.given}"
        return self.literal or self.family or self.given


class CitationDate(BaseModel):
    """A structured publication or access date."""
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    def display(self) -> str:
        if self.year and self.month and self.day:
            return f"{self.year}-{self.month:02d}-{self.day:02d}"
        if self.year and self.month:
            return f"{self.year}-{self.month:02d}"
        if self.year:
            return str(self.year)
        return ""

    def year_str(self) -> str:
        return str(self.year) if self.year else ""

    def mla_month_day(self) -> str:
        """'12 Jan.' style for MLA."""
        _MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
                   "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
        if self.month and 1 <= self.month <= 12:
            m = _MONTHS[self.month - 1]
            return f"{self.day} {m}" if self.day else m
        return ""

    @classmethod
    def from_string(cls, raw: str) -> "CitationDate":
        """Parse common date strings into a CitationDate."""
        if not raw:
            return cls()
        raw = raw.strip()
        # ISO: 2024-01-12
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', raw)
        if m:
            return cls(year=int(m.group(1)), month=int(m.group(2)), day=int(m.group(3)))
        # Year-month: 2024-01
        m = re.match(r'^(\d{4})-(\d{1,2})$', raw)
        if m:
            return cls(year=int(m.group(1)), month=int(m.group(2)))
        # Four-digit year anywhere
        m = re.search(r'\b(19|20)\d{2}\b', raw)
        if m:
            return cls(year=int(m.group(0)))
        return cls()

    def to_csl_date_parts(self) -> list[list[int]]:
        if self.year and self.month and self.day:
            return [[self.year, self.month, self.day]]
        if self.year and self.month:
            return [[self.year, self.month]]
        if self.year:
            return [[self.year]]
        return []


class FieldProvenance(BaseModel):
    """Provenance and confidence for one citation field."""
    source: str = SRC_NONE
    confidence: str = CONFIDENCE_UNKNOWN
    manually_edited: bool = False
    warning: str = ""

    def precedes(self, other: "FieldProvenance") -> bool:
        """Return True if self is more authoritative than other."""
        return confidence_rank(self.confidence) > confidence_rank(other.confidence)

    def is_reliable(self) -> bool:
        return confidence_rank(self.confidence) >= confidence_rank(CONFIDENCE_MEDIUM)


class CitationConflict(BaseModel):
    """A detected conflict between two metadata sources."""
    field: str
    selected_value: Any
    selected_source: str
    conflicting_value: Any
    conflicting_source: str
    message: str


# ── Core CitationRecord ──────────────────────────────────────────────────────

class CitationRecord(BaseModel):
    """Normalized, structured citation record — the internal source of truth.

    All rendered strings (MLA, APA, BibTeX, …) are computed FROM this record.
    Do not store rendered strings as the canonical citation.
    """
    # ── Source type
    source_type: str = STYPE_DOCUMENT   # CSL-JSON compatible
    source_type_confidence: str = CONFIDENCE_UNKNOWN

    # ── Authors / editors
    authors: list[CitationPerson] = []
    editors: list[CitationPerson] = []
    authors_prov: FieldProvenance = Field(default_factory=FieldProvenance)

    # ── Title fields
    title: str = ""
    title_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    container_title: str = ""           # journal, edited book, site name, series
    container_title_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    collection_title: str = ""          # series or book series

    # ── Publisher
    publisher: str = ""
    publisher_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    publisher_place: str = ""
    edition: str = ""

    # ── Issue identifiers
    volume: str = ""
    issue: str = ""
    page: str = ""
    article_number: str = ""

    # ── Dates
    issued: Optional[CitationDate] = None
    issued_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    accessed: Optional[CitationDate] = None

    # ── Identifiers
    doi: str = ""
    doi_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    url: str = ""
    url_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    canonical_url: str = ""

    # ── Legal / government
    court: str = ""
    case_name: str = ""
    docket_number: str = ""
    legislation_title: str = ""
    section: str = ""
    institution: str = ""       # also used for think tanks, universities
    institution_prov: FieldProvenance = Field(default_factory=FieldProvenance)
    report_number: str = ""
    jurisdiction: str = ""

    # ── Language
    language: str = ""

    # ── Quality state
    completeness: str = COMPLETENESS_INCOMPLETE
    conflicts: list[CitationConflict] = []
    warnings: list[str] = []
    citation_version: int = 1

    # ── Rendered cache (never source of truth — always re-derive from record)
    rendered_debate: str = ""
    rendered_mla: str = ""
    rendered_apa: str = ""
    rendered_chicago: str = ""
    rendered_bibtex: str = ""
    rendered_ris: str = ""

    def first_author_surname(self) -> str:
        if not self.authors:
            return ""
        return self.authors[0].surname()

    def year_str(self) -> str:
        return self.issued.year_str() if self.issued else ""

    def effective_publisher(self) -> str:
        """Container title for journals, publisher for books/reports."""
        return self.container_title or self.publisher or self.institution or ""

    def to_dict(self) -> dict:
        return self.model_dump()
