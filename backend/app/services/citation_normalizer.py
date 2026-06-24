"""Citation normalizer — Pass 12.

Converts raw metadata dicts (from Crossref, JSON-LD, OG, provider, etc.) into a
single CitationRecord with field-level provenance and deterministic precedence.

Key rules:
  * Stronger-confidence data never overwritten by weaker-confidence data.
  * Empty fields may always be enriched from any source.
  * Conflicting values at similar confidence are recorded as CitationConflict entries.
  * Organization authors are never split into fake person names.
  * DOI and URL are normalized.
  * Dates retain year/month/day precision when known.
  * Merging is deterministic — no randomness, no LLM calls.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from app.models.citation import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_INCOMPLETE,
    COMPLETENESS_UNVERIFIED,
    COMPLETENESS_USABLE,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_UNKNOWN,
    CONFIDENCE_VERIFIED,
    SRC_CITATION_META,
    SRC_CROSSREF,
    SRC_DOMAIN,
    SRC_JSON_LD,
    SRC_NONE,
    SRC_OG,
    SRC_OPENALEX,
    SRC_PROVIDER,
    SRC_SEMANTIC_SCHOLAR,
    SRC_URL,
    SRC_USER_EDIT,
    SRC_VISIBLE_TEXT,
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
    CitationConflict,
    CitationDate,
    CitationPerson,
    CitationRecord,
    FieldProvenance,
    confidence_rank,
    default_confidence,
    is_valid_source_type,
)

# ── DOI normalization ─────────────────────────────────────────────────────────
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:", "DOI:")
_DOI_RE = re.compile(r'\b10\.\d{4,}/\S+')

def normalize_doi(doi: str) -> str:
    """Strip URL prefixes from a DOI and lowercase the prefix."""
    if not doi:
        return ""
    doi = doi.strip()
    for prefix in _DOI_PREFIXES:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    return doi.strip("/").strip()


# ── URL normalization ─────────────────────────────────────────────────────────
_TRACKING_PARAMS = frozenset([
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "referral", "source",
    "mc_cid", "mc_eid", "_ga",
])

def normalize_url(url: str) -> str:
    """Strip common tracking parameters and normalize scheme."""
    if not url:
        return ""
    try:
        parts = urlparse(url.strip())
        qs = parse_qs(parts.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        new_query = urlencode(clean_qs, doseq=True)
        return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, ""))
    except Exception:
        return url


# ── Person parsing ────────────────────────────────────────────────────────────
# Org heuristic: known phrases that indicate a corporate/org author.
_ORG_INDICATORS = re.compile(
    r'\b(institute|institution|university|college|department|agency|bureau|congress|'
    r'committee|foundation|center|centre|council|commission|authority|corporation|'
    r'organization|organisation|service|project|program|programme|'
    r'government|ministry|office|administration|association|society|'
    r'research\s+group|working\s+group|task\s+force|panel|board)\b',
    re.IGNORECASE,
)


def _looks_like_organization(name: str) -> bool:
    """Return True if name looks like an organization, not a person."""
    if not name:
        return False
    tokens = name.split()
    # Multi-word name ending with an acronym → org
    if len(tokens) >= 2 and re.match(r'^[A-Z]{2,}$', tokens[-1]):
        return True
    if _ORG_INDICATORS.search(name):
        return True
    # 3+ capitalized words without comma → likely org
    cap_words = [t for t in tokens if t and t[0].isupper()]
    if len(cap_words) >= 3 and "," not in name:
        return True
    return False


def parse_person(raw: str) -> CitationPerson:
    """Convert a raw author string into a CitationPerson."""
    raw = raw.strip()
    if not raw:
        return CitationPerson()
    if _looks_like_organization(raw):
        return CitationPerson(literal=raw, is_organization=True)
    # "Last, First [Suffix]"
    if "," in raw:
        parts = raw.split(",", 1)
        family = parts[0].strip()
        rest = parts[1].strip()
        # Check for Jr./Sr./III suffix at end
        suffix_match = re.search(r'\s+(Jr\.?|Sr\.?|I{2,3}|IV|PhD|MD|Esq\.?)$', rest, re.I)
        suffix = ""
        if suffix_match:
            suffix = suffix_match.group(1).strip()
            rest = rest[:suffix_match.start()].strip()
        return CitationPerson(given=rest, family=family, suffix=suffix)
    # "First Last" format
    parts = raw.split()
    if len(parts) == 1:
        # Only one token — could be surname or org fragment
        return CitationPerson(family=parts[0], literal=raw)
    # Check for suffix at end
    suffix = ""
    if re.match(r'^(Jr\.?|Sr\.?|I{2,3}|IV)$', parts[-1], re.I):
        suffix = parts[-1]
        parts = parts[:-1]
    family = parts[-1]
    given = " ".join(parts[:-1])
    return CitationPerson(given=given, family=family, suffix=suffix)


def parse_authors(raw: str | list) -> list[CitationPerson]:
    """Parse an author string or list into CitationPerson records.

    Handles semicolon, ' and ', '&' separators.
    Organization names are preserved as-is.
    Accepts list[str] or list[CitationPerson].
    """
    if not raw:
        return []
    if isinstance(raw, list):
        result = []
        for a in raw:
            if isinstance(a, CitationPerson):
                result.append(a)
            elif isinstance(a, str) and a.strip():
                result.append(parse_person(a))
            elif isinstance(a, dict):
                result.append(CitationPerson(**a))
        return result
    # String: split on ; or ' and ' or ' & '
    parts = re.split(r';|\band\b|&', raw, flags=re.IGNORECASE)
    return [parse_person(p) for p in parts if p.strip()]


def parse_date(raw: str | None) -> Optional[CitationDate]:
    if not raw:
        return None
    d = CitationDate.from_string(raw)
    return d if d.year else None


# ── Infer source type ─────────────────────────────────────────────────────────
_URL_PDF_RE = re.compile(r'\.pdf(\?|#|$)', re.IGNORECASE)
_URL_THESIS_RE = re.compile(r'(?:thesis|dissertation|theses)', re.IGNORECASE)
_URL_STAT_RE = re.compile(r'(?:uscode|cfr\.gov|govinfo\.gov|congress\.gov/bill|leginfo|statute)', re.IGNORECASE)
_GOV_DOMAIN_RE = re.compile(r'\.gov(?:\.uk|\.au|\.ca|\.nz)?$', re.IGNORECASE)


def infer_source_type(
    url: str = "",
    domain: str = "",
    container_title: str = "",
    source_type_hint: str = "",
    crossref_type: str = "",
) -> tuple[str, str]:
    """Return (source_type, confidence) using conservative inference.

    Never classifies every PDF as report or every webpage as news.
    Falls back to 'document' when uncertain.
    """
    if source_type_hint and is_valid_source_type(source_type_hint):
        return source_type_hint, CONFIDENCE_HIGH

    # Crossref type mapping
    _CROSSREF_MAP: dict[str, str] = {
        "journal-article": STYPE_JOURNAL_ARTICLE,
        "proceedings-article": STYPE_CONFERENCE,
        "book": STYPE_BOOK,
        "book-chapter": STYPE_CHAPTER,
        "report": STYPE_REPORT,
        "report-series": STYPE_REPORT,
        "dataset": STYPE_DATASET,
        "dissertation": STYPE_THESIS,
        "working-paper": STYPE_WORKING_PAPER,
        "posted-content": STYPE_WORKING_PAPER,
    }
    if crossref_type and crossref_type in _CROSSREF_MAP:
        return _CROSSREF_MAP[crossref_type], CONFIDENCE_VERIFIED

    # Container title hints
    ct = container_title.lower()
    if any(w in ct for w in ("journal", "review", "quarterly", "proceedings", "transactions")):
        return STYPE_JOURNAL_ARTICLE, CONFIDENCE_MEDIUM
    if any(w in ct for w in ("newspaper", "times", "post", "gazette", "herald")):
        return STYPE_NEWS, CONFIDENCE_LOW
    if any(w in ct for w in ("magazine", "atlantic", "wired", "vox", "the guardian")):
        return STYPE_MAGAZINE, CONFIDENCE_LOW

    # URL-based inference
    if url:
        if _URL_STAT_RE.search(url):
            return STYPE_STATUTE, CONFIDENCE_MEDIUM
        if _URL_THESIS_RE.search(url):
            return STYPE_THESIS, CONFIDENCE_MEDIUM
        if _GOV_DOMAIN_RE.search(domain):
            if _URL_PDF_RE.search(url):
                return STYPE_GOV_REPORT, CONFIDENCE_LOW
            return STYPE_GOV_REPORT, CONFIDENCE_LOW
        if _URL_PDF_RE.search(url):
            # PDF but not .gov — could be report, working paper, or thesis
            return STYPE_DOCUMENT, CONFIDENCE_LOW  # conservative
        if domain and any(d in domain for d in ("scholar.google", "arxiv.org", "ssrn.com")):
            return STYPE_WORKING_PAPER, CONFIDENCE_MEDIUM

    return STYPE_WEBPAGE if url else STYPE_DOCUMENT, CONFIDENCE_LOW


# ── Build / merge logic ───────────────────────────────────────────────────────

def _prov(source: str, confidence: str | None = None) -> FieldProvenance:
    return FieldProvenance(
        source=source,
        confidence=confidence or default_confidence(source),
    )


def _should_update(
    existing_prov: FieldProvenance,
    existing_value: Any,
    new_prov: FieldProvenance,
    new_value: Any,
) -> bool:
    """True if new data should overwrite existing field."""
    if not new_value:
        return False
    if not existing_value:
        return True
    return confidence_rank(new_prov.confidence) > confidence_rank(existing_prov.confidence)


def _check_conflict(
    field: str,
    existing_val: str,
    existing_prov: FieldProvenance,
    new_val: str,
    new_prov: FieldProvenance,
) -> Optional[CitationConflict]:
    """Return a conflict when two non-empty string values materially differ."""
    if not existing_val or not new_val:
        return None
    if existing_val.lower().strip() == new_val.lower().strip():
        return None
    # Title mismatch: compare normalized words
    if field in ("title", "container_title"):
        ex_words = set(re.findall(r'\b\w{4,}\b', existing_val.lower()))
        nw_words = set(re.findall(r'\b\w{4,}\b', new_val.lower()))
        if ex_words and nw_words:
            overlap = len(ex_words & nw_words) / max(len(ex_words), len(nw_words))
            if overlap < 0.5:
                return CitationConflict(
                    field=field,
                    selected_value=existing_val,
                    selected_source=existing_prov.source,
                    conflicting_value=new_val,
                    conflicting_source=new_prov.source,
                    message=f"{field}: '{existing_val[:60]}' vs '{new_val[:60]}'",
                )
        return None  # small wording differences are fine
    # Year/DOI: exact match required for no conflict
    if field in ("doi", "year"):
        return CitationConflict(
            field=field,
            selected_value=existing_val,
            selected_source=existing_prov.source,
            conflicting_value=new_val,
            conflicting_source=new_prov.source,
            message=f"{field} mismatch: '{existing_val}' vs '{new_val}'",
        )
    # Author: only conflict when surnames are totally different
    if field == "authors":
        ex_surnames = set(re.findall(r'\b[A-Z][a-z]+', existing_val))
        nw_surnames = set(re.findall(r'\b[A-Z][a-z]+', new_val))
        if ex_surnames and nw_surnames and not (ex_surnames & nw_surnames):
            return CitationConflict(
                field=field,
                selected_value=existing_val,
                selected_source=existing_prov.source,
                conflicting_value=new_val,
                conflicting_source=new_prov.source,
                message=f"author mismatch: '{existing_val[:40]}' vs '{new_val[:40]}'",
            )
    return None


def build_citation_record(
    url: str = "",
    authors_raw: str | list[str] = "",
    title: str = "",
    container_title: str = "",
    publisher: str = "",
    published_date: str = "",
    doi: str = "",
    volume: str = "",
    issue: str = "",
    page: str = "",
    institution: str = "",
    report_number: str = "",
    source_type_hint: str = "",
    language: str = "",
    canonical_url: str = "",
    # Provenance for each input field
    authors_source: str = SRC_PROVIDER,
    title_source: str = SRC_PROVIDER,
    container_title_source: str = SRC_PROVIDER,
    publisher_source: str = SRC_PROVIDER,
    date_source: str = SRC_PROVIDER,
    doi_source: str = SRC_PROVIDER,
    url_source: str = SRC_URL,
    institution_source: str = SRC_NONE,
) -> CitationRecord:
    """Build a CitationRecord from raw metadata inputs with provenance."""
    from urllib.parse import urlparse as _up

    clean_doi = normalize_doi(doi)
    clean_url = normalize_url(url)
    clean_canonical = normalize_url(canonical_url)

    try:
        domain = _up(clean_url).netloc.lower().lstrip("www.")
    except Exception:
        domain = ""

    stype, stype_conf = infer_source_type(
        url=clean_url, domain=domain,
        container_title=container_title,
        source_type_hint=source_type_hint,
    )

    authors = parse_authors(authors_raw)
    issued = parse_date(published_date)

    record = CitationRecord(
        source_type=stype,
        source_type_confidence=stype_conf,
        authors=authors,
        authors_prov=_prov(authors_source) if (authors_raw or authors) else FieldProvenance(),
        title=title or "",
        title_prov=_prov(title_source) if title else FieldProvenance(),
        container_title=container_title or "",
        container_title_prov=_prov(container_title_source) if container_title else FieldProvenance(),
        publisher=publisher or "",
        publisher_prov=_prov(publisher_source) if publisher else FieldProvenance(),
        volume=volume or "",
        issue=issue or "",
        page=page or "",
        institution=institution or "",
        institution_prov=_prov(institution_source) if institution else FieldProvenance(),
        report_number=report_number or "",
        issued=issued,
        issued_prov=_prov(date_source) if issued else FieldProvenance(),
        doi=clean_doi,
        doi_prov=_prov(doi_source) if clean_doi else FieldProvenance(),
        url=clean_url,
        url_prov=_prov(url_source) if clean_url else FieldProvenance(),
        canonical_url=clean_canonical,
        language=language or "",
    )
    record = validate_completeness(record)
    return record


def merge_crossref(record: CitationRecord, crossref: dict) -> CitationRecord:
    """Apply Crossref API response into record with precedence."""
    if not crossref:
        return record

    cr_prov = _prov(SRC_CROSSREF, CONFIDENCE_VERIFIED)

    # DOI
    cr_doi = normalize_doi(crossref.get("DOI", ""))
    if cr_doi:
        if not record.doi:
            record.doi = cr_doi
            record.doi_prov = cr_prov
        elif record.doi.lower() != cr_doi.lower():
            c = _check_conflict("doi", record.doi, record.doi_prov, cr_doi, cr_prov)
            if c:
                record.conflicts.append(c)

    # Authors
    cr_authors_raw = crossref.get("author", [])
    if cr_authors_raw and not record.authors:
        record.authors = [
            CitationPerson(
                given=a.get("given", ""),
                family=a.get("family", ""),
                literal=a.get("literal", ""),
                is_organization=bool(a.get("literal")),
            )
            for a in cr_authors_raw
        ]
        record.authors_prov = cr_prov
    elif cr_authors_raw and record.authors:
        # Check for mismatch at similar confidence
        if confidence_rank(record.authors_prov.confidence) < confidence_rank(CONFIDENCE_HIGH):
            new_display = " ".join(
                a.get("family", a.get("literal", "")) for a in cr_authors_raw[:2]
            )
            old_display = " ".join(a.surname() for a in record.authors[:2])
            c = _check_conflict("authors", old_display, record.authors_prov, new_display, cr_prov)
            if c:
                record.conflicts.append(c)
            record.authors = [
                CitationPerson(
                    given=a.get("given", ""),
                    family=a.get("family", ""),
                    literal=a.get("literal", ""),
                    is_organization=bool(a.get("literal")),
                )
                for a in cr_authors_raw
            ]
            record.authors_prov = cr_prov

    # Title
    cr_titles = crossref.get("title", [])
    cr_title = (cr_titles[0] if isinstance(cr_titles, list) else cr_titles) or ""
    if cr_title and _should_update(record.title_prov, record.title, cr_prov, cr_title):
        c = _check_conflict("title", record.title, record.title_prov, cr_title, cr_prov)
        if c:
            record.conflicts.append(c)
        record.title = cr_title
        record.title_prov = cr_prov

    # Container title
    cr_cts = crossref.get("container-title", [])
    cr_ct = (cr_cts[0] if isinstance(cr_cts, list) else cr_cts) or ""
    if cr_ct and _should_update(record.container_title_prov, record.container_title, cr_prov, cr_ct):
        record.container_title = cr_ct
        record.container_title_prov = cr_prov

    # Publisher
    cr_pub = crossref.get("publisher", "")
    if cr_pub and _should_update(record.publisher_prov, record.publisher, cr_prov, cr_pub):
        record.publisher = cr_pub
        record.publisher_prov = cr_prov

    # Issued date
    cr_date_parts = crossref.get("issued", {}).get("date-parts", [[]])
    if cr_date_parts and cr_date_parts[0]:
        dp = cr_date_parts[0]
        cr_issued = CitationDate(
            year=dp[0] if dp else None,
            month=dp[1] if len(dp) > 1 else None,
            day=dp[2] if len(dp) > 2 else None,
        )
        if cr_issued.year:
            if not record.issued or not record.issued.year:
                record.issued = cr_issued
                record.issued_prov = cr_prov
            elif record.issued.year != cr_issued.year:
                c = _check_conflict(
                    "year", str(record.issued.year), record.issued_prov,
                    str(cr_issued.year), cr_prov,
                )
                if c:
                    record.conflicts.append(c)
                # Crossref wins (verified)
                record.issued = cr_issued
                record.issued_prov = cr_prov

    # Volume / issue / page
    if crossref.get("volume") and not record.volume:
        record.volume = str(crossref["volume"])
    if crossref.get("issue") and not record.issue:
        record.issue = str(crossref["issue"])
    if crossref.get("page") and not record.page:
        record.page = str(crossref["page"])

    # Source type from Crossref
    cr_type = crossref.get("type", "")
    if cr_type:
        from app.models.citation import STYPE_DOCUMENT
        stype, stype_conf = infer_source_type(crossref_type=cr_type)
        if stype != STYPE_DOCUMENT:
            record.source_type = stype
            record.source_type_confidence = stype_conf

    record = validate_completeness(record)
    return record


def merge_structured_metadata(
    record: CitationRecord,
    data: dict,
    source: str,
) -> CitationRecord:
    """Merge a flat metadata dict (from JSON-LD, OG, citation meta, etc.) into record.

    data keys: author, title, publication, date, doi, url, language
    """
    prov = _prov(source)

    raw_author = data.get("author") or data.get("authors") or ""
    if raw_author and _should_update(record.authors_prov, record.authors, prov, raw_author):
        parsed = parse_authors(raw_author)
        if parsed:
            record.authors = parsed
            record.authors_prov = prov

    raw_title = data.get("title") or ""
    if raw_title:
        if record.title and record.title != raw_title:
            c = _check_conflict("title", record.title, record.title_prov, raw_title, prov)
            if c:
                record.conflicts.append(c)
        if _should_update(record.title_prov, record.title, prov, raw_title):
            record.title = raw_title
            record.title_prov = prov

    raw_ct = data.get("publication") or data.get("container_title") or data.get("site_name") or ""
    if raw_ct and _should_update(record.container_title_prov, record.container_title, prov, raw_ct):
        record.container_title = raw_ct
        record.container_title_prov = prov

    raw_pub = data.get("publisher") or ""
    if raw_pub and _should_update(record.publisher_prov, record.publisher, prov, raw_pub):
        record.publisher = raw_pub
        record.publisher_prov = prov

    raw_date = data.get("date") or data.get("published_date") or ""
    if raw_date:
        new_issued = parse_date(raw_date)
        if new_issued and new_issued.year:
            if _should_update(record.issued_prov, record.issued, prov, raw_date):
                record.issued = new_issued
                record.issued_prov = prov

    raw_doi = normalize_doi(data.get("doi") or "")
    if raw_doi and _should_update(record.doi_prov, record.doi, prov, raw_doi):
        record.doi = raw_doi
        record.doi_prov = prov

    if data.get("language") and not record.language:
        record.language = data["language"]

    record = validate_completeness(record)
    return record


def apply_user_edit(record: CitationRecord, field: str, value: str) -> CitationRecord:
    """Apply a user correction to a named field — always wins over detected values."""
    user_prov = FieldProvenance(
        source=SRC_USER_EDIT,
        confidence=CONFIDENCE_VERIFIED,
        manually_edited=True,
    )
    simple_str_fields = {
        "title", "container_title", "publisher", "publisher_place",
        "volume", "issue", "page", "doi", "url", "institution",
        "report_number", "court", "case_name", "docket_number",
        "legislation_title", "section", "language", "source_type",
    }
    if field in simple_str_fields:
        setattr(record, field, value)
        if hasattr(record, f"{field}_prov"):
            setattr(record, f"{field}_prov", user_prov)
        return validate_completeness(record)
    if field == "authors":
        record.authors = parse_authors(value)
        record.authors_prov = user_prov
    elif field == "issued_year":
        record.issued = record.issued or CitationDate()
        record.issued = CitationDate(
            year=int(value) if value.isdigit() else record.issued.year,
            month=record.issued.month,
            day=record.issued.day,
        )
        record.issued_prov = user_prov
    return validate_completeness(record)


# ── Completeness validation ───────────────────────────────────────────────────

def validate_completeness(record: CitationRecord) -> CitationRecord:
    """Set record.completeness based on source-type-specific rules."""
    st = record.source_type
    has_title = bool(record.title)
    has_author = bool(record.authors)
    has_year = bool(record.issued and record.issued.year)
    has_container = bool(record.container_title)
    has_pub = bool(record.publisher or record.container_title or record.institution)
    has_url = bool(record.url or record.doi)

    if st == STYPE_JOURNAL_ARTICLE:
        if has_title and has_author and has_container and has_year:
            record.completeness = COMPLETENESS_COMPLETE
        elif has_title and (has_author or has_container) and has_url:
            record.completeness = COMPLETENESS_USABLE
        elif has_title or has_url:
            record.completeness = COMPLETENESS_INCOMPLETE
        else:
            record.completeness = COMPLETENESS_UNVERIFIED

    elif st in (STYPE_REPORT, STYPE_GOV_REPORT):
        # report_number optional per spec
        if has_title and has_year and has_pub:
            record.completeness = COMPLETENESS_COMPLETE
        elif has_title and has_url:
            record.completeness = COMPLETENESS_USABLE
        else:
            record.completeness = COMPLETENESS_INCOMPLETE

    elif st == STYPE_WEBPAGE:
        if has_title and has_pub and has_url:
            record.completeness = COMPLETENESS_COMPLETE if has_year else COMPLETENESS_USABLE
        elif has_title and has_url:
            record.completeness = COMPLETENESS_USABLE
        else:
            record.completeness = COMPLETENESS_INCOMPLETE

    elif st == STYPE_LEGAL_CASE:
        if record.case_name and (record.court or record.jurisdiction) and has_year:
            record.completeness = COMPLETENESS_COMPLETE
        elif record.case_name and has_url:
            record.completeness = COMPLETENESS_USABLE
        else:
            record.completeness = COMPLETENESS_INCOMPLETE

    elif st == STYPE_STATUTE:
        if record.legislation_title and has_year and has_url:
            record.completeness = COMPLETENESS_COMPLETE
        elif has_title and has_url:
            record.completeness = COMPLETENESS_USABLE
        else:
            record.completeness = COMPLETENESS_INCOMPLETE

    else:
        # generic document, book, chapter, etc.
        score = sum([has_title, has_author or has_pub, has_year, has_url])
        if score >= 3:
            record.completeness = COMPLETENESS_COMPLETE
        elif score >= 2:
            record.completeness = COMPLETENESS_USABLE
        elif score >= 1:
            record.completeness = COMPLETENESS_INCOMPLETE
        else:
            record.completeness = COMPLETENESS_UNVERIFIED

    return record


# ── Build CitationRecord from an existing CitationMetadata ────────────────────

def from_legacy_citation_metadata(legacy: Any) -> CitationRecord:
    """Create a partial CitationRecord from the existing CitationMetadata object.

    Existing mla_citation / short_cite are preserved as rendered compatibility
    fields — they are NOT stored in the CitationRecord.
    """
    if legacy is None:
        return CitationRecord()

    # Determine per-field sources from legacy provenance fields
    _author_src = getattr(legacy, "author_source", SRC_PROVIDER) or SRC_PROVIDER
    _date_src = getattr(legacy, "date_source", SRC_PROVIDER) or SRC_PROVIDER
    _title_src = getattr(legacy, "title_source", SRC_PROVIDER) or SRC_PROVIDER
    _pub_src = getattr(legacy, "publication_source", SRC_PROVIDER) or SRC_PROVIDER

    record = build_citation_record(
        url=legacy.url or "",
        authors_raw=legacy.authors or legacy.author_display or "",
        title=legacy.title or "",
        container_title=legacy.container_title or "",
        publisher=legacy.publication_name or "",
        published_date=legacy.year or "",
        doi=legacy.doi or "",
        authors_source=_author_src,
        title_source=_title_src,
        container_title_source=_pub_src,
        publisher_source=_pub_src,
        date_source=_date_src,
    )
    return record
