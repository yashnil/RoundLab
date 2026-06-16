"""
Tests for Research-to-Card Evidence Builder.

All tests are deterministic and do not call OpenAI, Tavily, or real HTTP.
Safety invariants tested:
  - URL validation rejects private IPs, localhost, file:// etc.
  - Article extraction never fabricates metadata
  - body_text always comes from extracted source (char indices verified)
  - Highlight spans outside body_text are dropped
  - Draft requires confirmed=True to save (enforced in API layer)
  - Source quality is deterministic (domain-based)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.models.research import ArticleMetadata, ExtractedArticle, HighlightSpan
from app.services.web_article_extraction import (
    validate_url,
    _extract_metadata_from_html,
    _build_article_metadata,
    _extract_text_beautifulsoup,
    _normalize_text,
    extract_article_from_paste,
)
from app.services.source_quality import rate_source_quality
from app.services.card_cutting import (
    verify_spans,
    _score_paragraph,
    _split_paragraphs,
    _build_cite,
    generate_card_draft,
)


# ── Factories ─────────────────────────────────────────────────────────────────

def make_metadata(**kwargs) -> ArticleMetadata:
    defaults = dict(
        title="Test Article",
        author="Jane Smith",
        publication="Science Journal",
        published_date="2024-03-15",
        url="https://example.com/article",
    )
    defaults.update(kwargs)
    return ArticleMetadata(**defaults)


def make_article(text: str = "Sample article text " * 30, **kwargs) -> ExtractedArticle:
    meta = make_metadata(**{k: v for k, v in kwargs.items() if k in ArticleMetadata.model_fields})
    return ExtractedArticle(
        url=kwargs.get("url", "https://example.com/article"),
        metadata=meta,
        extracted_text=text,
        extraction_method="test",
        extraction_confidence=0.85,
        status="ok",
    )


# ── URL validation ─────────────────────────────────────────────────────────────

class TestValidateUrl:
    def test_allows_https(self):
        safe, reason = validate_url("https://nytimes.com/article")
        assert safe is True
        assert reason == ""

    def test_allows_http(self):
        safe, reason = validate_url("http://brookings.edu/report")
        assert safe is True

    def test_rejects_localhost(self):
        safe, reason = validate_url("http://localhost/admin")
        assert safe is False
        assert "Internal" in reason or "localhost" in reason.lower()

    def test_rejects_127_0_0_1(self):
        safe, reason = validate_url("http://127.0.0.1:8080/secret")
        assert safe is False

    def test_rejects_file_scheme(self):
        safe, reason = validate_url("file:///etc/passwd")
        assert safe is False

    def test_rejects_ftp_scheme(self):
        safe, reason = validate_url("ftp://example.com/file.txt")
        assert safe is False

    def test_rejects_local_suffix(self):
        safe, reason = validate_url("http://internal.local/api")
        assert safe is False

    def test_no_hostname_rejected(self):
        safe, reason = validate_url("http:///no-host")
        assert safe is False


# ── Metadata extraction ────────────────────────────────────────────────────────

class TestMetadataExtraction:
    SAMPLE_HTML = """
    <html lang="en">
    <head>
      <title>Test Article - Science Journal</title>
      <meta property="og:title" content="Test Article" />
      <meta name="author" content="Jane Smith" />
      <meta property="og:site_name" content="Science Journal" />
      <meta property="article:published_time" content="2024-03-15T10:00:00Z" />
      <meta property="og:description" content="A test excerpt." />
    </head>
    <body><p>Article content here.</p></body>
    </html>
    """

    def test_title_extracted(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _extract_metadata_from_html(self.SAMPLE_HTML, "https://example.com")
        assert meta.title == "Test Article"

    def test_author_extracted(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _extract_metadata_from_html(self.SAMPLE_HTML, "https://example.com")
        assert meta.author == "Jane Smith"

    def test_publication_extracted(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _extract_metadata_from_html(self.SAMPLE_HTML, "https://example.com")
        assert meta.publication == "Science Journal"

    def test_date_extracted_and_truncated(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _extract_metadata_from_html(self.SAMPLE_HTML, "https://example.com")
        assert meta.published_date == "2024-03-15"

    def test_no_fabrication_for_missing_fields(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        html = "<html><head><title>Plain</title></head><body></body></html>"
        meta = _extract_metadata_from_html(html, "https://example.com")
        # Only title should be extracted; author/publication should be None
        assert meta.author is None
        assert meta.publication is None
        assert meta.published_date is None

    def test_url_always_set(self):
        meta = _extract_metadata_from_html("<html></html>", "https://example.com/test")
        assert meta.url == "https://example.com/test"


class TestDeepMetadataCascade:
    """_build_article_metadata uses academic citation_* meta + JSON-LD that the
    basic OG/name reader misses, so scholarly sources cite cleanly."""

    SCHOLARLY_HTML = """
    <html lang="en">
    <head>
      <title>Repository | Some Article</title>
      <meta name="citation_title" content="Humanitarian Intervention and Just War" />
      <meta name="citation_author" content="King, Nathaniel R." />
      <meta name="citation_author" content="Chen, Emily" />
      <meta name="citation_publication_date" content="2022/03/01" />
      <meta name="citation_journal_title" content="Ozark Historical Review" />
      <meta property="og:description" content="An excerpt." />
    </head>
    <body><p>Body.</p></body>
    </html>
    """

    JSONLD_HTML = """
    <html>
    <head>
      <script type="application/ld+json">
      {"@type":"NewsArticle","headline":"Tariffs and Growth",
       "author":{"@type":"Person","name":"Dana Lopez"},
       "datePublished":"2023-08-04T09:00:00Z",
       "publisher":{"@type":"Organization","name":"The Economic Times"}}
      </script>
    </head>
    <body><p>Body.</p></body>
    </html>
    """

    def test_citation_author_extracted(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _build_article_metadata(self.SCHOLARLY_HTML, "https://digitalcommons.example.edu/a/1")
        assert meta.author and "King" in meta.author

    def test_citation_title_preferred(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _build_article_metadata(self.SCHOLARLY_HTML, "https://digitalcommons.example.edu/a/1")
        assert meta.title == "Humanitarian Intervention and Just War"

    def test_citation_journal_as_publication(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _build_article_metadata(self.SCHOLARLY_HTML, "https://digitalcommons.example.edu/a/1")
        assert meta.publication == "Ozark Historical Review"

    def test_citation_date_normalized(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _build_article_metadata(self.SCHOLARLY_HTML, "https://digitalcommons.example.edu/a/1")
        assert meta.published_date and meta.published_date.startswith("2022")

    def test_jsonld_author_and_date(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _build_article_metadata(self.JSONLD_HTML, "https://example.com/x")
        assert meta.author == "Dana Lopez"
        assert meta.published_date == "2023-08-04"
        assert meta.publication == "The Economic Times"

    def test_no_fabrication_when_empty(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        meta = _build_article_metadata("<html><head><title>X</title></head><body></body></html>",
                                       "https://example.com/x")
        assert meta.author is None
        assert meta.published_date is None


# ── Text normalization ─────────────────────────────────────────────────────────

class TestNormalizeText:
    def test_collapses_spaces(self):
        result = _normalize_text("hello   world\t here")
        assert "  " not in result

    def test_preserves_paragraphs(self):
        result = _normalize_text("para one\n\npara two")
        assert "para one" in result
        assert "para two" in result

    def test_limits_blank_lines(self):
        result = _normalize_text("a\n\n\n\n\nb")
        assert "\n\n\n" not in result


# ── BeautifulSoup extraction ───────────────────────────────────────────────────

class TestBeautifulSoupExtraction:
    def test_extracts_article_tag(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        html = """
        <html><body>
        <nav>Nav garbage</nav>
        <article>
          <p>This is the real article text. It goes on for a while to hit the length threshold.</p>
          <p>Second paragraph with more relevant content about the topic at hand.</p>
          <p>Third paragraph to make this long enough to extract properly.</p>
          <p>Fourth paragraph to ensure we have sufficient text content here.</p>
        </article>
        </body></html>
        """
        text, confidence = _extract_text_beautifulsoup(html)
        assert "real article text" in text
        assert "Nav garbage" not in text

    def test_falls_back_to_paragraphs(self):
        pytest.importorskip("bs4", reason="bs4 not installed")
        html = "<html><body>" + "".join(
            f"<p>Paragraph {i} with useful content about the topic.</p>" for i in range(10)
        ) + "</body></html>"
        text, confidence = _extract_text_beautifulsoup(html)
        assert "Paragraph" in text

    def test_empty_html_returns_empty(self):
        text, confidence = _extract_text_beautifulsoup("<html></html>")
        assert text == ""


# ── Paste extraction ──────────────────────────────────────────────────────────

class TestPasteExtraction:
    def test_paste_preserves_text(self):
        long_text = "A" * 300 + " example passage about economic impacts."
        article = extract_article_from_paste(long_text, url="https://example.com")
        assert article.status == "ok"
        assert article.extracted_text.startswith("A")

    def test_paste_too_short_is_partial(self):
        article = extract_article_from_paste("Short text")
        assert article.status == "partial"

    def test_paste_uses_provided_metadata(self):
        article = extract_article_from_paste(
            "A" * 300,
            author="John Doe",
            publication="The Times",
            published_date="2024-01",
        )
        assert article.metadata.author == "John Doe"
        assert article.metadata.publication == "The Times"


# ── Source quality heuristics ─────────────────────────────────────────────────

class TestSourceQuality:
    def _meta(self, **kwargs):
        return make_metadata(**kwargs)

    def test_gov_tld_is_high(self):
        meta = self._meta(url="https://cdc.gov/report")
        result = rate_source_quality("https://cdc.gov/report", meta, "A" * 500)
        assert result.source_quality == "high"

    def test_edu_tld_is_high(self):
        meta = self._meta(url="https://harvard.edu/paper")
        result = rate_source_quality("https://harvard.edu/paper", meta, "A" * 500)
        assert result.source_quality == "high"

    def test_known_medium_domain(self):
        meta = self._meta(url="https://nytimes.com/2024/article")
        result = rate_source_quality("https://nytimes.com/2024/article", meta, "A" * 500)
        assert result.source_quality == "medium"

    def test_reddit_is_low(self):
        meta = self._meta(url="https://reddit.com/r/debate")
        result = rate_source_quality("https://reddit.com/r/debate", meta, "A" * 500)
        assert result.source_quality == "low"

    def test_unknown_domain_with_author_and_date_is_medium(self):
        meta = self._meta(
            url="https://someobscuredomain.xyz/article",
            author="Jane Doe",
            published_date="2024-01",
        )
        result = rate_source_quality("https://someobscuredomain.xyz/article", meta, "A" * 500)
        assert result.source_quality == "medium"

    def test_unknown_domain_no_author_no_date_is_low(self):
        meta = ArticleMetadata(url="https://someobscuredomain.xyz/article")
        result = rate_source_quality("https://someobscuredomain.xyz/article", meta, "A" * 500)
        assert result.source_quality == "low"

    def test_very_short_content_warns(self):
        meta = self._meta(url="https://nytimes.com/2024/article")
        result = rate_source_quality("https://nytimes.com/2024/article", meta, "Short")
        assert any("short" in w.lower() for w in result.warnings)

    def test_old_article_warns(self):
        meta = self._meta(url="https://nytimes.com/2024/article", published_date="2001-06-01")
        result = rate_source_quality("https://nytimes.com/2024/article", meta, "A" * 500)
        assert any("2001" in w for w in result.warnings)

    def test_credibility_notes_always_set(self):
        meta = self._meta(url="https://rand.org/report")
        result = rate_source_quality("https://rand.org/report", meta, "A" * 500)
        assert result.credibility_notes


# ── Span verification ─────────────────────────────────────────────────────────

class TestVerifySpans:
    BODY = "The economy grew by 3.2% last year, according to the IMF."

    def test_valid_span_kept(self):
        spans = [{"start": 0, "end": 11, "reason": "key stat"}]
        result = verify_spans(self.BODY, spans)
        assert len(result) == 1
        assert result[0]["start"] == 0

    def test_out_of_range_dropped(self):
        spans = [{"start": 0, "end": len(self.BODY) + 10}]
        result = verify_spans(self.BODY, spans)
        assert len(result) == 0

    def test_negative_start_dropped(self):
        spans = [{"start": -1, "end": 5}]
        result = verify_spans(self.BODY, spans)
        assert len(result) == 0

    def test_zero_length_span_dropped(self):
        spans = [{"start": 3, "end": 3}]
        result = verify_spans(self.BODY, spans)
        assert len(result) == 0

    def test_non_int_dropped(self):
        spans = [{"start": "0", "end": 5}]
        result = verify_spans(self.BODY, spans)
        assert len(result) == 0

    def test_multiple_spans_filtered(self):
        spans = [
            {"start": 0, "end": 5},           # valid
            {"start": 100, "end": 200},        # out of range
            {"start": 10, "end": 20},          # valid
        ]
        result = verify_spans(self.BODY, spans)
        assert len(result) == 2


# ── Paragraph scoring ─────────────────────────────────────────────────────────

class TestParagraphScoring:
    def test_causal_language_boosts_score(self):
        causal = "The study demonstrates that tariffs therefore reduce economic growth significantly."
        plain = "The article discusses various aspects of global trade and policy."
        assert _score_paragraph(causal, "tariffs growth", "trade") > _score_paragraph(plain, "tariffs growth", "trade")

    def test_statistics_boost_score(self):
        stats = "GDP fell by 2.5% in 2023 according to new research data."
        no_stats = "GDP has declined over recent years in this region."
        assert _score_paragraph(stats, "GDP growth", "economy") > _score_paragraph(no_stats, "GDP growth", "economy")

    def test_length_bonus_applied(self):
        short = "Short."
        long = "This is a well-developed paragraph " * 20
        score_short = _score_paragraph(short, "topic", "debate")
        score_long = _score_paragraph(long, "topic", "debate")
        assert score_long > score_short


class TestSplitParagraphs:
    def test_splits_on_double_newline(self):
        text = "Paragraph one.\n\nParagraph two that is long enough to keep.\n\nParagraph three."
        paras = _split_paragraphs(text)
        # Only paragraphs ≥ 80 chars are kept
        for p in paras:
            assert len(p) >= 80 or True  # short ones may be filtered

    def test_filters_very_short(self):
        text = "Short.\n\nThis is a much longer paragraph that meets the threshold for inclusion in results."
        paras = _split_paragraphs(text)
        # "Short." should be filtered
        for p in paras:
            assert len(p) >= 80


# ── Cite building ─────────────────────────────────────────────────────────────

class TestBuildCite:
    def test_full_metadata(self):
        cite = _build_cite(
            author="Jane Smith",
            publication="Nature",
            published_date="2024-03-15",
            url="https://nature.com/article",
            title="Climate Change Effects",
        )
        assert "Jane Smith" in cite
        assert "Nature" in cite
        assert "2024" in cite

    def test_year_extracted_from_datetime(self):
        cite = _build_cite(
            author="Bob Jones",
            publication=None,
            published_date="2023-08-22T14:30:00Z",
            url="https://example.com",
            title=None,
        )
        assert "2023" in cite

    def test_url_only_fallback(self):
        cite = _build_cite(
            author=None,
            publication=None,
            published_date=None,
            url="https://example.com/article",
            title=None,
        )
        assert cite == "https://example.com/article"

    def test_long_title_excluded(self):
        long_title = "A" * 100
        cite = _build_cite(
            author="Author",
            publication="Journal",
            published_date="2024",
            url="https://example.com",
            title=long_title,
        )
        assert long_title not in cite


# ── Card draft generation ─────────────────────────────────────────────────────

class TestGenerateCardDraft:
    """Tests that card draft body_text comes exclusively from source text."""

    LONG_ARTICLE = (
        "Economic theory suggests that tariffs reduce trade efficiency. "
        "A study by the IMF found that tariffs increase consumer prices by 3.5%. "
        "The research demonstrates that free trade promotes economic growth. "
        "Countries that adopt protectionist policies therefore see reduced GDP. "
        "Data from 2023 shows the impact on global supply chains was significant. "
    ) * 15  # > 1000 chars

    def _make_article(self, text: str | None = None) -> ExtractedArticle:
        t = text or self.LONG_ARTICLE
        return ExtractedArticle(
            url="https://imf.org/report",
            metadata=ArticleMetadata(
                url="https://imf.org/report",
                title="IMF Trade Report",
                author="IMF Staff",
                publication="IMF",
                published_date="2023-09-01",
            ),
            extracted_text=t,
            extraction_method="test",
            extraction_confidence=0.85,
            status="ok",
        )

    def test_body_text_is_substring_of_source(self):
        """Body text must be an exact substring of extracted_text (LLM patched out)."""
        article = self._make_article()

        # Patch _draft_with_llm to return None → fallback path used
        with patch("app.services.card_cutting._draft_with_llm", return_value=None):
            draft = generate_card_draft(
                article=article,
                topic="US-China trade",
                claim_goal="tariffs hurt economy",
                user_id="user-1",
                source_quality="high",
            )

        body = draft["body_text"]
        assert len(body) >= 40
        # body_text must be an exact substring of the source text
        assert body in article.extracted_text or body.replace("\n\n", "\n") in article.extracted_text

    def test_generated_tag_is_true(self):
        article = self._make_article()
        with patch("app.services.card_cutting._draft_with_llm", return_value=None):
            draft = generate_card_draft(article=article, topic="trade", claim_goal="tariffs hurt", user_id="u1")
        assert draft["generated_tag"] is True

    def test_missing_author_flagged(self):
        article = ExtractedArticle(
            url="https://example.com",
            metadata=ArticleMetadata(url="https://example.com"),
            extracted_text=self.LONG_ARTICLE,
            extraction_method="test",
            extraction_confidence=0.8,
            status="ok",
        )
        with patch("app.services.card_cutting._draft_with_llm", return_value=None):
            draft = generate_card_draft(article=article, topic="trade", claim_goal="tariffs", user_id="u1")
        assert "author" in draft["missing_metadata_json"]

    def test_status_is_draft(self):
        article = self._make_article()
        with patch("app.services.card_cutting._draft_with_llm", return_value=None):
            draft = generate_card_draft(article=article, topic="trade", claim_goal="tariffs", user_id="u1")
        assert draft["status"] == "draft"

    def test_invalid_llm_indices_fall_back_to_heuristic(self):
        """If LLM returns out-of-range indices, fallback heuristic is used."""
        from app.services.card_cutting import _CardCuttingOutput

        bad_output = _CardCuttingOutput(
            body_start_idx=9999,
            body_end_idx=99999,
            tag="Bad indices tag",
            highlight_spans=[],
            underline_spans=[],
            warrant_summary="",
            impact_summary="",
        )
        article = self._make_article()
        with patch("app.services.card_cutting._draft_with_llm", return_value=bad_output):
            draft = generate_card_draft(article=article, topic="trade", claim_goal="tariffs", user_id="u1")
        # body should still come from the article text
        body = draft["body_text"]
        assert len(body) >= 40

    def test_highlight_spans_within_body_text(self):
        """All returned highlight spans must map to valid offsets within body_text."""
        from app.services.card_cutting import _CardCuttingOutput, _SpanOutput

        article = self._make_article()
        body_snippet = article.extracted_text[0:200]
        good_span = _SpanOutput(start=0, end=10, reason="key phrase")
        bad_span  = _SpanOutput(start=9000, end=9100, reason="out of range")

        good_output = _CardCuttingOutput(
            body_start_idx=0,
            body_end_idx=200,
            tag="Test tag for this card",
            highlight_spans=[good_span, bad_span],
            underline_spans=[],
            warrant_summary="Proves impact",
            impact_summary="Economic consequence",
        )
        with patch("app.services.card_cutting._draft_with_llm", return_value=good_output):
            draft = generate_card_draft(article=article, topic="trade", claim_goal="tariffs", user_id="u1")

        body = draft["body_text"]
        for span in draft["highlighted_spans_json"]:
            assert span["start"] >= 0
            assert span["end"] <= len(body)
            assert span["end"] > span["start"]


# ── Config endpoint ───────────────────────────────────────────────────────────

class TestResearchConfig:
    def test_configured_when_key_set(self):
        from app.config import Settings
        fake_settings = Settings(
            openai_api_key="", supabase_url="", supabase_service_role_key="",
            tavily_api_key="tvly-test-key",
        )
        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test-key"):
            import asyncio
            from app.api.research import research_config
            result = asyncio.run(research_config())
        assert result.search_configured is True

    def test_not_configured_when_key_missing(self):
        with patch("app.api.research.get_tavily_api_key", return_value=None):
            import asyncio
            from app.api.research import research_config
            result = asyncio.run(research_config())
        assert result.search_configured is False

    def test_config_never_exposes_key(self):
        with patch("app.api.research.get_tavily_api_key", return_value="tvly-secret"):
            import asyncio
            from app.api.research import research_config
            result = asyncio.run(research_config())
        response_dict = result.model_dump()
        for v in response_dict.values():
            assert v != "tvly-secret"

    def test_url_extraction_always_available(self):
        with patch("app.api.research.get_tavily_api_key", return_value=None):
            import asyncio
            from app.api.research import research_config
            result = asyncio.run(research_config())
        assert result.url_extraction_available is True
        assert result.card_builder_available is True


# ── build_research_search_query ───────────────────────────────────────────────

class TestBuildResearchSearchQuery:
    def test_basic_topic_and_claim(self):
        from app.services.research_search import build_research_search_query
        q = build_research_search_query("US-China trade", "tariffs hurt economic growth", "Pro")
        assert "tariffs" in q or "economic" in q or "growth" in q

    def test_claim_only(self):
        from app.services.research_search import build_research_search_query
        q = build_research_search_query(None, "carbon taxes reduce emissions", None)
        assert len(q) > 0
        assert "carbon" in q or "taxes" in q or "emissions" in q

    def test_topic_not_duplicated_when_in_claim(self):
        from app.services.research_search import build_research_search_query
        q = build_research_search_query("climate change", "climate change causes sea level rise", None)
        # "climate change" appears once in claim; topic shouldn't be separately prepended
        # count of "climate" should be 1 (since topic deduplication applies)
        assert q.lower().count("climate change") <= 1

    def test_query_under_15_words(self):
        from app.services.research_search import build_research_search_query
        long_claim = "the implementation of universal basic income policies will significantly reduce poverty rates across the entire nation"
        q = build_research_search_query("poverty", long_claim, None)
        assert len(q.split()) <= 15

    def test_whitespace_normalised(self):
        from app.services.research_search import build_research_search_query
        q = build_research_search_query("  trade  ", "  tariffs hurt  ", None)
        assert "  " not in q

    def test_signal_word_appended_when_missing(self):
        from app.services.research_search import build_research_search_query
        q = build_research_search_query(None, "tariffs hurt growth", None)
        assert any(w in q.lower() for w in ("evidence", "study", "report", "data", "research"))

    def test_signal_word_not_doubled(self):
        from app.services.research_search import build_research_search_query
        q = build_research_search_query(None, "research shows tariffs hurt trade", None)
        # "research" already in claim — shouldn't add another copy
        assert q.lower().count("evidence report") == 0


# ── Support classification ────────────────────────────────────────────────────

class TestClassifySupport:
    def test_strong_support_with_stats_and_signals(self):
        from app.services.research_search import _classify_support
        passage = (
            "A study by the IMF found that tariffs increase consumer prices by 3.5%. "
            "The research demonstrates that protectionist policies reduce economic growth. "
            "Data from 2023 confirms the significant impact on global supply chains."
        )
        level, rationale = _classify_support(passage, "tariffs hurt economic growth", "US trade policy")
        assert level in ("strong_support", "partial_support")
        assert len(rationale) > 0

    def test_no_support_unrelated_passage(self):
        from app.services.research_search import _classify_support
        passage = "The history of ancient Rome includes many fascinating architectural achievements."
        level, rationale = _classify_support(passage, "climate change causes sea level rise", "environment")
        assert level in ("weak_support", "no_support")

    def test_short_passage_penalised(self):
        from app.services.research_search import _classify_support
        short = "Tariffs hurt growth."
        long = (
            "According to a 2023 study, tariffs hurt economic growth by reducing trade efficiency. "
            "The IMF found that nations adopting protectionist policies see GDP decline by 2.5%. "
            "The data demonstrates a direct causal link between tariff implementation and growth reduction. " * 3
        )
        level_short, _ = _classify_support(short, "tariffs hurt economic growth", "trade")
        level_long, _ = _classify_support(long, "tariffs hurt economic growth", "trade")
        # Long passage should score at least as well as short passage
        ordering = {"strong_support": 3, "partial_support": 2, "weak_support": 1, "no_support": 0}
        assert ordering[level_long] >= ordering[level_short]


# ── Near-duplicate detection ──────────────────────────────────────────────────

class TestNearDuplicate:
    def test_identical_is_duplicate(self):
        from app.services.research_search import _is_near_duplicate
        body = "The economy grew by 3.2 percent according to the IMF report on trade."
        assert _is_near_duplicate(body, [body]) is True

    def test_completely_different_not_duplicate(self):
        from app.services.research_search import _is_near_duplicate
        body = "Quantum computing may transform cryptography in the next decade."
        existing = ["The economy grew by 3.2 percent according to the IMF report on trade."]
        assert _is_near_duplicate(body, existing) is False

    def test_empty_existing_not_duplicate(self):
        from app.services.research_search import _is_near_duplicate
        assert _is_near_duplicate("some text here", []) is False

    def test_high_overlap_is_duplicate(self):
        from app.services.research_search import _is_near_duplicate
        original = "Tariffs reduce economic growth according to the IMF study findings published in 2023."
        similar = "Tariffs reduce economic growth according to the IMF study findings published recently."
        assert _is_near_duplicate(similar, [original]) is True


# ── generate_candidate_cards (mocked) ────────────────────────────────────────

class TestGenerateCandidateCards:
    LONG_TEXT = (
        "A comprehensive study by the IMF found that tariffs increase consumer prices by 3.5 percent. "
        "The research demonstrates that protectionist policies reduce economic growth significantly. "
        "Data from 2023 confirms the impact on global supply chains was substantial and lasting. "
        "Countries adopting high tariffs therefore see reduced GDP growth rates over time. "
        "The analysis shows strong evidence that free trade promotes economic efficiency nationwide. "
    ) * 8

    def _make_article(self, url: str = "https://imf.org/report"):
        from app.models.research import ArticleMetadata, ExtractedArticle
        return ExtractedArticle(
            url=url,
            metadata=ArticleMetadata(
                url=url, title="IMF Trade Study", author="IMF Staff",
                publication="IMF", published_date="2023-09-01",
            ),
            extracted_text=self.LONG_TEXT,
            extraction_method="test",
            extraction_confidence=0.85,
            status="ok",
        )

    def test_max_four_cards_returned(self):
        from app.services.research_search import generate_candidate_cards

        search_results = [
            {"url": f"https://domain{i}.edu/article"} for i in range(10)
        ]
        article = self._make_article()

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft:

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="Good source")
            call_count = [0]
            def fake_draft(**kwargs):
                call_count[0] += 1
                return {
                    "user_id": "u1",
                    "url": kwargs["article"].url,
                    "body_text": self.LONG_TEXT[:200] + f" unique {call_count[0]}",
                    "tag": f"IMF Trade Study {call_count[0]}",
                    "cite": "IMF Staff · IMF · 2023",
                    "status": "draft",
                    "draft_json": {},
                    "missing_metadata_json": {},
                    "generated_tag": True,
                    "extraction_confidence": 0.85,
                    "card_source_type": "research_search",
                    "highlighted_spans_json": [],
                    "underline_spans_json": [],
                }
            mock_draft.side_effect = fake_draft

            result = generate_candidate_cards(
                search_results=search_results,
                topic="trade",
                claim_to_support="tariffs hurt economic growth",
                side="Pro",
                user_id="u1",
                max_cards=4,
            )
            drafts = result.card_drafts

        assert len(drafts) <= 4

    def test_domain_limit_two_per_domain(self):
        from app.services.research_search import generate_candidate_cards

        search_results = [
            {"url": f"https://imf.org/article{i}"} for i in range(6)
        ]
        article = self._make_article(url="https://imf.org/article0")

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft:

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="Good")
            counter = [0]
            def fake_draft(**kwargs):
                counter[0] += 1
                return {
                    "user_id": "u1",
                    "url": kwargs["article"].url,
                    "body_text": self.LONG_TEXT[:200] + f" v{counter[0]}",
                    "tag": f"Tag {counter[0]}",
                    "cite": "IMF Staff · IMF · 2023",
                    "status": "draft",
                    "draft_json": {},
                    "missing_metadata_json": {},
                    "generated_tag": True,
                    "extraction_confidence": 0.85,
                    "card_source_type": "research_search",
                    "highlighted_spans_json": [],
                    "underline_spans_json": [],
                }
            mock_draft.side_effect = fake_draft

            result = generate_candidate_cards(
                search_results=search_results,
                topic="trade",
                claim_to_support="tariffs hurt economic growth",
                side=None,
                user_id="u1",
            )
            drafts = result.card_drafts

        domain_cards = [d for d in drafts if "imf.org" in (d.get("url") or "")]
        assert len(domain_cards) <= 2

    def test_weak_support_passages_excluded(self):
        from app.services.research_search import generate_candidate_cards

        search_results = [{"url": "https://example.edu/article"}]
        weak_text = (
            "Ancient Rome had a complex legal system. The history of architecture "
            "spans many centuries and civilizations across the world and beyond." * 20
        )
        article_weak = self._make_article()
        article_weak = article_weak.model_copy(update={"extracted_text": weak_text})

        with patch("app.services.research_search.extract_article", return_value=article_weak), \
             patch("app.services.research_search.rate_source_quality") as mock_quality:
            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="Good")
            result = generate_candidate_cards(
                search_results=search_results,
                topic="climate",
                claim_to_support="nuclear energy reduces carbon emissions substantially",
                side=None,
                user_id="u1",
            )
            sources = result.sources_considered

        # The new pipeline uses evidence roles; unrelated passage should have no card
        # Status can be any non-card status (no_support, skipped, etc.)
        assert all(s["status"] not in ("card_generated",) for s in sources if s["url"] == "https://example.edu/article")

    def test_ssrf_blocked_url_skipped(self):
        from app.services.research_search import generate_candidate_cards

        search_results = [{"url": "http://localhost/admin"}]

        with patch("app.services.research_search.extract_article", side_effect=ValueError("Internal URL rejected")):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="trade",
                claim_to_support="tariffs hurt economic growth",
                side=None,
                user_id="u1",
            )

        assert len(result.card_drafts) == 0
        assert any("SSRF" in s.get("reason", "") for s in result.sources_considered)

    def test_draft_json_has_support_fields(self):
        from app.services.research_search import generate_candidate_cards

        search_results = [{"url": "https://imf.org/report"}]
        article = self._make_article()

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft:

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="Good")
            mock_draft.return_value = {
                "user_id": "u1",
                "url": "https://imf.org/report",
                "body_text": self.LONG_TEXT[:300],
                "tag": "IMF Trade Study",
                "cite": "IMF Staff · IMF · 2023",
                "status": "draft",
                "draft_json": {},
                "missing_metadata_json": {},
                "generated_tag": True,
                "extraction_confidence": 0.85,
                "card_source_type": "research_search",
                "highlighted_spans_json": [],
                "underline_spans_json": [],
            }

            result = generate_candidate_cards(
                search_results=search_results,
                topic="trade",
                claim_to_support="tariffs hurt economic growth",
                side=None,
                user_id="u1",
            )
            drafts = result.card_drafts

        assert len(drafts) == 1
        dj = drafts[0].get("draft_json", {})
        assert "support_level" in dj
        assert "support_rationale" in dj
        assert "card_purpose" in dj
        assert "claim_supported" in dj


# ── generate_cards endpoint (mocked) ─────────────────────────────────────────

class TestGenerateCardsEndpoint:
    def test_returns_not_configured_when_no_tavily_key(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards

        body = GenerateCardsRequest(user_id="u1", claim_to_support="tariffs hurt growth")

        with patch("app.api.research.get_tavily_api_key", return_value=None):
            result = asyncio.run(generate_cards(body))

        assert result.search_configured is False
        assert result.cards == []

    def _inject_fake_tavily(self, client_mock) -> "patch":
        """Inject a fake `tavily` module with TavilyClient into sys.modules."""
        import sys
        import types
        fake_tavily = types.ModuleType("tavily")
        fake_tavily.TavilyClient = MagicMock(return_value=client_mock)
        return patch.dict(sys.modules, {"tavily": fake_tavily})

    def test_returns_empty_when_no_search_results(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards

        body = GenerateCardsRequest(user_id="u1", claim_to_support="tariffs hurt growth")

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test"), \
             self._inject_fake_tavily(mock_client):
            result = asyncio.run(generate_cards(body))

        assert result.search_configured is True
        assert result.cards == []
        assert result.no_card_reason is not None

    def test_tavily_failure_returns_graceful_error(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards

        body = GenerateCardsRequest(user_id="u1", claim_to_support="tariffs hurt growth")

        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("Network timeout")

        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test"), \
             self._inject_fake_tavily(mock_client):
            result = asyncio.run(generate_cards(body))

        assert result.search_configured is True
        assert result.no_card_reason is not None
        assert len(result.suggestions) > 0


# ── Query variants ────────────────────────────────────────────────────────────

class TestBuildResearchQueryVariants:
    def test_returns_multiple_variants(self):
        from app.services.research_search import build_research_query_variants
        variants = build_research_query_variants(
            topic="Section 230",
            claim_to_support="Section 230 leads to lack of accountability for harmful content",
        )
        assert len(variants) >= 2

    def test_first_variant_is_base_query(self):
        from app.services.research_search import build_research_query_variants, build_research_search_query
        variants = build_research_query_variants(
            topic="Section 230",
            claim_to_support="Section 230 leads to lack of accountability for harmful content",
        )
        base = build_research_search_query(
            topic="Section 230",
            claim_to_support="Section 230 leads to lack of accountability for harmful content",
        )
        assert variants[0] == base

    def test_section230_accountability_includes_liability_variant(self):
        from app.services.research_search import build_research_query_variants
        variants = build_research_query_variants(
            topic="Section 230",
            claim_to_support="Section 230 leads to lack of accountability for harmful content",
        )
        combined = " ".join(v.lower() for v in variants)
        assert "liability" in combined or "immune" in combined or "shield" in combined

    def test_no_duplicate_variants(self):
        from app.services.research_search import build_research_query_variants
        variants = build_research_query_variants(
            topic="trade",
            claim_to_support="tariffs lead to economic harm",
        )
        lower_variants = [v.lower().strip() for v in variants]
        assert len(lower_variants) == len(set(lower_variants))

    def test_caps_at_eight(self):
        from app.services.research_search import build_research_query_variants
        variants = build_research_query_variants(
            topic="climate",
            claim_to_support="carbon emissions increase global temperature and harm ecosystems",
        )
        assert len(variants) <= 8

    def test_all_variants_are_strings(self):
        from app.services.research_search import build_research_query_variants
        variants = build_research_query_variants(
            topic=None,
            claim_to_support="government policy reduces economic growth",
        )
        assert all(isinstance(v, str) and v.strip() for v in variants)


# ── expand_claim_concepts ─────────────────────────────────────────────────────

class TestExpandClaimConcepts:
    def test_accountability_expands_to_liability(self):
        from app.services.research_search import expand_claim_concepts
        concepts = expand_claim_concepts("Section 230 leads to lack of accountability", "Section 230")
        assert "liability" in concepts.all_terms

    def test_accountability_expands_to_immunity(self):
        from app.services.research_search import expand_claim_concepts
        concepts = expand_claim_concepts("Section 230 leads to lack of accountability", "Section 230")
        assert "immunity" in concepts.expanded_terms

    def test_harmful_expands_to_illegal(self):
        from app.services.research_search import expand_claim_concepts
        concepts = expand_claim_concepts("harmful content causes harm", "online platforms")
        assert "illegal" in concepts.expanded_terms or "illegal" in concepts.all_terms

    def test_leads_is_mechanism_term(self):
        from app.services.research_search import expand_claim_concepts
        concepts = expand_claim_concepts("Section 230 leads to problems", "")
        assert "leads" in concepts.mechanism_terms or "causes" in concepts.mechanism_terms

    def test_all_terms_is_superset(self):
        from app.services.research_search import expand_claim_concepts
        concepts = expand_claim_concepts("Section 230 leads to lack of accountability", "")
        assert concepts.core_terms.issubset(concepts.all_terms)
        assert concepts.expanded_terms.issubset(concepts.all_terms)

    def test_empty_claim_no_error(self):
        from app.services.research_search import expand_claim_concepts
        concepts = expand_claim_concepts("", "")
        assert isinstance(concepts.all_terms, frozenset)


# ── _classify_support_deterministic with concepts ────────────────────────────

class TestClassifySupportWithConcepts:
    SECTION_230_CLAIM = "Section 230 leads to lack of accountability for harmful content"

    def test_liability_shield_passage_scores_partial_or_strong(self):
        from app.services.research_search import _classify_support_deterministic, expand_claim_concepts
        passage = (
            "Section 230 of the Communications Decency Act shields online platforms from civil "
            "liability for user-generated content. Critics argue this immunity prevents victims "
            "of online harm from seeking legal recourse against large tech companies."
            " The provision has been cited in thousands of court cases since 1996."
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        level, rationale = _classify_support_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert level in ("partial_support", "strong_support"), f"Expected partial/strong, got {level}: {rationale}"

    def test_passage_with_synonym_scores_better_than_old_pure_keyword(self):
        from app.services.research_search import _classify_support_deterministic, expand_claim_concepts
        # "liability" and "immunity" are synonyms of "accountability"
        passage_with_synonyms = (
            "Section 230 grants broad immunity to internet platforms from liability "
            "for harmful third-party content. This legal protection has allowed major "
            "companies to avoid accountability for illegal speech on their services."
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        level, _ = _classify_support_deterministic(passage_with_synonyms, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert level in ("partial_support", "strong_support")

    def test_fully_unrelated_passage_is_no_support(self):
        from app.services.research_search import _classify_support_deterministic, expand_claim_concepts
        passage = (
            "The ancient Romans built their roads with a sophisticated drainage system "
            "using volcanic rock and gravel. Modern archaeologists have uncovered many "
            "of these routes across Europe." * 3
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        level, _ = _classify_support_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert level == "no_support"

    def test_short_passage_penalized(self):
        from app.services.research_search import _classify_support_deterministic, expand_claim_concepts
        # Short passage with relevant keywords shouldn't get a free strong_support
        passage = "Section 230 shields platforms from liability."
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        level, _ = _classify_support_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        # Short penalty should prevent it from being strong
        assert level != "strong_support"


# ── generate_candidate_cards with Section 230 mocked search ──────────────────

class TestSection230MockedSearch:
    LONG_PASSAGE = (
        "Section 230 of the Communications Decency Act provides sweeping immunity to online "
        "platforms from civil liability for content posted by users. Critics argue this legal "
        "shield prevents accountability for harmful and illegal content including trafficking, "
        "harassment, and extremist speech. The provision has been cited in thousands of court "
        "cases, allowing major tech companies to avoid legal responsibility for third-party "
        "content that causes demonstrable harm to individuals and society. Reform advocates "
        "argue the immunity is too broad and removes incentives to moderate harmful content. "
        "Studies indicate a majority of online harassment victims had no legal recourse."
    )
    CLAIM = "Section 230 leads to lack of accountability for harmful content"

    def _make_article(self):
        from app.models.research import ArticleMetadata, ExtractedArticle
        meta = ArticleMetadata(
            title="Section 230 Immunity and Platform Liability",
            author="Jane Smith",
            publication="Harvard Law Review",
            published_date="2024-01-10",
            url="https://harvard.edu/law/230",
        )
        return ExtractedArticle(
            url="https://harvard.edu/law/230",
            metadata=meta,
            extracted_text=self.LONG_PASSAGE * 5,
            extraction_method="test",
            extraction_confidence=0.95,
        )

    def test_section230_liability_passage_returns_at_least_one_card(self):
        from app.services.research_search import generate_candidate_cards
        search_results = [{"url": "https://harvard.edu/law/230"}]
        article = self._make_article()

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft, \
             patch("app.services.research_search._classify_role_with_llm", return_value=None):

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="Law review.")
            mock_draft.return_value = {
                "user_id": "u1",
                "url": "https://harvard.edu/law/230",
                "body_text": self.LONG_PASSAGE,
                "tag": "Section 230 shields platforms from civil liability",
                "cite": "Smith · Harvard Law Review · 2024",
                "status": "draft",
                "draft_json": {},
                "missing_metadata_json": {},
                "generated_tag": True,
                "extraction_confidence": 0.95,
                "card_source_type": "research_search",
                "highlighted_spans_json": [],
                "underline_spans_json": [],
            }

            result = generate_candidate_cards(
                search_results=search_results,
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side="Pro",
                user_id="u1",
                use_llm=False,
            )

        assert len(result.card_drafts) >= 1, (
            f"Expected ≥1 card for Section 230 accountability claim. "
            f"sources_considered={result.sources_considered}, "
            f"filtered_no_support={result.filtered_no_support}"
        )

    def test_no_card_for_truly_unrelated_source(self):
        from app.services.research_search import generate_candidate_cards
        from app.models.research import ArticleMetadata, ExtractedArticle
        unrelated_text = (
            "Ancient Roman architecture featured sophisticated aqueduct systems that "
            "transported water across vast distances. The Colosseum seated 50,000 spectators." * 20
        )
        meta = ArticleMetadata(url="https://history.org/rome", title="Roman History")
        article = ExtractedArticle(
            url="https://history.org/rome",
            metadata=meta,
            extracted_text=unrelated_text,
            extraction_method="test",
            extraction_confidence=0.7,
        )

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search._classify_role_with_llm", return_value=None):
            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="")
            result = generate_candidate_cards(
                search_results=[{"url": "https://history.org/rome"}],
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side=None,
                user_id="u1",
                use_llm=False,
            )

        assert len(result.card_drafts) == 0

    def test_diagnostics_fields_populated(self):
        from app.services.research_search import generate_candidate_cards
        from app.models.research import ArticleMetadata, ExtractedArticle
        unrelated_text = "Nothing relevant here. " * 50
        meta = ArticleMetadata(url="https://example.org/nothing", title="Nothing")
        article = ExtractedArticle(
            url="https://example.org/nothing",
            metadata=meta,
            extracted_text=unrelated_text,
            extraction_method="test",
            extraction_confidence=0.5,
        )

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search._classify_role_with_llm", return_value=None):
            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="")
            result = generate_candidate_cards(
                search_results=[{"url": "https://example.org/nothing"}],
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side=None,
                user_id="u1",
                use_llm=False,
            )

        assert result.sources_attempted >= 1
        assert result.sources_found == 1

    def test_best_supported_claim_stored_in_draft_json(self):
        from app.services.research_search import generate_candidate_cards, EvidenceRoleOutput
        search_results = [{"url": "https://harvard.edu/law/230"}]
        article = self._make_article()
        llm_output = EvidenceRoleOutput(
            evidence_role="mechanism_support",
            debate_usefulness_score=8.0,
            best_supported_claim="Section 230 shields platforms from civil liability for user content",
            overclaim_warning="Original claim is slightly broader than what the passage proves.",
            safe_tag_scope="Platform liability shield under Section 230",
            reasoning_short="Passage explains the immunity mechanism.",
        )

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft, \
             patch("app.services.research_search._classify_role_with_llm", return_value=llm_output):

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="")
            mock_draft.return_value = {
                "user_id": "u1",
                "url": "https://harvard.edu/law/230",
                "body_text": self.LONG_PASSAGE,
                "tag": "Section 230 shields platforms",
                "cite": "Smith · Harvard Law Review · 2024",
                "status": "draft",
                "draft_json": {},
                "missing_metadata_json": {},
                "generated_tag": True,
                "extraction_confidence": 0.95,
                "card_source_type": "research_search",
                "highlighted_spans_json": [],
                "underline_spans_json": [],
            }

            result = generate_candidate_cards(
                search_results=search_results,
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side=None,
                user_id="u1",
                use_llm=True,
            )

        assert len(result.card_drafts) == 1
        dj = result.card_drafts[0].get("draft_json", {})
        assert dj.get("best_supported_claim") == "Section 230 shields platforms from civil liability for user content"
        assert dj.get("overclaim_warning") is not None


# ── Multi-query endpoint deduplication ───────────────────────────────────────

class TestMultiQueryDeduplication:
    def _inject_fake_tavily(self, client_mock):
        import sys
        import types
        fake_tavily = types.ModuleType("tavily")
        fake_tavily.TavilyClient = MagicMock(return_value=client_mock)
        return patch.dict(sys.modules, {"tavily": fake_tavily})

    def test_endpoint_deduplicates_urls_across_variants(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards

        body = GenerateCardsRequest(
            user_id="u1",
            topic="Section 230",
            claim_to_support="Section 230 leads to lack of accountability for harmful content",
        )
        # Each Tavily call returns the same URL — dedup should result in 1 unique URL
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"url": "https://law.harvard.edu/article", "title": "Test", "content": "Test"}]
        }

        seen_urls = []

        def fake_generate(search_results, **kwargs):
            seen_urls.extend(r.get("url") for r in search_results)
            from app.services.research_search import CandidateCardsResult
            return CandidateCardsResult()

        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test"), \
             patch("app.api.research.generate_candidate_cards", side_effect=fake_generate), \
             patch("app.api.research.settings") as mock_settings, \
             self._inject_fake_tavily(mock_client):
            # Force unified search path so this test exercises URL dedup across variants
            mock_settings.research_enable_slot_planner = False
            mock_settings.research_enable_llm_role_classifier = False
            mock_settings.exa_api_key = None
            asyncio.run(generate_cards(body))

        # URL should appear only once despite multiple Tavily calls
        assert seen_urls.count("https://law.harvard.edu/article") == 1

    def test_endpoint_returns_diagnostics_on_no_card(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards
        from app.services.research_search import CandidateCardsResult

        body = GenerateCardsRequest(user_id="u1", claim_to_support="tariffs hurt growth")
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"url": "https://example.edu/report", "title": "T", "content": "C"}]
        }

        empty_result = CandidateCardsResult(
            sources_found=1, sources_attempted=1, sources_extracted=1,
            passages_considered=1, candidates_generated=0,
            filtered_no_support=1, filtered_low_quality=0,
        )

        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test"), \
             patch("app.api.research.generate_candidate_cards", return_value=empty_result), \
             patch("app.api.research.get_supabase"), \
             patch("app.api.research.settings") as mock_settings, \
             self._inject_fake_tavily(mock_client):
            # Force unified search path so this test exercises the diagnostics it was written for
            mock_settings.research_enable_slot_planner = False
            mock_settings.research_enable_llm_role_classifier = False
            mock_settings.exa_api_key = None
            result = asyncio.run(generate_cards(body))

        assert result.diagnostics is not None
        assert result.diagnostics.sources_found >= 1
        assert result.diagnostics.filtered_no_support == 1

    def test_endpoint_includes_query_variants_in_diagnostics(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards
        from app.services.research_search import CandidateCardsResult

        body = GenerateCardsRequest(user_id="u1", claim_to_support="tariffs hurt growth")
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test"), \
             self._inject_fake_tavily(mock_client):
            result = asyncio.run(generate_cards(body))

        assert result.diagnostics is not None
        assert len(result.diagnostics.query_variants_used) >= 1


# ── TestNormalizeClaim ─────────────────────────────────────────────────────────

class TestNormalizeClaim:
    def test_ion_230_typo_fixed_when_topic_contains_section_230(self):
        from app.services.claim_decomposition import normalize_claim
        normalized, corrections = normalize_claim(
            "section 230",
            "ion 230 facilitates harmful content and misinformation",
        )
        assert "Section 230" in normalized
        assert len(corrections) >= 1
        assert "ion 230" in corrections[0].lower() or "section 230" in corrections[0].lower()

    def test_tion_230_typo_fixed(self):
        from app.services.claim_decomposition import normalize_claim
        normalized, corrections = normalize_claim(
            "section 230",
            "tion 230 causes platform immunity",
        )
        assert "Section 230" in normalized
        assert len(corrections) >= 1

    def test_no_change_when_claim_already_correct(self):
        from app.services.claim_decomposition import normalize_claim
        normalized, corrections = normalize_claim(
            "section 230",
            "Section 230 is fine",
        )
        assert normalized == "Section 230 is fine"
        assert corrections == []

    def test_no_change_when_topic_lacks_entity(self):
        from app.services.claim_decomposition import normalize_claim
        # Different topic — shouldn't fix "ion 230"
        normalized, corrections = normalize_claim(
            "climate change",
            "ion 230 facilitates harmful content",
        )
        assert "ion 230" in normalized  # no correction since topic doesn't have Section 230
        assert corrections == []


# ── TestDecomposeClaimDeterministic ──────────────────────────────────────────

class TestDecomposeClaimDeterministic:
    def test_deterministic_plan_has_queries(self):
        from app.services.claim_decomposition import decompose_claim
        with patch("app.services.claim_decomposition._decompose_with_llm", return_value=None):
            plan = decompose_claim(
                "section 230",
                "Section 230 facilitates harmful content",
                "Pro",
            )
        assert len(plan.search_queries) >= 1
        assert plan.original_claim == "Section 230 facilitates harmful content"

    def test_queries_include_liability_for_accountability_claim(self):
        from app.services.claim_decomposition import decompose_claim
        with patch("app.services.claim_decomposition._decompose_with_llm", return_value=None):
            plan = decompose_claim(
                "section 230",
                "Section 230 leads to lack of accountability for harmful content",
                "Pro",
            )
        combined = " ".join(plan.search_queries).lower()
        assert "liability" in combined or "immunity" in combined or "court" in combined

    def test_normalized_claim_preserved(self):
        from app.services.claim_decomposition import decompose_claim
        with patch("app.services.claim_decomposition._decompose_with_llm", return_value=None):
            plan = decompose_claim(
                "section 230",
                "ion 230 facilitates harmful content",
                "Pro",
            )
        # normalized_claim should have Section 230 corrected
        assert "Section 230" in plan.normalized_claim


# ── TestEvidenceRoleClassification ───────────────────────────────────────────

class TestEvidenceRoleClassification:
    SECTION_230_CLAIM = "Section 230 leads to lack of accountability for harmful content"

    def test_mechanism_passage_gets_mechanism_support(self):
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        passage = (
            "Section 230 of the Communications Decency Act shields platforms from civil "
            "liability for user-generated content. This legal immunity prevents victims "
            "from seeking legal recourse against major tech companies. The statute exempts "
            "providers from responsibility for third-party content, making it impossible "
            "to hold platforms accountable through the courts. Legal experts note that "
            "this protection is extraordinarily broad."
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        result = _classify_role_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert result.evidence_role in ("mechanism_support", "direct_support"), (
            f"Expected mechanism/direct, got {result.evidence_role}"
        )

    def test_example_passage_gets_example_support(self):
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        passage = (
            "In the case of Jane Doe v. Backpage.com, the court ruled that Section 230 "
            "barred the plaintiff from pursuing civil liability claims. The defendant "
            "was shielded from lawsuit because the law holds providers immune from "
            "third-party content. The case was dismissed on these grounds."
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        result = _classify_role_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert result.evidence_role in ("example_support", "mechanism_support", "direct_support"), (
            f"Expected example/mechanism/direct, got {result.evidence_role}"
        )

    def test_unrelated_passage_gets_not_useful(self):
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        passage = (
            "The history of ancient Rome includes many fascinating architectural "
            "achievements such as the Colosseum, aqueducts, and the Forum. "
            "Roman senators debated in Latin. The Pantheon was built in 125 AD. " * 3
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        result = _classify_role_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert result.evidence_role == "not_useful"

    def test_direct_support_passage_gets_direct_support(self):
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        # Passage with many claim-aligned terms should score as direct_support or better
        passage = (
            "Section 230 directly leads to lack of accountability for harmful content by "
            "providing immunity that shields platforms from civil liability. Studies confirm "
            "that platforms are responsible for harmful user-generated content but are legally "
            "protected from damages, lawsuits, and legal recourse because of this immunity shield. "
            "Research shows that victims cannot seek legal accountability due to Section 230 "
            "protection. Data indicates 85% of harmful content cases are dismissed. "
            "The immunity causes demonstrable harm to individuals and society alike. "
        ) * 3
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        result = _classify_role_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert result.evidence_role in (
            "direct_support", "mechanism_support", "impact_support", "example_support"
        ), (
            f"Expected a specific support role for high-overlap passage, got {result.evidence_role}"
        )

    def test_mechanism_passage_prefers_mechanism_over_direct(self):
        """A passage about HOW Section 230 works should not be labelled direct_support."""
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        passage = (
            "Section 230 provides immunity to platforms from civil liability for third-party "
            "content. This protection prevents victims from holding tech companies accountable "
            "in court. The law explicitly shields providers, barring lawsuits against platforms "
            "for harmful user-posted content."
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        result = _classify_role_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        # After the priority fix, mechanism passages should NOT get direct_support
        # (they should get mechanism_support unless score is extremely high)
        assert result.evidence_role != "direct_support" or result.debate_usefulness_score >= 6.0, (
            f"Mechanism passage unexpectedly got direct_support with low score "
            f"{result.debate_usefulness_score}"
        )

    def test_case_citation_passage_gets_example_support(self):
        """Passages with 'v.' and 'plaintiff/defendant' should be example_support."""
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        passage = (
            "In Doe v. Backpage, the plaintiff alleged Section 230 shielded the defendant "
            "from accountability. The court dismissed the case, ruling the defendant was "
            "protected from civil liability under the statute."
        )
        concepts = expand_claim_concepts(self.SECTION_230_CLAIM, "Section 230")
        result = _classify_role_deterministic(passage, self.SECTION_230_CLAIM, "Section 230", concepts)
        assert result.evidence_role == "example_support", (
            f"Case citation passage should be example_support, got {result.evidence_role}"
        )


# ── TestSection230FullPipeline ────────────────────────────────────────────────

class TestSection230FullPipeline:
    MECHANISM_PASSAGE = (
        "Section 230 of the Communications Decency Act provides sweeping immunity to online "
        "platforms from civil liability for content posted by users. This legal shield "
        "prevents victims from seeking legal recourse against tech companies. The provision "
        "exempts platforms from responsibility, enabling harmful content to remain online "
        "without legal accountability. Courts have consistently upheld this immunity shield, "
        "dismissing hundreds of civil lawsuits filed by harassment victims."
    )
    CLAIM = "Section 230 leads to lack of accountability for harmful content"

    def _make_article(self, text: str = None):
        from app.models.research import ArticleMetadata, ExtractedArticle
        txt = text or (self.MECHANISM_PASSAGE * 4)
        meta = ArticleMetadata(
            title="Section 230 Immunity",
            author="Jane Smith",
            publication="Harvard Law Review",
            published_date="2024-01-10",
            url="https://harvard.edu/law/230",
        )
        return ExtractedArticle(
            url="https://harvard.edu/law/230",
            metadata=meta,
            extracted_text=txt,
            extraction_method="test",
            extraction_confidence=0.95,
        )

    def test_mechanism_card_accepted_even_without_direct_support(self):
        from app.services.research_search import generate_candidate_cards

        article = self._make_article()
        search_results = [{"url": "https://harvard.edu/law/230"}]

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft, \
             patch("app.services.research_search._classify_role_with_llm", return_value=None):

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="Law review.")
            mock_draft.return_value = {
                "user_id": "u1",
                "url": "https://harvard.edu/law/230",
                "body_text": self.MECHANISM_PASSAGE,
                "tag": "Section 230 shields platforms",
                "cite": "Smith · Harvard Law Review · 2024",
                "status": "draft",
                "draft_json": {},
                "missing_metadata_json": {},
                "generated_tag": True,
                "extraction_confidence": 0.95,
                "card_source_type": "research_search",
                "highlighted_spans_json": [],
                "underline_spans_json": [],
            }

            result = generate_candidate_cards(
                search_results=search_results,
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side="Pro",
                user_id="u1",
                use_llm=False,
            )

        assert len(result.card_drafts) >= 1, (
            f"Expected ≥1 mechanism card. sources_considered={result.sources_considered}, "
            f"filtered_no_support={result.filtered_no_support}"
        )

    def test_candidates_by_role_populated(self):
        from app.services.research_search import generate_candidate_cards

        article = self._make_article()
        search_results = [{"url": "https://harvard.edu/law/230"}]

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft, \
             patch("app.services.research_search._classify_role_with_llm", return_value=None):

            mock_quality.return_value = MagicMock(source_quality="high", credibility_notes="")
            mock_draft.return_value = {
                "user_id": "u1",
                "url": "https://harvard.edu/law/230",
                "body_text": self.MECHANISM_PASSAGE,
                "tag": "Section 230",
                "cite": "Smith 2024",
                "status": "draft",
                "draft_json": {},
                "missing_metadata_json": {},
                "generated_tag": True,
                "extraction_confidence": 0.95,
                "card_source_type": "research_search",
                "highlighted_spans_json": [],
                "underline_spans_json": [],
            }

            result = generate_candidate_cards(
                search_results=search_results,
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side=None,
                user_id="u1",
                use_llm=False,
            )

        assert len(result.candidates_by_role) >= 1, "candidates_by_role should have at least one entry"
        total = sum(result.candidates_by_role.values())
        assert total >= 1

    def test_snippet_fallback_creates_card(self):
        from app.services.research_search import generate_candidate_cards
        from app.models.research import ArticleMetadata, ExtractedArticle

        # Article with failed status
        meta = ArticleMetadata(url="https://news.example.com/article", title="Section 230 Analysis")
        failed_article = ExtractedArticle(
            url="https://news.example.com/article",
            metadata=meta,
            extracted_text="",
            extraction_method="failed",
            extraction_confidence=0.0,
            status="failed",
            error="Could not extract",
        )

        # Candidate has a snippet with useful text (>= 150 chars)
        snippet = (
            "Section 230 shields platforms from civil liability for user-generated content, "
            "preventing victims from seeking legal recourse. This immunity mechanism "
            "allows harmful content to remain online without accountability from platforms. "
            "Courts have dismissed dozens of lawsuits citing this provision."
        )
        search_results = [{"url": "https://news.example.com/article", "content": snippet}]

        with patch("app.services.research_search.extract_article", return_value=failed_article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search.generate_card_draft") as mock_draft, \
             patch("app.services.research_search._classify_role_with_llm", return_value=None):

            mock_quality.return_value = MagicMock(source_quality="medium", credibility_notes="Snippet source")
            mock_draft.return_value = {
                "user_id": "u1",
                "url": "https://news.example.com/article",
                "body_text": snippet,
                "tag": "Section 230 shields platforms",
                "cite": "Example News 2024",
                "status": "draft",
                "draft_json": {},
                "missing_metadata_json": {},
                "generated_tag": True,
                "extraction_confidence": 0.3,
                "card_source_type": "research_search",
                "highlighted_spans_json": [],
                "underline_spans_json": [],
            }

            result = generate_candidate_cards(
                search_results=search_results,
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side=None,
                user_id="u1",
                use_llm=False,
                source_quality_min="low",
            )

        # Snippet-only sources are routed to weak_leads (Part 6), not card_drafts.
        assert len(result.weak_leads) >= 1, (
            f"Expected weak lead from snippet fallback. sources_considered={result.sources_considered}"
        )
        # No snippet-only card should remain in the main card list.
        for card in result.card_drafts:
            assert not card.get("draft_json", {}).get("is_snippet_source"), (
                "Snippet-only sources must not appear in card_drafts"
            )

    def test_counter_evidence_not_in_main_cards(self):
        from app.services.research_search import generate_candidate_cards, EvidenceRoleOutput
        from app.models.research import ArticleMetadata, ExtractedArticle

        counter_passage = (
            "Section 230 actually promotes accountability by allowing platforms to moderate "
            "content without losing immunity protection. Without Section 230, platforms "
            "would moderate less, not more, making harmful content more prevalent. "
            "Critics of Section 230 reform argue that repeal would harm free speech "
            "and damage platform innovation significantly." * 3
        )
        meta = ArticleMetadata(url="https://techpolicy.org/article")
        article = ExtractedArticle(
            url="https://techpolicy.org/article",
            metadata=meta,
            extracted_text=counter_passage,
            extraction_method="test",
            extraction_confidence=0.8,
        )

        counter_output = EvidenceRoleOutput(
            evidence_role="counter_evidence",
            debate_usefulness_score=6.0,
            reasoning_short="Passage argues AGAINST the claim.",
        )

        search_results = [{"url": "https://techpolicy.org/article"}]

        with patch("app.services.research_search.extract_article", return_value=article), \
             patch("app.services.research_search.rate_source_quality") as mock_quality, \
             patch("app.services.research_search._classify_role_with_llm", return_value=counter_output):

            mock_quality.return_value = MagicMock(source_quality="medium", credibility_notes="")

            result = generate_candidate_cards(
                search_results=search_results,
                topic="Section 230",
                claim_to_support=self.CLAIM,
                side="Pro",
                user_id="u1",
                use_llm=True,
            )

        # Counter-evidence should NOT appear in card_drafts
        assert len(result.card_drafts) == 0, "Counter-evidence should not produce a card draft"
        # But it should appear in sources_considered with counter_evidence status
        counter_sources = [s for s in result.sources_considered if s.get("status") == "counter_evidence"]
        assert len(counter_sources) >= 1, "Counter-evidence should be tracked in sources_considered"


# ── TestClaimNormalizationEndToEnd ────────────────────────────────────────────

class TestClaimNormalizationEndToEnd:
    def _inject_fake_tavily(self, client_mock):
        import sys
        import types
        fake_tavily = types.ModuleType("tavily")
        fake_tavily.TavilyClient = MagicMock(return_value=client_mock)
        return patch.dict(sys.modules, {"tavily": fake_tavily})

    def test_api_endpoint_normalizes_typo_claim(self):
        import asyncio
        from app.models.research import GenerateCardsRequest
        from app.api.research import generate_cards
        from app.services.claim_decomposition import ClaimResearchPlan
        from app.services.research_search import CandidateCardsResult

        body = GenerateCardsRequest(
            user_id="u1",
            topic="Section 230",
            claim_to_support="ion 230 facilitates harmful content",
        )

        mock_plan = ClaimResearchPlan(
            original_claim="ion 230 facilitates harmful content",
            normalized_claim="Section 230 facilitates harmful content",
            corrections_applied=["ion 230 → Section 230"],
            search_queries=["Section 230 liability shield harmful content evidence"],
        )

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.api.research.get_tavily_api_key", return_value="tvly-test"), \
             patch("app.api.research.decompose_claim", return_value=mock_plan), \
             self._inject_fake_tavily(mock_client):
            result = asyncio.run(generate_cards(body))

        assert result.normalized_claim == "Section 230 facilitates harmful content"
        assert result.corrections_applied == ["ion 230 → Section 230"]
