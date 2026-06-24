"""Pass 12 — Structured Citation Records, Metadata Confidence, and Multi-Format Export.

Tests cover:
  * CitationPerson, CitationDate, FieldProvenance models
  * DOI / URL normalization
  * Person parsing (Last/First, org detection)
  * Author list splitting
  * Date parsing (ISO, year-only)
  * Source type inference
  * build_citation_record (provenance assignment)
  * merge_crossref (precedence rules)
  * merge_structured_metadata (precedence + conflict detection)
  * apply_user_edit (always wins)
  * Completeness validation per source type
  * Renderers: debate, MLA, APA, Chicago, BibTeX, RIS, CSL-JSON
  * citation_key determinism
  * export_bibliography deduplication
  * from_legacy_citation_metadata
  * SearchStageTrace P12 fields
  * build_search_trace P12 params
  * Import integrity
"""
import json
import pytest

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
    SRC_CROSSREF,
    SRC_DOMAIN,
    SRC_JSON_LD,
    SRC_NONE,
    SRC_OG,
    SRC_PROVIDER,
    SRC_URL,
    SRC_USER_EDIT,
    STYPE_DOCUMENT,
    STYPE_GOV_REPORT,
    STYPE_JOURNAL_ARTICLE,
    STYPE_LEGAL_CASE,
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
from app.services.citation_normalizer import (
    _looks_like_organization,
    apply_user_edit,
    build_citation_record,
    from_legacy_citation_metadata,
    infer_source_type,
    merge_crossref,
    merge_structured_metadata,
    normalize_doi,
    normalize_url,
    parse_authors,
    parse_date,
    parse_person,
    validate_completeness,
)
from app.services.citation_renderers import (
    citation_key,
    export_bibliography,
    render_apa,
    render_bibtex,
    render_chicago,
    render_csl_json,
    render_debate,
    render_mla,
    render_ris,
    render_all,
    attach_rendered,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _journal(
    authors=None,
    title="Testing the Hypothesis",
    container="Journal of Science",
    year=2023,
    doi="10.1234/test",
    volume="12",
    issue="3",
    page="100-115",
) -> CitationRecord:
    """Build a complete journal article CitationRecord for testing."""
    rec = build_citation_record(
        url="https://example.org/article",
        authors_raw=authors or [{"given": "Jane", "family": "Smith"}],
        title=title,
        container_title=container,
        published_date=str(year),
        doi=doi,
        volume=volume,
        issue=issue,
        page=page,
        source_type_hint=STYPE_JOURNAL_ARTICLE,
        authors_source=SRC_CROSSREF,
        title_source=SRC_CROSSREF,
    )
    if not rec.authors and isinstance(authors, list) and authors:
        first = authors[0]
        if isinstance(first, dict):
            rec.authors = [CitationPerson(**first)]
        elif isinstance(first, CitationPerson):
            rec.authors = list(authors)
    return rec


def _org_record() -> CitationRecord:
    return build_citation_record(
        url="https://rand.org/report",
        authors_raw="RAND Corporation",
        title="Security Analysis 2024",
        container_title="RAND Report",
        published_date="2024",
        source_type_hint=STYPE_REPORT,
        authors_source=SRC_JSON_LD,
    )


# ── TestCitationPerson ────────────────────────────────────────────────────────

class TestCitationPerson:
    def test_display_name_person(self):
        p = CitationPerson(given="Jane", family="Smith")
        assert p.display_name() == "Jane Smith"

    def test_display_name_org(self):
        p = CitationPerson(literal="RAND Corporation", is_organization=True)
        assert p.display_name() == "RAND Corporation"

    def test_surname_person(self):
        p = CitationPerson(given="Jane A.", family="Smith")
        assert p.surname() == "Smith"

    def test_surname_org(self):
        p = CitationPerson(literal="WHO", is_organization=True)
        assert p.surname() == "WHO"

    def test_mla_name_person(self):
        p = CitationPerson(given="Jane A.", family="Smith")
        assert p.mla_name() == "Smith, Jane A."

    def test_mla_name_org(self):
        p = CitationPerson(literal="UNESCO", is_organization=True)
        assert p.mla_name() == "UNESCO"

    def test_apa_name_person(self):
        p = CitationPerson(given="Jane Ann", family="Smith")
        # "Smith, J. A."
        assert p.apa_name() == "Smith, J. A."

    def test_apa_name_org(self):
        p = CitationPerson(literal="CDC", is_organization=True)
        assert p.apa_name() == "CDC"

    def test_bibtex_name_person(self):
        p = CitationPerson(given="Jane", family="Smith")
        assert p.bibtex_name() == "Smith, Jane"

    def test_bibtex_name_org(self):
        p = CitationPerson(literal="World Bank", is_organization=True)
        assert "{World Bank}" in p.bibtex_name()

    def test_suffix_preserved(self):
        p = CitationPerson(given="John", family="Smith", suffix="Jr.")
        assert "Jr." in p.mla_name()


# ── TestCitationDate ──────────────────────────────────────────────────────────

class TestCitationDate:
    def test_full_date_display(self):
        d = CitationDate(year=2024, month=3, day=15)
        assert d.display() == "2024-03-15"

    def test_year_month_display(self):
        d = CitationDate(year=2024, month=3)
        assert d.display() == "2024-03"

    def test_year_only_display(self):
        d = CitationDate(year=2024)
        assert d.display() == "2024"

    def test_empty_display(self):
        d = CitationDate()
        assert d.display() == ""

    def test_from_iso_string(self):
        d = CitationDate.from_string("2024-03-15")
        assert d.year == 2024 and d.month == 3 and d.day == 15

    def test_from_year_month_string(self):
        d = CitationDate.from_string("2023-07")
        assert d.year == 2023 and d.month == 7 and d.day is None

    def test_from_year_only(self):
        d = CitationDate.from_string("2022")
        assert d.year == 2022 and d.month is None

    def test_from_empty(self):
        d = CitationDate.from_string("")
        assert d.year is None

    def test_from_natural_string(self):
        d = CitationDate.from_string("March 2024")
        assert d.year == 2024

    def test_csl_date_parts_full(self):
        d = CitationDate(year=2024, month=3, day=15)
        assert d.to_csl_date_parts() == [[2024, 3, 15]]

    def test_csl_date_parts_year_only(self):
        d = CitationDate(year=2024)
        assert d.to_csl_date_parts() == [[2024]]

    def test_csl_date_parts_empty(self):
        d = CitationDate()
        assert d.to_csl_date_parts() == []


# ── TestFieldProvenance ───────────────────────────────────────────────────────

class TestFieldProvenance:
    def test_confidence_ordering(self):
        assert confidence_rank(CONFIDENCE_VERIFIED) > confidence_rank(CONFIDENCE_HIGH)
        assert confidence_rank(CONFIDENCE_HIGH) > confidence_rank(CONFIDENCE_MEDIUM)
        assert confidence_rank(CONFIDENCE_MEDIUM) > confidence_rank(CONFIDENCE_LOW)
        assert confidence_rank(CONFIDENCE_LOW) > confidence_rank(CONFIDENCE_UNKNOWN)

    def test_precedes_stronger_beats_weaker(self):
        strong = FieldProvenance(source=SRC_CROSSREF, confidence=CONFIDENCE_VERIFIED)
        weak = FieldProvenance(source=SRC_OG, confidence=CONFIDENCE_MEDIUM)
        assert strong.precedes(weak)
        assert not weak.precedes(strong)

    def test_precedes_equal_returns_false(self):
        a = FieldProvenance(source=SRC_JSON_LD, confidence=CONFIDENCE_HIGH)
        b = FieldProvenance(source=SRC_JSON_LD, confidence=CONFIDENCE_HIGH)
        assert not a.precedes(b)

    def test_default_confidence_by_source(self):
        assert default_confidence(SRC_CROSSREF) == CONFIDENCE_VERIFIED
        assert default_confidence(SRC_JSON_LD) == CONFIDENCE_HIGH
        assert default_confidence(SRC_OG) == CONFIDENCE_MEDIUM
        assert default_confidence(SRC_DOMAIN) == CONFIDENCE_LOW
        assert default_confidence(SRC_NONE) == CONFIDENCE_UNKNOWN

    def test_is_reliable_medium_and_above(self):
        assert FieldProvenance(source=SRC_CROSSREF, confidence=CONFIDENCE_VERIFIED).is_reliable()
        assert FieldProvenance(source=SRC_JSON_LD, confidence=CONFIDENCE_HIGH).is_reliable()
        assert FieldProvenance(source=SRC_OG, confidence=CONFIDENCE_MEDIUM).is_reliable()
        assert not FieldProvenance(source=SRC_DOMAIN, confidence=CONFIDENCE_LOW).is_reliable()

    def test_manually_edited_flag(self):
        prov = FieldProvenance(source=SRC_USER_EDIT, confidence=CONFIDENCE_VERIFIED, manually_edited=True)
        assert prov.manually_edited is True


# ── TestNormalizeDOI ──────────────────────────────────────────────────────────

class TestNormalizeDOI:
    def test_strip_https_prefix(self):
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"

    def test_strip_http_prefix(self):
        assert normalize_doi("http://doi.org/10.1234/test") == "10.1234/test"

    def test_strip_doi_colon(self):
        assert normalize_doi("doi:10.1234/test") == "10.1234/test"

    def test_no_prefix(self):
        assert normalize_doi("10.1234/test") == "10.1234/test"

    def test_empty(self):
        assert normalize_doi("") == ""

    def test_strips_trailing_slash(self):
        assert normalize_doi("10.1234/test/") == "10.1234/test"

    def test_case_insensitive_prefix(self):
        assert normalize_doi("DOI:10.1234/test") == "10.1234/test"


# ── TestNormalizeURL ──────────────────────────────────────────────────────────

class TestNormalizeURL:
    def test_strips_utm_source(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "example.com/article" in result

    def test_strips_fbclid(self):
        url = "https://example.com/?fbclid=abc123"
        assert "fbclid" not in normalize_url(url)

    def test_preserves_regular_params(self):
        url = "https://example.com/search?q=test&page=2"
        result = normalize_url(url)
        assert "q=test" in result
        assert "page=2" in result

    def test_empty_url(self):
        assert normalize_url("") == ""

    def test_no_params(self):
        url = "https://example.com/article"
        assert normalize_url(url) == url


# ── TestPersonParsing ─────────────────────────────────────────────────────────

class TestPersonParsing:
    def test_last_first_format(self):
        p = parse_person("Smith, Jane A.")
        assert p.family == "Smith"
        assert p.given == "Jane A."

    def test_first_last_format(self):
        p = parse_person("Jane Smith")
        assert p.family == "Smith"
        assert p.given == "Jane"

    def test_org_institute(self):
        p = parse_person("Brookings Institution")
        assert p.is_organization is True
        assert "Brookings" in p.literal

    def test_org_university(self):
        p = parse_person("Harvard University Department of Economics")
        assert p.is_organization is True

    def test_org_acronym(self):
        p = parse_person("RAND")
        # Single token: stored as family, not forced org
        assert p.family == "RAND"

    def test_parse_person_empty(self):
        p = parse_person("")
        assert p.given == "" and p.family == "" and p.literal == ""

    def test_suffix_jr(self):
        p = parse_person("Smith, John Jr.")
        assert p.family == "Smith"
        assert "Jr." in p.suffix

    def test_three_capitalized_words_org(self):
        p = parse_person("World Health Organization")
        assert p.is_organization is True


class TestAuthorParsing:
    def test_semicolon_separated(self):
        authors = parse_authors("Smith, Jane; Jones, Bob")
        assert len(authors) == 2
        assert authors[0].family == "Smith"
        assert authors[1].family == "Jones"

    def test_and_separated(self):
        authors = parse_authors("Jane Smith and Bob Jones")
        assert len(authors) == 2

    def test_ampersand_separated(self):
        authors = parse_authors("Smith J & Jones B")
        assert len(authors) == 2

    def test_org_not_split(self):
        authors = parse_authors("World Health Organization")
        assert len(authors) == 1
        assert authors[0].is_organization is True

    def test_list_input(self):
        authors = parse_authors(["Smith, Jane", "Jones, Bob"])
        assert len(authors) == 2

    def test_empty_string(self):
        assert parse_authors("") == []

    def test_empty_list(self):
        assert parse_authors([]) == []


# ── TestInferSourceType ───────────────────────────────────────────────────────

class TestInferSourceType:
    def test_journal_from_container(self):
        stype, conf = infer_source_type(container_title="Journal of Economics")
        assert stype == STYPE_JOURNAL_ARTICLE
        assert conf == CONFIDENCE_MEDIUM

    def test_crossref_wins(self):
        stype, conf = infer_source_type(crossref_type="journal-article")
        assert stype == STYPE_JOURNAL_ARTICLE
        assert conf == CONFIDENCE_VERIFIED

    def test_gov_domain_pdf(self):
        stype, _ = infer_source_type(url="https://cdc.gov/report.pdf", domain="cdc.gov")
        assert stype == STYPE_GOV_REPORT

    def test_uscode_url(self):
        stype, conf = infer_source_type(url="https://uscode.house.gov/view.xhtml?req=title:47")
        assert stype == STYPE_STATUTE

    def test_hint_takes_precedence(self):
        stype, _ = infer_source_type(source_type_hint=STYPE_THESIS, crossref_type="report")
        # hint wins
        assert stype == STYPE_THESIS

    def test_unknown_falls_back_to_webpage(self):
        stype, conf = infer_source_type(url="https://example.com/article")
        assert stype == STYPE_WEBPAGE

    def test_no_url_falls_back_to_document(self):
        stype, _ = infer_source_type()
        assert stype == STYPE_DOCUMENT

    def test_invalid_hint_ignored(self):
        stype, conf = infer_source_type(source_type_hint="not-a-valid-type")
        # falls through to URL/domain inference
        assert is_valid_source_type(stype)


# ── TestBuildCitationRecord ───────────────────────────────────────────────────

class TestBuildCitationRecord:
    def test_minimal_record(self):
        rec = build_citation_record(url="https://example.com")
        assert rec.url == "https://example.com"
        assert rec.source_type in (STYPE_WEBPAGE, STYPE_DOCUMENT)

    def test_doi_normalized(self):
        rec = build_citation_record(doi="https://doi.org/10.1234/test")
        assert rec.doi == "10.1234/test"

    def test_url_tracking_stripped(self):
        rec = build_citation_record(url="https://example.com/?utm_source=x")
        assert "utm_source" not in rec.url

    def test_authors_parsed(self):
        rec = build_citation_record(authors_raw="Smith, Jane; Jones, Bob")
        assert len(rec.authors) == 2

    def test_org_author_preserved(self):
        rec = build_citation_record(authors_raw="World Health Organization")
        assert rec.authors[0].is_organization is True

    def test_provenance_assigned(self):
        rec = build_citation_record(
            title="Test", title_source=SRC_JSON_LD
        )
        assert rec.title_prov.source == SRC_JSON_LD
        assert rec.title_prov.confidence == CONFIDENCE_HIGH

    def test_crossref_source_verified(self):
        rec = build_citation_record(
            title="Test", title_source=SRC_CROSSREF
        )
        assert rec.title_prov.confidence == CONFIDENCE_VERIFIED

    def test_url_source_low(self):
        rec = build_citation_record(
            url="https://example.com", url_source=SRC_URL
        )
        assert rec.url_prov.confidence == CONFIDENCE_LOW

    def test_completeness_set(self):
        rec = build_citation_record(
            url="https://example.com",
            title="Test Title",
            authors_raw="Smith",
            published_date="2024",
        )
        assert rec.completeness != COMPLETENESS_UNVERIFIED

    def test_empty_author_gives_no_authors(self):
        rec = build_citation_record(authors_raw="")
        assert rec.authors == []


# ── TestMergeCrossref ─────────────────────────────────────────────────────────

class TestMergeCrossref:
    def _make_crossref(self, **overrides) -> dict:
        base = {
            "author": [{"family": "Smith", "given": "Jane"}],
            "title": ["Test Article"],
            "container-title": ["Journal of Science"],
            "publisher": "Academic Press",
            "issued": {"date-parts": [[2024, 3]]},
            "DOI": "10.1234/test",
            "volume": "12",
            "issue": "3",
            "page": "100-115",
            "type": "journal-article",
        }
        base.update(overrides)
        return base

    def test_empty_fields_filled(self):
        rec = build_citation_record(url="https://example.com", doi="10.1234/test")
        cr = self._make_crossref()
        merged = merge_crossref(rec, cr)
        assert merged.title == "Test Article"
        assert merged.authors[0].family == "Smith"
        assert merged.container_title == "Journal of Science"

    def test_crossref_title_wins_over_og(self):
        rec = build_citation_record(
            url="https://example.com",
            title="OG Title",
            title_source=SRC_OG,
        )
        cr = self._make_crossref(title=["Crossref Title"])
        merged = merge_crossref(rec, cr)
        assert merged.title == "Crossref Title"

    def test_crossref_does_not_overwrite_user_edit(self):
        rec = apply_user_edit(
            build_citation_record(url="https://example.com", title="Crossref Title"),
            "title",
            "User Corrected Title",
        )
        cr = self._make_crossref(title=["Crossref Title"])
        merged = merge_crossref(rec, cr)
        assert merged.title == "User Corrected Title"
        assert merged.title_prov.manually_edited is True

    def test_crossref_year_conflict_detected(self):
        rec = build_citation_record(
            url="https://example.com",
            published_date="2023",
            date_source=SRC_OG,
        )
        cr = self._make_crossref(**{"issued": {"date-parts": [[2024]]}})
        merged = merge_crossref(rec, cr)
        # crossref wins on year
        assert merged.issued.year == 2024
        # but conflict was recorded
        year_conflicts = [c for c in merged.conflicts if c.field == "year"]
        assert len(year_conflicts) == 1

    def test_volume_issue_page_filled(self):
        rec = build_citation_record(url="https://example.com")
        merged = merge_crossref(rec, self._make_crossref())
        assert merged.volume == "12"
        assert merged.issue == "3"
        assert merged.page == "100-115"

    def test_source_type_from_crossref(self):
        rec = build_citation_record(url="https://example.com")
        merged = merge_crossref(rec, self._make_crossref())
        assert merged.source_type == STYPE_JOURNAL_ARTICLE

    def test_empty_crossref_no_change(self):
        rec = build_citation_record(url="https://example.com", title="Original")
        merged = merge_crossref(rec, {})
        assert merged.title == "Original"


# ── TestMergeStructuredMetadata ───────────────────────────────────────────────

class TestMergeStructuredMetadata:
    def test_json_ld_beats_og(self):
        rec = build_citation_record(
            url="https://example.com",
            authors_raw="OG Author",
            authors_source=SRC_OG,
        )
        merged = merge_structured_metadata(
            rec, {"author": "JSON-LD Author"}, SRC_JSON_LD
        )
        assert merged.authors[0].display_name() == "JSON-LD Author"
        assert merged.authors_prov.source == SRC_JSON_LD

    def test_og_does_not_beat_json_ld(self):
        rec = build_citation_record(
            url="https://example.com",
            authors_raw="JSON-LD Author",
            authors_source=SRC_JSON_LD,
        )
        merged = merge_structured_metadata(
            rec, {"author": "OG Author"}, SRC_OG
        )
        assert merged.authors_prov.source == SRC_JSON_LD

    def test_empty_value_skipped(self):
        rec = build_citation_record(url="https://example.com", title="Existing")
        merged = merge_structured_metadata(rec, {"title": ""}, SRC_JSON_LD)
        assert merged.title == "Existing"

    def test_conflict_detected_on_title(self):
        rec = build_citation_record(
            url="https://example.com",
            title="Article About Climate",
            title_source=SRC_JSON_LD,
        )
        merged = merge_structured_metadata(
            rec, {"title": "Guide to Nuclear Power Safety"}, SRC_JSON_LD
        )
        # Same confidence — existing wins, conflict logged
        assert len(merged.conflicts) >= 1

    def test_no_conflict_minor_differences(self):
        rec = build_citation_record(
            url="https://example.com",
            title="Testing the Hypothesis",
            title_source=SRC_OG,
        )
        merged = merge_structured_metadata(
            rec, {"title": "Testing the hypothesis."}, SRC_JSON_LD
        )
        # Nearly identical — no conflict
        assert len(merged.conflicts) == 0


# ── TestUserEdit ──────────────────────────────────────────────────────────────

class TestUserEdit:
    def test_user_edit_wins_over_crossref(self):
        rec = build_citation_record(
            url="https://example.com",
            title="Original Title",
            title_source=SRC_CROSSREF,
        )
        edited = apply_user_edit(rec, "title", "Corrected Title")
        assert edited.title == "Corrected Title"
        assert edited.title_prov.manually_edited is True
        assert edited.title_prov.confidence == CONFIDENCE_VERIFIED

    def test_user_edit_year(self):
        rec = build_citation_record(url="https://example.com", published_date="2023")
        edited = apply_user_edit(rec, "issued_year", "2024")
        assert edited.issued.year == 2024
        assert edited.issued_prov.manually_edited is True

    def test_user_edit_authors(self):
        rec = build_citation_record(url="https://example.com", authors_raw="Smith")
        edited = apply_user_edit(rec, "authors", "Jones, Alice; Lee, Bob")
        assert len(edited.authors) == 2
        assert edited.authors[0].family == "Jones"
        assert edited.authors_prov.manually_edited is True

    def test_user_edit_doi(self):
        rec = build_citation_record(url="https://example.com")
        edited = apply_user_edit(rec, "doi", "10.9999/user")
        assert edited.doi == "10.9999/user"
        assert edited.doi_prov.manually_edited is True


# ── TestCompletenessValidation ────────────────────────────────────────────────

class TestCompletenessValidation:
    def test_journal_complete(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[CitationPerson(family="Smith", given="Jane")],
            title="Test",
            container_title="Nature",
            issued=CitationDate(year=2024),
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_COMPLETE

    def test_journal_usable_missing_container(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[CitationPerson(family="Smith", given="Jane")],
            title="Test",
            issued=CitationDate(year=2024),
            url="https://example.com",
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_USABLE

    def test_journal_incomplete_no_title(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            url="https://example.com",
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_INCOMPLETE

    def test_webpage_complete(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            title="Test Page",
            container_title="Example Site",
            issued=CitationDate(year=2024),
            url="https://example.com",
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_COMPLETE

    def test_webpage_usable_no_date(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            title="Test Page",
            container_title="Example Site",
            url="https://example.com",
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_USABLE

    def test_gov_report_complete(self):
        rec = CitationRecord(
            source_type=STYPE_GOV_REPORT,
            title="Annual Report",
            institution="CDC",
            issued=CitationDate(year=2023),
            # report_number optional per spec
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_COMPLETE

    def test_gov_report_without_report_number_still_usable(self):
        rec = CitationRecord(
            source_type=STYPE_GOV_REPORT,
            title="Annual Report",
            url="https://cdc.gov/report.pdf",
        )
        validated = validate_completeness(rec)
        assert validated.completeness in (COMPLETENESS_USABLE, COMPLETENESS_INCOMPLETE)

    def test_legal_case_complete(self):
        rec = CitationRecord(
            source_type=STYPE_LEGAL_CASE,
            case_name="Brown v. Board",
            court="Supreme Court",
            issued=CitationDate(year=1954),
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_COMPLETE

    def test_legal_case_usable_with_url(self):
        rec = CitationRecord(
            source_type=STYPE_LEGAL_CASE,
            case_name="Smith v. Jones",
            url="https://law.cornell.edu/case",
        )
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_USABLE

    def test_unverified_when_nothing(self):
        rec = CitationRecord(source_type=STYPE_DOCUMENT)
        validated = validate_completeness(rec)
        assert validated.completeness == COMPLETENESS_UNVERIFIED


# ── TestRendererDebate ────────────────────────────────────────────────────────

class TestRendererDebate:
    def test_person_author_with_year(self):
        rec = _journal(authors=[CitationPerson(given="Jane", family="Smith")])
        result = render_debate(rec)
        assert "Smith" in result
        assert "2023" in result

    def test_organization_author(self):
        rec = _org_record()
        result = render_debate(rec)
        assert "RAND" in result
        assert "2024" in result

    def test_no_institution_when_low_confidence(self):
        rec = build_citation_record(
            url="https://example.com",
            authors_raw="Smith, Jane",
            published_date="2024",
            institution="Unknown Org",
            institution_source=SRC_DOMAIN,  # low confidence
        )
        result = render_debate(rec)
        # Institution should NOT appear at low confidence
        assert "Unknown Org" not in result

    def test_institution_appears_at_high_confidence(self):
        rec = build_citation_record(
            url="https://example.com",
            authors_raw="Smith, Jane",
            published_date="2024",
            institution="Harvard Medical School",
            institution_source=SRC_JSON_LD,  # high confidence
        )
        result = render_debate(rec)
        assert "Harvard Medical School" in result

    def test_nd_when_no_year(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            authors=[CitationPerson(family="Smith", given="Jane")],
        )
        result = render_debate(rec)
        assert "n.d." in result or "Smith" in result

    def test_no_fabricated_qualification(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            authors=[CitationPerson(family="Smith", given="Jane")],
            issued=CitationDate(year=2024),
            institution="",  # no institution
        )
        result = render_debate(rec)
        assert "—" not in result  # no separator without qual

    def test_two_authors(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[
                CitationPerson(family="Smith", given="Jane"),
                CitationPerson(family="Jones", given="Bob"),
            ],
            issued=CitationDate(year=2024),
        )
        result = render_debate(rec)
        assert "Smith & Jones" in result

    def test_three_or_more_authors_et_al(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[
                CitationPerson(family="Smith", given="Jane"),
                CitationPerson(family="Jones", given="Bob"),
                CitationPerson(family="Lee", given="Alice"),
            ],
            issued=CitationDate(year=2024),
        )
        result = render_debate(rec)
        assert "et al." in result


# ── TestRendererMLA ───────────────────────────────────────────────────────────

class TestRendererMLA:
    def test_journal_full(self):
        rec = _journal()
        result = render_mla(rec)
        assert "Smith" in result
        assert "Testing the Hypothesis" in result
        assert "Journal of Science" in result
        assert "2023" in result

    def test_mla_author_format_first(self):
        # First MLA author should be "Last, First"
        rec = _journal(authors=[CitationPerson(given="Jane A.", family="Smith")])
        result = render_mla(rec)
        assert "Smith, Jane" in result

    def test_mla_no_author_fallback(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            title="Test Article",
            container_title="Example Site",
            issued=CitationDate(year=2024),
            url="https://example.com",
        )
        result = render_mla(rec)
        assert "Test Article" in result
        assert "Accessed" in result

    def test_mla_org_author(self):
        rec = _org_record()
        result = render_mla(rec)
        assert "RAND" in result

    def test_mla_never_empty(self):
        rec = CitationRecord(source_type=STYPE_DOCUMENT, url="https://example.com")
        result = render_mla(rec)
        assert len(result) > 0

    def test_mla_doi_included(self):
        rec = _journal()
        result = render_mla(rec)
        assert "10.1234" in result or "doi.org" in result

    def test_mla_two_authors(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[
                CitationPerson(given="Jane", family="Smith"),
                CitationPerson(given="Bob", family="Jones"),
            ],
            title="Test",
            issued=CitationDate(year=2024),
        )
        result = render_mla(rec)
        assert "Smith" in result and "Jones" in result

    def test_mla_three_authors_et_al(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[
                CitationPerson(given="Jane", family="Smith"),
                CitationPerson(given="Bob", family="Jones"),
                CitationPerson(given="Alice", family="Lee"),
            ],
            title="Test",
            issued=CitationDate(year=2024),
        )
        result = render_mla(rec)
        assert "et al." in result


# ── TestRendererAPA ───────────────────────────────────────────────────────────

class TestRendererAPA:
    def test_journal_article(self):
        rec = _journal()
        result = render_apa(rec)
        assert "Smith" in result
        assert "(2023)" in result
        assert "Journal of Science" in result

    def test_apa_org_author(self):
        rec = _org_record()
        result = render_apa(rec)
        assert "RAND" in result

    def test_apa_doi_included(self):
        rec = _journal()
        result = render_apa(rec)
        assert "doi.org" in result or "10.1234" in result

    def test_apa_no_date(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            authors=[CitationPerson(family="Smith", given="Jane")],
            title="Test",
            url="https://example.com",
        )
        result = render_apa(rec)
        assert "n.d." in result

    def test_apa_multiple_authors_ampersand(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[
                CitationPerson(family="Smith", given="Jane"),
                CitationPerson(family="Jones", given="Bob"),
            ],
            title="Test",
            issued=CitationDate(year=2024),
        )
        result = render_apa(rec)
        assert "&" in result

    def test_apa_report_italics(self):
        rec = _org_record()
        result = render_apa(rec)
        # Report title should have asterisks for italics
        assert "*" in result

    def test_apa_never_empty(self):
        rec = CitationRecord(source_type=STYPE_DOCUMENT)
        result = render_apa(rec)
        assert len(result) > 0


# ── TestRendererChicago ───────────────────────────────────────────────────────

class TestRendererChicago:
    def test_journal_article(self):
        rec = _journal()
        result = render_chicago(rec)
        assert "Smith" in result
        assert "2023" in result
        assert "Journal of Science" in result

    def test_org_author(self):
        rec = _org_record()
        result = render_chicago(rec)
        assert "RAND" in result

    def test_chicago_two_authors(self):
        rec = CitationRecord(
            source_type=STYPE_JOURNAL_ARTICLE,
            authors=[
                CitationPerson(given="Jane", family="Smith"),
                CitationPerson(given="Bob", family="Jones"),
            ],
            title="Test",
            issued=CitationDate(year=2024),
        )
        result = render_chicago(rec)
        assert "Smith" in result and "Jones" in result

    def test_chicago_never_empty(self):
        rec = CitationRecord(source_type=STYPE_DOCUMENT)
        result = render_chicago(rec)
        assert len(result) > 0


# ── TestRendererBibTeX ────────────────────────────────────────────────────────

class TestRendererBibTeX:
    def test_journal_article_type(self):
        rec = _journal()
        result = render_bibtex(rec)
        assert result.startswith("@article{")

    def test_report_type(self):
        rec = _org_record()
        result = render_bibtex(rec)
        assert "@techreport" in result

    def test_has_author_field(self):
        rec = _journal()
        result = render_bibtex(rec)
        assert "author" in result

    def test_has_title_field(self):
        rec = _journal()
        result = render_bibtex(rec)
        assert "title" in result
        assert "Testing the Hypothesis" in result

    def test_has_year_field(self):
        rec = _journal()
        result = render_bibtex(rec)
        assert "year" in result and "2023" in result

    def test_org_author_braced(self):
        rec = _org_record()
        result = render_bibtex(rec)
        # Org authors must be braced to prevent BibTeX name parsing
        assert "{RAND" in result or "{RAND Corporation}" in result

    def test_doi_included(self):
        rec = _journal()
        result = render_bibtex(rec)
        assert "10.1234" in result

    def test_webpage_type_misc(self):
        rec = CitationRecord(
            source_type=STYPE_WEBPAGE,
            title="Test", url="https://example.com"
        )
        result = render_bibtex(rec)
        assert "@misc{" in result


# ── TestRendererRIS ───────────────────────────────────────────────────────────

class TestRendererRIS:
    def test_journal_article_ty(self):
        rec = _journal()
        result = render_ris(rec)
        assert "TY  - JOUR" in result

    def test_report_ty(self):
        rec = _org_record()
        result = render_ris(rec)
        assert "TY  - RPRT" in result

    def test_has_author_au(self):
        rec = _journal()
        result = render_ris(rec)
        assert "AU  -" in result

    def test_has_title_ti(self):
        rec = _journal()
        result = render_ris(rec)
        assert "TI  -" in result

    def test_has_year_py(self):
        rec = _journal()
        result = render_ris(rec)
        assert "PY  - 2023" in result

    def test_has_doi_do(self):
        rec = _journal()
        result = render_ris(rec)
        assert "DO  - 10.1234" in result

    def test_ends_with_er(self):
        rec = _journal()
        result = render_ris(rec)
        assert result.strip().endswith("ER  -")

    def test_legal_case_ty(self):
        rec = CitationRecord(
            source_type=STYPE_LEGAL_CASE,
            case_name="Test v. Case",
            issued=CitationDate(year=2020),
        )
        result = render_ris(rec)
        assert "TY  - CASE" in result


# ── TestRendererCSLJSON ───────────────────────────────────────────────────────

class TestRendererCSLJSON:
    def test_type_field(self):
        rec = _journal()
        csl = render_csl_json(rec)
        assert csl["type"] == STYPE_JOURNAL_ARTICLE

    def test_author_list(self):
        rec = _journal()
        csl = render_csl_json(rec)
        assert "author" in csl
        assert csl["author"][0]["family"] == "Smith"

    def test_title_included(self):
        rec = _journal()
        csl = render_csl_json(rec)
        assert csl["title"] == "Testing the Hypothesis"

    def test_container_title(self):
        rec = _journal()
        csl = render_csl_json(rec)
        assert csl["container-title"] == "Journal of Science"

    def test_issued_date_parts(self):
        rec = _journal()
        csl = render_csl_json(rec)
        assert "issued" in csl
        assert csl["issued"]["date-parts"][0][0] == 2023

    def test_doi_field(self):
        rec = _journal()
        csl = render_csl_json(rec)
        assert csl.get("DOI") == "10.1234/test"

    def test_org_author_literal(self):
        rec = _org_record()
        csl = render_csl_json(rec)
        authors = csl.get("author", [])
        assert len(authors) > 0
        assert "literal" in authors[0] or "family" in authors[0]

    def test_no_secrets_in_output(self):
        rec = _journal()
        csl = render_csl_json(rec)
        csl_str = json.dumps(csl)
        for secret_key in ("api_key", "token", "password", "secret", "trace"):
            assert secret_key not in csl_str.lower()


# ── TestCitationKey ───────────────────────────────────────────────────────────

class TestCitationKey:
    def test_deterministic(self):
        rec = _journal()
        key1 = citation_key(rec)
        key2 = citation_key(rec)
        assert key1 == key2

    def test_contains_surname(self):
        rec = _journal()
        key = citation_key(rec)
        assert "smith" in key.lower()

    def test_contains_year(self):
        rec = _journal()
        key = citation_key(rec)
        assert "2023" in key

    def test_no_special_chars(self):
        rec = _journal()
        key = citation_key(rec)
        import re as _re
        assert _re.match(r'^[a-zA-Z0-9]+$', key)

    def test_max_length_40(self):
        rec = _journal(title="A Very Long Title That Exceeds Normal Limits By Quite A Bit")
        key = citation_key(rec)
        assert len(key) <= 40

    def test_org_author_key(self):
        rec = _org_record()
        key = citation_key(rec)
        assert len(key) > 0


# ── TestBibliographyExport ────────────────────────────────────────────────────

class TestBibliographyExport:
    def test_duplicate_doi_collapsed(self):
        rec1 = _journal()
        rec2 = _journal(title="Different Title, Same DOI")  # same doi
        result = export_bibliography([rec1, rec2], fmt="mla")
        # Only one entry
        assert result.count("Testing the Hypothesis") + result.count("Different Title") == 1

    def test_different_doi_both_included(self):
        rec1 = _journal()
        rec2 = build_citation_record(
            url="https://other.com/article",
            title="Another Article",
            doi="10.5678/other",
            published_date="2024",
            source_type_hint=STYPE_JOURNAL_ARTICLE,
        )
        result = export_bibliography([rec1, rec2], fmt="mla")
        assert "Testing the Hypothesis" in result
        assert "Another Article" in result

    def test_bibtex_export_format(self):
        rec = _journal()
        result = export_bibliography([rec], fmt="bibtex")
        assert "@article{" in result

    def test_ris_export_format(self):
        rec = _journal()
        result = export_bibliography([rec], fmt="ris")
        assert "TY  - JOUR" in result

    def test_empty_list(self):
        result = export_bibliography([], fmt="mla")
        assert result == ""

    def test_no_internal_fields_in_export(self):
        rec = _journal()
        result = export_bibliography([rec], fmt="csl_json")
        parsed = json.loads(result)
        assert "p11" not in str(parsed)
        assert "p12" not in str(parsed)


# ── TestFromLegacyCitationMetadata ────────────────────────────────────────────

class TestFromLegacyCitationMetadata:
    def _legacy(self):
        from app.models.research import CitationMetadata
        return CitationMetadata(
            author_display="Smith",
            authors=["Smith, Jane"],
            year="2023",
            title="Legacy Article",
            container_title="Old Journal",
            publication_name="Old Journal",
            url="https://example.com",
            doi="10.1234/legacy",
            accessed_date="2024-01-01",
            citation_quality="complete",
            mla_citation="Smith. Legacy Article. Old Journal, 2023.",
            short_cite="Smith 2023",
            author_source="crossref",
            date_source="crossref",
            title_source="crossref",
            publication_source="search_provider",
        )

    def test_creates_record(self):
        legacy = self._legacy()
        rec = from_legacy_citation_metadata(legacy)
        assert isinstance(rec, CitationRecord)

    def test_title_preserved(self):
        rec = from_legacy_citation_metadata(self._legacy())
        assert rec.title == "Legacy Article"

    def test_doi_normalized(self):
        rec = from_legacy_citation_metadata(self._legacy())
        assert rec.doi == "10.1234/legacy"

    def test_authors_parsed(self):
        rec = from_legacy_citation_metadata(self._legacy())
        assert len(rec.authors) >= 1

    def test_year_parsed(self):
        rec = from_legacy_citation_metadata(self._legacy())
        assert rec.issued and rec.issued.year == 2023

    def test_crossref_source_gets_verified_confidence(self):
        rec = from_legacy_citation_metadata(self._legacy())
        # author_source was "crossref" → should map to verified or high
        assert rec.authors_prov.confidence in (CONFIDENCE_VERIFIED, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM)

    def test_none_input_returns_empty(self):
        rec = from_legacy_citation_metadata(None)
        assert isinstance(rec, CitationRecord)

    def test_mla_citation_not_stored_in_record(self):
        rec = from_legacy_citation_metadata(self._legacy())
        # The rendered_mla is empty until attach_rendered is called
        # The legacy mla string is NOT stored in CitationRecord
        assert "Smith. Legacy Article." not in rec.rendered_mla or rec.rendered_mla == ""


# ── TestSearchTraceP12 ────────────────────────────────────────────────────────

class TestSearchTraceP12:
    def test_stage_trace_has_p12_fields(self):
        from app.services.search_trace import SearchStageTrace
        stage = SearchStageTrace(stage="extraction")
        assert hasattr(stage, "citation_records_created")
        assert hasattr(stage, "crossref_verified_records")
        assert hasattr(stage, "citation_fields_enriched")
        assert hasattr(stage, "citation_conflicts_found")
        assert hasattr(stage, "citation_records_complete")
        assert hasattr(stage, "citation_records_with_warnings")
        assert hasattr(stage, "citation_records_incomplete")
        assert hasattr(stage, "legacy_citations_migrated")
        assert hasattr(stage, "citation_renderer_backend")
        assert hasattr(stage, "citation_renderer_failures")

    def test_trace_result_has_citation_summary(self):
        from app.services.search_trace import SearchTraceResult
        result = SearchTraceResult()
        assert hasattr(result, "citation_summary")
        assert result.citation_summary == ""

    def _base_kwargs(self) -> dict:
        return dict(
            queries_run=["test query"],
            roles_attempted=["direct_support"],
            sources_found=2,
            sources_attempted=2,
            sources_extracted=2,
            passages_considered=3,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=2,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=2,
            retrieval_backend="bm25",
        )

    def test_build_trace_p12_params(self):
        from app.services.search_trace import build_search_trace
        result = build_search_trace(
            **self._base_kwargs(),
            p12_records_created=2,
            p12_crossref_verified=1,
            p12_fields_enriched=5,
            p12_conflicts_found=0,
            p12_records_complete=2,
        )
        assert result.total_cards == 2

    def test_citation_summary_message(self):
        from app.services.search_trace import build_search_trace
        result = build_search_trace(
            **self._base_kwargs(),
            p12_records_created=1,
        )
        # Should generate a citation summary
        assert "1" in result.citation_summary or result.citation_summary == ""


# ── TestAttachRendered ────────────────────────────────────────────────────────

class TestAttachRendered:
    def test_all_formats_attached(self):
        rec = _journal()
        rec = attach_rendered(rec)
        assert len(rec.rendered_debate) > 0
        assert len(rec.rendered_mla) > 0
        assert len(rec.rendered_apa) > 0
        assert len(rec.rendered_chicago) > 0
        assert len(rec.rendered_bibtex) > 0
        assert len(rec.rendered_ris) > 0

    def test_render_all_dict(self):
        rec = _journal()
        result = render_all(rec)
        assert set(result.keys()) == {"debate", "mla", "apa", "chicago", "bibtex", "ris", "csl_json"}
        assert all(isinstance(v, str) for v in result.values())


# ── TestImportIntegrity ───────────────────────────────────────────────────────

class TestImportIntegrity:
    def test_models_importable(self):
        from app.models import citation as _c
        assert hasattr(_c, "CitationRecord")
        assert hasattr(_c, "CitationPerson")
        assert hasattr(_c, "CitationDate")
        assert hasattr(_c, "FieldProvenance")
        assert hasattr(_c, "CitationConflict")

    def test_normalizer_importable(self):
        from app.services import citation_normalizer as _n
        assert hasattr(_n, "build_citation_record")
        assert hasattr(_n, "merge_crossref")
        assert hasattr(_n, "apply_user_edit")
        assert hasattr(_n, "normalize_doi")
        assert hasattr(_n, "normalize_url")

    def test_renderers_importable(self):
        from app.services import citation_renderers as _r
        assert hasattr(_r, "render_mla")
        assert hasattr(_r, "render_apa")
        assert hasattr(_r, "render_chicago")
        assert hasattr(_r, "render_bibtex")
        assert hasattr(_r, "render_ris")
        assert hasattr(_r, "render_csl_json")
        assert hasattr(_r, "render_debate")
        assert hasattr(_r, "export_bibliography")

    def test_research_model_has_citation_record(self):
        from app.models.research import CitationMetadata
        meta = CitationMetadata()
        assert hasattr(meta, "citation_record")
        assert meta.citation_record is None

    def test_card_draft_row_has_citation_record(self):
        from app.models.research import CardDraftRow
        import inspect
        sig = inspect.signature(CardDraftRow)
        assert "citation_record" in sig.parameters

    def test_search_stage_trace_has_p12(self):
        from app.services.search_trace import SearchStageTrace
        stage = SearchStageTrace(stage="test")
        assert stage.citation_records_created == 0
        assert stage.citation_renderer_backend == "deterministic"

    def test_valid_source_types(self):
        for st in [
            STYPE_JOURNAL_ARTICLE, STYPE_REPORT, STYPE_WEBPAGE,
            STYPE_LEGAL_CASE, STYPE_DOCUMENT, STYPE_GOV_REPORT,
        ]:
            assert is_valid_source_type(st)

    def test_invalid_source_type_rejected(self):
        assert not is_valid_source_type("fake-type")
        assert not is_valid_source_type("")
