"""Tests for the optional GROBID scholarly-PDF extraction integration.

All HTTP is mocked — NO live network calls. GROBID is always optional and every
function returns None/empty gracefully when unavailable.
"""

from unittest.mock import MagicMock, patch

from app.services.grobid_extraction import (
    GrobidMetadata,
    extract_with_grobid,
    is_pdf_url,
    parse_tei_metadata,
)


SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title level="a" type="main">Platform Liability and Section 230</title>
      </titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <author>
              <persName><forename type="first">Jane</forename><surname>Smith</surname></persName>
            </author>
            <author>
              <persName><forename type="first">Bob</forename><surname>Jones</surname></persName>
            </author>
          </analytic>
          <monogr>
            <title level="j">Harvard Law Review</title>
            <idno type="DOI">10.1000/example.230</idno>
            <imprint>
              <date type="published" when="2023-06-01">2023</date>
            </imprint>
          </monogr>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>
        <p>This paper examines how Section 230 grants platforms broad immunity from civil liability.</p>
      </abstract>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head>Introduction</head>
        <p>Section 230 of the Communications Decency Act provides broad immunity to online platforms. This section establishes the legal foundation for modern internet services and shapes content moderation.</p>
      </div>
    </body>
  </text>
</TEI>"""


class TestParseTeiMetadata:
    def test_parse_tei_metadata_extracts_title(self):
        meta = parse_tei_metadata(SAMPLE_TEI)
        assert meta.title == "Platform Liability and Section 230"

    def test_parse_tei_metadata_extracts_authors(self):
        meta = parse_tei_metadata(SAMPLE_TEI)
        assert "Jane Smith" in meta.authors
        assert "Bob Jones" in meta.authors
        assert meta.author_display == "Jane Smith et al."

    def test_parse_tei_metadata_extracts_year(self):
        meta = parse_tei_metadata(SAMPLE_TEI)
        assert meta.year == "2023"

    def test_parse_tei_metadata_extracts_abstract(self):
        meta = parse_tei_metadata(SAMPLE_TEI)
        assert "Section 230" in meta.abstract
        assert "immunity" in meta.abstract

    def test_parse_tei_metadata_extracts_journal_and_doi(self):
        meta = parse_tei_metadata(SAMPLE_TEI)
        assert meta.journal == "Harvard Law Review"
        assert meta.doi == "10.1000/example.230"

    def test_parse_tei_metadata_full_text_combines_abstract_and_body(self):
        meta = parse_tei_metadata(SAMPLE_TEI)
        assert meta.abstract in meta.full_text
        assert "Communications Decency Act" in meta.full_text

    def test_parse_tei_metadata_handles_malformed_xml(self):
        meta = parse_tei_metadata("<TEI><unclosed>")
        assert isinstance(meta, GrobidMetadata)
        assert meta.title == ""
        assert meta.authors == []


class TestIsPdfUrl:
    def test_is_pdf_url_detects_pdf_extension(self):
        assert is_pdf_url("https://example.com/paper.pdf") is True

    def test_is_pdf_url_detects_pdf_path(self):
        assert is_pdf_url("https://example.com/pdf/12345") is True

    def test_is_pdf_url_detects_download_path(self):
        assert is_pdf_url("https://example.com/download/article") is True

    def test_is_pdf_url_false_for_html(self):
        assert is_pdf_url("https://example.com/article.html") is False
        assert is_pdf_url("https://example.com/news/story") is False


class TestExtractWithGrobid:
    def test_extract_with_grobid_skipped_when_disabled(self):
        """No grobid_url → returns None without any HTTP."""
        with patch("app.services.grobid_extraction.httpx.get") as mock_get:
            result = extract_with_grobid("https://example.com/p.pdf", "")
        assert result is None
        mock_get.assert_not_called()

    def test_extract_with_grobid_skipped_for_non_pdf_url(self):
        """A successful download that is not a PDF returns None."""
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"<html>not a pdf</html>"
        resp.headers = {"content-type": "text/html"}
        with patch("app.services.grobid_extraction.httpx.get", return_value=resp):
            result = extract_with_grobid("https://example.com/page", "http://localhost:8070")
        assert result is None

    def test_extract_with_grobid_handles_download_failure(self):
        resp = MagicMock()
        resp.status_code = 404
        with patch("app.services.grobid_extraction.httpx.get", return_value=resp):
            result = extract_with_grobid("https://example.com/p.pdf", "http://localhost:8070")
        assert result is None

    def test_extract_with_grobid_handles_grobid_server_error(self):
        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.content = b"%PDF-1.4 fake pdf bytes"
        get_resp.headers = {"content-type": "application/pdf"}
        post_resp = MagicMock()
        post_resp.status_code = 500
        with patch("app.services.grobid_extraction.httpx.get", return_value=get_resp), \
             patch("app.services.grobid_extraction.httpx.post", return_value=post_resp):
            result = extract_with_grobid("https://example.com/p.pdf", "http://localhost:8070")
        assert result is None

    def test_extract_with_grobid_returns_metadata_on_success(self):
        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.content = b"%PDF-1.4 fake pdf bytes"
        get_resp.headers = {"content-type": "application/pdf"}
        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.text = SAMPLE_TEI
        with patch("app.services.grobid_extraction.httpx.get", return_value=get_resp), \
             patch("app.services.grobid_extraction.httpx.post", return_value=post_resp):
            result = extract_with_grobid("https://example.com/p.pdf", "http://localhost:8070")
        assert result is not None
        assert result.title == "Platform Liability and Section 230"
        assert result.year == "2023"

    def test_extract_with_grobid_handles_oversize_pdf(self):
        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.content = b"x" * (11 * 1024 * 1024)  # 11MB > 10MB limit
        get_resp.headers = {"content-type": "application/pdf"}
        with patch("app.services.grobid_extraction.httpx.get", return_value=get_resp):
            result = extract_with_grobid("https://example.com/p.pdf", "http://localhost:8070", max_pdf_mb=10)
        assert result is None
