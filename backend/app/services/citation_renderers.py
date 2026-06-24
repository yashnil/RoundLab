"""Citation renderers — Pass 12.

Renders a CitationRecord into multiple citation formats.
All renderers are deterministic fallbacks — no external library required.

Formats supported:
  * debate   — RoundLab compact debate citation
  * mla      — MLA 9th edition
  * apa      — APA 7th edition
  * chicago  — Chicago 17th author-date
  * bibtex   — BibTeX
  * ris      — RIS
  * csl_json — CSL-JSON dict

Rendered strings are cached on the CitationRecord but are NEVER
the source of truth.  Always re-render from the record.
"""
from __future__ import annotations

import json
import re
from datetime import date as _date
from typing import Optional

from app.models.citation import (
    CONFIDENCE_HIGH,
    CONFIDENCE_VERIFIED,
    CitationDate,
    CitationPerson,
    CitationRecord,
    STYPE_BOOK,
    STYPE_CHAPTER,
    STYPE_CONFERENCE,
    STYPE_DATASET,
    STYPE_DOCUMENT,
    STYPE_GOV_REPORT,
    STYPE_JOURNAL_ARTICLE,
    STYPE_LEGAL_CASE,
    STYPE_MAGAZINE,
    STYPE_NEWS,
    STYPE_REPORT,
    STYPE_STATUTE,
    STYPE_THESIS,
    STYPE_WEBPAGE,
    STYPE_WORKING_PAPER,
    confidence_rank,
)

# ── helpers ─────────────────────────────────────────────────────────────────

def _today() -> str:
    return _date.today().strftime("%d %b. %Y")


def _accessed_phrase(record: CitationRecord) -> str:
    if record.accessed and record.accessed.year:
        return f"Accessed {record.accessed.display()}."
    return f"Accessed {_today()}."


def _vol_issue(record: CitationRecord) -> str:
    parts = []
    if record.volume:
        parts.append(f"vol. {record.volume}")
    if record.issue:
        parts.append(f"no. {record.issue}")
    return ", ".join(parts)


def _doi_url(record: CitationRecord) -> str:
    if record.doi:
        return f"https://doi.org/{record.doi}"
    return record.canonical_url or record.url or ""


def _clean(s: str) -> str:
    return s.strip().rstrip(".")


# ── Debate citation ───────────────────────────────────────────────────────────

def render_debate(record: CitationRecord) -> str:
    """RoundLab compact debate citation for card headers.

    Format:  Surname Year — Institution, Container/Publication
    Rules:
    * Only include institution/qualification when confidence >= high.
    * Never fabricate qualifications.
    * Organization authors appear as-is.
    """
    parts: list[str] = []

    # Author portion
    if record.authors:
        first = record.authors[0]
        if first.is_organization:
            label = first.literal or first.family
        else:
            label = first.surname()
            if len(record.authors) == 2:
                label += f" & {record.authors[1].surname()}"
            elif len(record.authors) > 2:
                label += " et al."
        parts.append(label)
    elif record.institution and confidence_rank(record.institution_prov.confidence) >= confidence_rank(CONFIDENCE_HIGH):
        parts.append(record.institution)

    # Year
    year = record.year_str()
    if year:
        parts.append(year)
    elif not parts:
        parts.append("n.d.")

    prefix = " ".join(parts) if parts else "Source"

    # Qualification / institution separator
    qual_parts: list[str] = []

    # Only include institution when reliably sourced
    inst_prov = record.institution_prov
    if record.institution and confidence_rank(inst_prov.confidence) >= confidence_rank(CONFIDENCE_HIGH):
        qual_parts.append(record.institution)

    # Container title (journal, publication)
    if record.container_title:
        qual_parts.append(record.container_title)
    elif record.publisher and not record.institution:
        qual_parts.append(record.publisher)

    if qual_parts:
        return f"{prefix} — {', '.join(qual_parts)}"
    return prefix


# ── MLA 9th edition ───────────────────────────────────────────────────────────

def _mla_author_block(persons: list[CitationPerson]) -> str:
    if not persons:
        return ""
    if len(persons) == 1:
        return persons[0].mla_name() + "."
    if len(persons) == 2:
        return f"{persons[0].mla_name()}, and {persons[1].display_name()}."
    return f"{persons[0].mla_name()}, et al."


def render_mla(record: CitationRecord) -> str:
    """MLA 9th edition."""
    parts: list[str] = []

    author_block = _mla_author_block(record.authors)
    if author_block:
        parts.append(author_block)

    # Title
    title = record.title or record.legislation_title or record.case_name
    if title:
        st = record.source_type
        if st in (STYPE_BOOK, STYPE_THESIS, STYPE_GOV_REPORT, STYPE_REPORT):
            parts.append(f"*{title}*.")  # italics in plain text → asterisks
        else:
            parts.append(f'"{_clean(title)}."')

    # Container / publication
    ct = record.container_title
    if ct:
        parts.append(f"*{ct}*,")

    # Volume / issue
    vi = _vol_issue(record)
    if vi:
        parts.append(f"{vi},")

    # Year
    year = record.year_str()
    if year:
        mla_date = record.mla_date_str()
        parts.append(f"{mla_date},")

    # Pages
    if record.page:
        parts.append(f"pp. {record.page}.")

    # URL / DOI
    link = _doi_url(record)
    if link:
        parts.append(link + ".")

    # Accessed date (webpages or no author)
    if record.source_type in (STYPE_WEBPAGE, STYPE_NEWS, STYPE_MAGAZINE) or not record.authors:
        parts.append(_accessed_phrase(record))

    raw = " ".join(parts).replace(",.", ".").replace(",,", ",").strip()
    if not raw:
        # Hard fallback
        fallback = record.container_title or record.publisher or "Source"
        raw = f"{fallback}."
        if link:
            raw += f" {link}."
        raw += f" {_accessed_phrase(record)}"
    return raw


def _mla_date_str(record: CitationRecord) -> str:
    if not record.issued:
        return ""
    md = record.issued.mla_month_day()
    if md and record.issued.year:
        return f"{md} {record.issued.year}"
    return record.issued.year_str()


# Monkey-patch onto record for convenience
CitationRecord.mla_date_str = _mla_date_str  # type: ignore[attr-defined]


# ── APA 7th edition ───────────────────────────────────────────────────────────

def _apa_author_block(persons: list[CitationPerson]) -> str:
    if not persons:
        return ""
    if len(persons) == 1:
        return persons[0].apa_name()
    if len(persons) == 2:
        return f"{persons[0].apa_name()}, & {persons[1].apa_name()}"
    if len(persons) <= 20:
        names = ", ".join(p.apa_name() for p in persons[:-1])
        return f"{names}, & {persons[-1].apa_name()}"
    # > 20: first 19 + ellipsis + last
    first19 = ", ".join(p.apa_name() for p in persons[:19])
    return f"{first19}, . . . {persons[-1].apa_name()}"


def render_apa(record: CitationRecord) -> str:
    """APA 7th edition."""
    parts: list[str] = []

    # Authors
    ab = _apa_author_block(record.authors)
    if ab:
        parts.append(ab)

    # Year
    year = record.year_str()
    if year:
        parts.append(f"({year}).")
    else:
        parts.append("(n.d.).")

    # Title (sentence case for articles; title case for books)
    title = record.title or record.legislation_title or record.case_name
    if title:
        st = record.source_type
        if st in (STYPE_BOOK, STYPE_THESIS, STYPE_GOV_REPORT, STYPE_REPORT, STYPE_WORKING_PAPER):
            # italicize; keep title case
            parts.append(f"*{title}*.")
        else:
            parts.append(f"{title}.")

    # Source
    ct = record.container_title
    if ct:
        vi_str = ""
        if record.volume:
            vi_str = f", *{record.volume}*"
            if record.issue:
                vi_str += f"({record.issue})"
        page_str = f", {record.page}" if record.page else ""
        parts.append(f"*{ct}*{vi_str}{page_str}.")

    elif record.publisher:
        parts.append(f"{record.publisher}.")

    # DOI / URL
    doi = record.doi
    if doi:
        parts.append(f"https://doi.org/{doi}")
    elif record.url:
        parts.append(record.url)

    raw = " ".join(parts).replace("..", ".").strip()
    return raw or "Source (n.d.)."


# ── Chicago 17th author-date ──────────────────────────────────────────────────

def _chicago_author_block(persons: list[CitationPerson]) -> str:
    if not persons:
        return ""
    if len(persons) == 1:
        return persons[0].mla_name()  # "Last, First"
    if len(persons) <= 3:
        first = persons[0].mla_name()
        rest = ", and ".join(p.display_name() for p in persons[1:])
        return f"{first}, and {rest}"
    first = persons[0].mla_name()
    return f"{first} et al."


def render_chicago(record: CitationRecord) -> str:
    """Chicago 17th edition author-date style."""
    parts: list[str] = []

    ab = _chicago_author_block(record.authors)
    if ab:
        parts.append(ab + ".")

    year = record.year_str()
    if year:
        parts.append(f"{year}.")

    title = record.title or record.legislation_title or record.case_name
    if title:
        st = record.source_type
        if st in (STYPE_BOOK, STYPE_THESIS, STYPE_REPORT, STYPE_GOV_REPORT):
            parts.append(f"*{title}*.")
        else:
            parts.append(f'"{title}."')

    ct = record.container_title
    if ct:
        vi_str = ""
        if record.volume:
            vi_str = f" {record.volume}"
            if record.issue:
                vi_str += f", no. {record.issue}"
        page_str = f": {record.page}" if record.page else ""
        parts.append(f"*{ct}*{vi_str}{page_str}.")

    elif record.publisher:
        parts.append(f"{record.publisher}.")

    doi = record.doi
    if doi:
        parts.append(f"https://doi.org/{doi}.")
    elif record.url:
        parts.append(f"{record.url}.")

    raw = " ".join(parts).replace("..", ".").strip()
    return raw or "Source."


# ── BibTeX ────────────────────────────────────────────────────────────────────

def _bibtex_escape(s: str) -> str:
    return s.replace("{", "{{").replace("}", "}}").replace("&", "\\&").replace("%", "\\%")


def citation_key(record: CitationRecord) -> str:
    """Deterministic BibTeX citation key: first_surname + year + first_title_word."""
    surname = record.first_author_surname() or ""
    # Strip non-alphanum
    surname = re.sub(r'[^a-zA-Z0-9]', '', surname.lower())[:15]
    year = record.year_str()
    title_word = ""
    if record.title:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', record.title)
        title_word = re.sub(r'[^a-zA-Z0-9]', '', words[0].lower()) if words else ""
    key = f"{surname}{year}{title_word}" or "unknown"
    return key[:40]


_BIBTEX_TYPE_MAP: dict[str, str] = {
    STYPE_JOURNAL_ARTICLE: "article",
    STYPE_CONFERENCE: "inproceedings",
    STYPE_BOOK: "book",
    STYPE_CHAPTER: "incollection",
    STYPE_REPORT: "techreport",
    STYPE_GOV_REPORT: "techreport",
    STYPE_WEBPAGE: "misc",
    STYPE_NEWS: "misc",
    STYPE_MAGAZINE: "misc",
    STYPE_LEGAL_CASE: "misc",
    STYPE_STATUTE: "misc",
    STYPE_DATASET: "misc",
    STYPE_THESIS: "phdthesis",
    STYPE_WORKING_PAPER: "unpublished",
    STYPE_DOCUMENT: "misc",
}


def render_bibtex(record: CitationRecord) -> str:
    """BibTeX entry."""
    btype = _BIBTEX_TYPE_MAP.get(record.source_type, "misc")
    key = citation_key(record)
    fields: list[str] = []

    def _field(name: str, val: str) -> None:
        if val:
            fields.append(f"  {name} = {{{_bibtex_escape(val)}}}")

    # Authors
    if record.authors:
        author_str = " and ".join(p.bibtex_name() for p in record.authors)
        fields.append(f"  author = {{{_bibtex_escape(author_str)}}}")

    _field("title", record.title or record.legislation_title or record.case_name)
    _field("journal", record.container_title if btype == "article" else "")
    _field("booktitle", record.container_title if btype in ("inproceedings", "incollection") else "")
    _field("publisher", record.publisher)
    _field("institution", record.institution if btype == "techreport" else "")
    _field("school", record.institution if btype == "phdthesis" else "")
    _field("year", record.year_str())
    _field("volume", record.volume)
    _field("number", record.issue)
    _field("pages", record.page.replace("-", "--") if record.page else "")
    _field("doi", record.doi)
    _field("url", record.url)
    _field("note", record.report_number if btype == "techreport" else "")

    lines = [f"@{btype}{{{key},"] + [f + "," for f in fields] + ["}"]
    return "\n".join(lines)


# ── RIS ───────────────────────────────────────────────────────────────────────

_RIS_TYPE_MAP: dict[str, str] = {
    STYPE_JOURNAL_ARTICLE: "JOUR",
    STYPE_CONFERENCE: "CONF",
    STYPE_BOOK: "BOOK",
    STYPE_CHAPTER: "CHAP",
    STYPE_REPORT: "RPRT",
    STYPE_GOV_REPORT: "RPRT",
    STYPE_WEBPAGE: "ELEC",
    STYPE_NEWS: "NEWS",
    STYPE_MAGAZINE: "MGZN",
    STYPE_LEGAL_CASE: "CASE",
    STYPE_STATUTE: "STAT",
    STYPE_DATASET: "DATA",
    STYPE_THESIS: "THES",
    STYPE_WORKING_PAPER: "UNPB",
    STYPE_DOCUMENT: "GEN",
}


def render_ris(record: CitationRecord) -> str:
    """RIS format."""
    ris_type = _RIS_TYPE_MAP.get(record.source_type, "GEN")
    lines: list[str] = [f"TY  - {ris_type}"]

    for person in record.authors:
        lines.append(f"AU  - {person.mla_name()}")

    if record.title:
        lines.append(f"TI  - {record.title}")
    if record.legislation_title:
        lines.append(f"TI  - {record.legislation_title}")
    if record.container_title:
        lines.append(f"JO  - {record.container_title}")
    if record.publisher:
        lines.append(f"PB  - {record.publisher}")
    if record.institution:
        lines.append(f"AD  - {record.institution}")
    if record.volume:
        lines.append(f"VL  - {record.volume}")
    if record.issue:
        lines.append(f"IS  - {record.issue}")
    if record.page:
        sp, ep = (record.page.split("-") + [""])[:2]
        lines.append(f"SP  - {sp.strip()}")
        if ep.strip():
            lines.append(f"EP  - {ep.strip()}")
    if record.issued and record.issued.year:
        lines.append(f"PY  - {record.issued.year}")
    if record.doi:
        lines.append(f"DO  - {record.doi}")
    if record.url:
        lines.append(f"UR  - {record.url}")
    if record.report_number:
        lines.append(f"AN  - {record.report_number}")
    if record.docket_number:
        lines.append(f"AN  - {record.docket_number}")

    lines.append("ER  - ")
    return "\n".join(lines)


# ── CSL-JSON ──────────────────────────────────────────────────────────────────

def render_csl_json(record: CitationRecord) -> dict:
    """CSL-JSON dict — suitable for use with citeproc-compatible processors."""
    obj: dict = {
        "type": record.source_type,
        "id": citation_key(record),
    }

    if record.authors:
        obj["author"] = [
            {k: v for k, v in {
                "family": p.family,
                "given": p.given,
                "literal": p.literal if p.is_organization else "",
                "suffix": p.suffix,
            }.items() if v}
            for p in record.authors
        ]
    if record.editors:
        obj["editor"] = [
            {k: v for k, v in {"family": p.family, "given": p.given, "literal": p.literal}.items() if v}
            for p in record.editors
        ]

    if record.title:
        obj["title"] = record.title
    if record.container_title:
        obj["container-title"] = record.container_title
    if record.collection_title:
        obj["collection-title"] = record.collection_title
    if record.publisher:
        obj["publisher"] = record.publisher
    if record.publisher_place:
        obj["publisher-place"] = record.publisher_place
    if record.edition:
        obj["edition"] = record.edition
    if record.volume:
        obj["volume"] = record.volume
    if record.issue:
        obj["issue"] = record.issue
    if record.page:
        obj["page"] = record.page
    if record.article_number:
        obj["article-number"] = record.article_number
    if record.doi:
        obj["DOI"] = record.doi
    if record.url:
        obj["URL"] = record.url
    if record.issued and record.issued.year:
        obj["issued"] = {"date-parts": record.issued.to_csl_date_parts()}
    if record.accessed and record.accessed.year:
        obj["accessed"] = {"date-parts": record.accessed.to_csl_date_parts()}
    if record.language:
        obj["language"] = record.language

    # Legal
    if record.case_name:
        obj["title"] = obj.get("title", record.case_name)
        obj["authority"] = record.court
        obj["number"] = record.docket_number
    if record.legislation_title:
        obj["title"] = obj.get("title", record.legislation_title)
        obj["section"] = record.section
        obj["jurisdiction"] = record.jurisdiction

    return {k: v for k, v in obj.items() if v or v == 0}


# ── Combined render_all ───────────────────────────────────────────────────────

def render_all(record: CitationRecord) -> dict[str, str]:
    """Render all formats from a single CitationRecord."""
    csl = render_csl_json(record)
    return {
        "debate": render_debate(record),
        "mla": render_mla(record),
        "apa": render_apa(record),
        "chicago": render_chicago(record),
        "bibtex": render_bibtex(record),
        "ris": render_ris(record),
        "csl_json": json.dumps(csl, ensure_ascii=False),
    }


def attach_rendered(record: CitationRecord) -> CitationRecord:
    """Compute all rendered strings and cache them on the record."""
    record.rendered_debate = render_debate(record)
    record.rendered_mla = render_mla(record)
    record.rendered_apa = render_apa(record)
    record.rendered_chicago = render_chicago(record)
    record.rendered_bibtex = render_bibtex(record)
    record.rendered_ris = render_ris(record)
    return record


# ── Bibliography export ───────────────────────────────────────────────────────

def export_bibliography(
    records: list[CitationRecord],
    fmt: str = "mla",
) -> str:
    """Export a deduplicated bibliography for multiple cards.

    Cards sharing the same DOI collapse to one entry.
    Citation keys are deterministic.
    """
    seen_dois: set[str] = set()
    seen_keys: set[str] = set()
    output: list[str] = []

    for record in records:
        # Deduplicate by DOI
        if record.doi:
            norm = record.doi.lower()
            if norm in seen_dois:
                continue
            seen_dois.add(norm)

        key = citation_key(record)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        if fmt == "bibtex":
            output.append(render_bibtex(record))
        elif fmt == "ris":
            output.append(render_ris(record))
        elif fmt == "apa":
            output.append(render_apa(record))
        elif fmt == "chicago":
            output.append(render_chicago(record))
        elif fmt == "csl_json":
            output.append(json.dumps(render_csl_json(record), ensure_ascii=False))
        else:  # default: MLA
            output.append(render_mla(record))

    sep = "\n\n" if fmt in ("bibtex", "ris") else "\n"
    return sep.join(output)
