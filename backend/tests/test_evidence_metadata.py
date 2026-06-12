"""Tests for enhanced citation metadata extraction (Part 3)."""

from unittest.mock import patch

from app.services.card_cutting import enrich_citation_metadata
from app.services.web_article_extraction import (
    extract_metadata_from_html,
    organization_author_for_url,
)


def test_congress_gov_org_author():
    assert organization_author_for_url("https://www.congress.gov/bill/118") == "U.S. Congress"


def test_cfr_org_author():
    assert organization_author_for_url("https://www.cfr.org/article/intervention") == "Council on Foreign Relations"


def test_subdomain_org_author():
    assert (
        organization_author_for_url("https://crsreports.congress.gov/product/pdf/R/R12345")
        == "Congressional Research Service"
    )


def test_unknown_domain_no_org_author():
    assert organization_author_for_url("https://randomblog.example.com/post") == ""


def test_enrich_uses_org_heuristic_for_missing_author():
    cite = enrich_citation_metadata(
        url="https://www.congress.gov/bill/118/hr/1",
        author=None,
        title="A Bill",
        publication=None,
        published_date="2023-01-01",
    )
    assert cite.author_display == "U.S. Congress"
    assert cite.author_source == "organization_heuristic"


def test_schema_org_jsonld_parsed():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "NewsArticle", "headline": "Intervention Saves Lives",
     "author": {"@type": "Person", "name": "Jane Doe"},
     "datePublished": "2022-05-04T10:00:00Z",
     "publisher": {"@type": "Organization", "name": "Global Times"}}
    </script>
    </head><body></body></html>
    """
    md = extract_metadata_from_html("https://example.com/a", html, {})
    assert md["title"] == "Intervention Saves Lives"
    assert md["author"] == "Jane Doe"
    assert md["date"] == "2022-05-04"
    assert md["publication"] == "Global Times"
    assert md["provenance"]["title"] == "schema_org"


def test_meta_tag_extraction():
    html = """
    <html><head>
    <meta property="og:title" content="OG Headline" />
    <meta property="article:published_time" content="2021-03-02T08:00:00Z" />
    <meta name="author" content="John Smith" />
    </head><body></body></html>
    """
    md = extract_metadata_from_html("https://example.com/x", html, {})
    assert md["title"] == "OG Headline"
    assert md["date"] == "2021-03-02"
    assert md["author"] == "John Smith"
    assert md["provenance"]["title"] == "meta_tags"


def test_academic_citation_meta_tags():
    html = """
    <html><head>
    <meta name="citation_title" content="On Sovereignty" />
    <meta name="citation_author" content="Alice Brown" />
    <meta name="citation_author" content="Bob Green" />
    <meta name="citation_publication_date" content="2019/06/01" />
    <meta name="citation_journal_title" content="Journal of Ethics" />
    </head><body></body></html>
    """
    md = extract_metadata_from_html("https://example.com/p", html, {})
    assert md["title"] == "On Sovereignty"
    assert "Alice Brown" in md["author"]
    assert md["publication"] == "Journal of Ethics"


def test_zotero_skipped_when_disabled(monkeypatch):
    from app.services.zotero_extraction import extract_with_zotero
    from app.config import settings

    monkeypatch.setattr(settings, "research_enable_zotero", False, raising=False)
    assert extract_with_zotero("https://example.com/a") is None


def test_zotero_parsed_when_enabled(monkeypatch):
    from app.services import zotero_extraction
    from app.config import settings

    monkeypatch.setattr(settings, "research_enable_zotero", True, raising=False)
    monkeypatch.setattr(
        settings, "zotero_translation_server_url", "http://zotero.local:1969", raising=False
    )

    class _Resp:
        status_code = 200

        def json(self):
            return [{
                "itemType": "journalArticle",
                "title": "Intervention and Law",
                "creators": [{"creatorType": "author", "firstName": "Jane", "lastName": "Doe"}],
                "date": "2020-04-01",
                "publicationTitle": "Intl Law Review",
                "DOI": "10.1000/xyz",
            }]

    with patch("httpx.post", return_value=_Resp()):
        meta = zotero_extraction.extract_with_zotero("https://example.com/a")
    assert meta is not None
    assert meta.title == "Intervention and Law"
    assert meta.author == "Doe"
    assert meta.year == "2020"
    assert meta.publication == "Intl Law Review"
    assert meta.is_academic is True


def test_citation_provenance_fields_populated():
    cite = enrich_citation_metadata(
        url="https://www.brookings.edu/research/x",
        author=None,
        title="Brookings Report",
        publication="Brookings",
        published_date="2022",
    )
    assert cite.author_source == "organization_heuristic"
    assert cite.title_source  # non-empty
    assert cite.date_source
    assert cite.publication_source


# ── IEP / SEP / Known-domain fixture tests ────────────────────────────────────

def test_iep_gets_container_internet_encyclopedia_of_philosophy():
    """IEP URL → container_title = Internet Encyclopedia of Philosophy."""
    cite = enrich_citation_metadata(
        url="https://iep.utm.edu/armed-humanitarian-intervention/",
        author=None,
        title="Armed Humanitarian Intervention",
        publication=None,
        published_date=None,
    )
    assert "Internet Encyclopedia of Philosophy" in (cite.container_title or cite.publication_name)


def test_iep_org_author_is_iep():
    cite = enrich_citation_metadata(
        url="https://iep.utm.edu/just-war/",
        author=None,
        title=None,
        publication=None,
        published_date=None,
    )
    assert "Internet Encyclopedia of Philosophy" in cite.author_display


def test_sep_gets_container_stanford_encyclopedia():
    cite = enrich_citation_metadata(
        url="https://plato.stanford.edu/entries/war/",
        author=None,
        title="War",
        publication=None,
        published_date=None,
    )
    assert "Stanford Encyclopedia" in (cite.container_title or cite.publication_name)


def test_congress_gov_container_us_congress():
    cite = enrich_citation_metadata(
        url="https://www.congress.gov/bill/118/hr/1",
        author=None,
        title="HR 1",
        publication=None,
        published_date="2023",
    )
    assert "Congress" in (cite.container_title or cite.publication_name or cite.author_display)


def test_carnegie_gets_org_label():
    cite = enrich_citation_metadata(
        url="https://carnegieendowment.org/2024/01/policy",
        author=None,
        title="Policy Report",
        publication=None,
        published_date="2024",
    )
    assert "Carnegie" in (cite.publication_name or cite.container_title or cite.author_display)


def test_mla_never_empty_when_url_exists():
    """MLA citation must be non-empty for any card with a URL."""
    cite = enrich_citation_metadata(
        url="https://iep.utm.edu/armed-humanitarian-intervention/",
        author=None,
        title=None,
        publication=None,
        published_date=None,
    )
    assert cite.mla_citation.strip() != ""


def test_mla_contains_url_when_no_other_info():
    """If no metadata, MLA should at least contain the URL."""
    cite = enrich_citation_metadata(
        url="https://example.edu/article",
        author=None,
        title=None,
        publication=None,
        published_date=None,
    )
    assert "example.edu" in cite.mla_citation or "https://example.edu" in cite.mla_citation


def test_short_cite_uses_accessed_year_when_no_pub_date():
    """When year is unknown, short_cite uses org/domain instead of fabricating a year."""
    cite = enrich_citation_metadata(
        url="https://iep.utm.edu/intervention/",
        author=None,
        title=None,
        publication=None,
        published_date=None,
    )
    # Should not fabricate a year — short_cite should use org name or domain
    assert cite.short_cite  # non-empty
    assert not cite.short_cite.startswith("19") and not cite.short_cite.startswith("20") or cite.author_display


def test_iep_full_fixture():
    """Full IEP card fixture: Armed Humanitarian Intervention."""
    cite = enrich_citation_metadata(
        url="https://iep.utm.edu/armed-humanitarian-intervention/",
        author=None,
        title="Armed Humanitarian Intervention",
        publication=None,
        published_date=None,
        extracted_text=(
            "Humanitarian intervention is a use of military force by a state or group of states "
            "aimed at preventing or ending widespread and grave violations of the fundamental human rights "
            "of individuals other than its own citizens, without the permission of the state within whose "
            "territory force is applied. The word 'humanitarian' signals the moral purpose of such intervention — "
            "to protect, defend, or rescue people from gross abuse, extraordinary suffering, genocide, or "
            "large-scale violation of basic human rights. The Rwandan genocide of 1994 saw nearly one million "
            "people killed within weeks, yet the international community failed to intervene effectively."
        ),
    )
    # Should have: org author, title, publication label, non-empty MLA
    assert cite.author_display  # IEP org author
    assert cite.title == "Armed Humanitarian Intervention"
    assert cite.mla_citation.strip() != ""
    assert "iep.utm.edu" in cite.mla_citation or "Internet Encyclopedia" in cite.mla_citation
    assert cite.accessed_date  # access date always present


# ── TestPasteTextChromeStripping ───────────────────────────────────────────────

def test_paste_text_strips_breadcrumb():
    from app.services.web_article_extraction import extract_article_from_paste
    pasted = (
        "Home > Ozark Historical Review > Vol. 42 > Issue 1\n"
        "Ozark Historical Review\n"
        "Digital Commons @ University\n"
        "Included in the History Commons\n"
        "\n"
        "Since the end of World War II, the United States has engaged in numerous "
        "military interventions abroad to protect civilian populations from atrocities."
    )
    article = extract_article_from_paste(pasted)
    assert "Home >" not in article.extracted_text
    assert "Digital Commons" not in article.extracted_text
    assert "Since the end of World War II" in article.extracted_text


def test_paste_text_preserves_evidence_content():
    from app.services.web_article_extraction import extract_article_from_paste
    evidence = (
        "Humanitarian intervention is a use of military force aimed at preventing "
        "widespread violations of human rights. "
        "The Rwandan genocide of 1994 saw nearly one million people killed."
    )
    article = extract_article_from_paste(evidence)
    assert "Humanitarian intervention" in article.extracted_text
    assert "Rwandan genocide" in article.extracted_text


def test_url_extraction_strips_chrome_before_cutting():
    """Verify that strip_page_chrome is available and applies to paste text path."""
    from app.services.card_cutting import strip_page_chrome
    chrome_text = "Home > Journal > Vol 3\nDigital Commons\nIncluded in History Commons\n\nReal evidence sentence here."
    cleaned = strip_page_chrome(chrome_text)
    assert "Home >" not in cleaned
    assert "Digital Commons" not in cleaned
    assert "Real evidence sentence here" in cleaned
