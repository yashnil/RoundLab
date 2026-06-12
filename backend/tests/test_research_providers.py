"""Tests for multi-provider robustness layer: URL canonicalization, Exa provider,
Firecrawl extraction fallback, heuristic/Cohere reranking, and boilerplate detection.

All tests use mocked httpx.post/httpx.get — NO live HTTP calls.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock


# ── Test helpers ──────────────────────────────────────────────────────────────

def _inject_fake_tavily(monkeypatch) -> None:
    """Inject a no-op Tavily module so imports work cleanly."""
    fake_tavily = types.ModuleType("tavily")
    fake_client = types.ModuleType("tavily.tavily_search_api_wrapper")
    fake_tavily.TavilyClient = MagicMock()
    fake_client.TavilySearchAPIWrapper = MagicMock()
    fake_tavily.tavily_search_api_wrapper = fake_client
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)
    monkeypatch.setitem(sys.modules, "tavily.tavily_search_api_wrapper", fake_client)


# ── Task 1: URL Canonicalization ──────────────────────────────────────────────

class TestUrlCanonicalization:
    def _canon(self, url: str) -> str:
        from app.services.research_search import canonicalize_url
        return canonicalize_url(url)

    def test_utm_source_removed(self):
        result = self._canon("https://example.com/article?utm_source=google&id=123")
        assert "utm_source" not in result
        assert "id=123" in result

    def test_utm_campaign_removed(self):
        result = self._canon("https://example.com/page?utm_campaign=spring&page=2")
        assert "utm_campaign" not in result
        assert "page=2" in result

    def test_fragment_removed(self):
        result = self._canon("https://example.com/article#section-3")
        assert "#" not in result
        assert "section-3" not in result

    def test_meaningful_query_params_preserved(self):
        result = self._canon("https://example.com/search?q=section+230&category=law")
        assert "q=section+230" in result or "q=section%20230" in result
        assert "category=law" in result

    def test_all_tracking_params_removed(self):
        tracking = "utm_source=a&utm_medium=b&utm_campaign=c&utm_content=d&utm_term=e&gclid=x&fbclid=y"
        result = self._canon(f"https://example.com/page?{tracking}&keep=1")
        assert "utm_" not in result
        assert "gclid" not in result
        assert "fbclid" not in result
        assert "keep=1" in result

    def test_deduplication_of_equivalent_urls(self):
        url1 = "https://EXAMPLE.COM/article?utm_source=newsletter"
        url2 = "https://example.com/article"
        from app.services.research_search import canonicalize_url
        assert canonicalize_url(url1) == canonicalize_url(url2)

    def test_scheme_lowercased(self):
        result = self._canon("HTTPS://Example.COM/path")
        assert result.startswith("https://example.com/")

    def test_ref_param_removed(self):
        result = self._canon("https://example.com/article?ref=twitter&id=5")
        assert "ref=twitter" not in result
        assert "id=5" in result

    def test_msclkid_removed(self):
        result = self._canon("https://example.com/page?msclkid=abc123&lang=en")
        assert "msclkid" not in result
        assert "lang=en" in result

    def test_invalid_url_returns_original(self):
        bad = "not a url at all!!!"
        from app.services.research_search import canonicalize_url
        # Should not raise; returns something
        result = canonicalize_url(bad)
        assert isinstance(result, str)


# ── Task 2: Exa Provider ──────────────────────────────────────────────────────

class TestExaProvider:
    def test_skipped_when_no_exa_key(self, monkeypatch):
        """Exa _search_exa should return empty list if called with empty key,
        but more importantly the api/research.py should not call it at all."""
        from app.services.research_search import _search_exa
        # With a blank API key, should attempt then get 401 — but we can just mock httpx
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = Exception("Should not be called in normal flow")
            # Directly calling with empty key — it will try and fail but not crash
            results = _search_exa(["test query"], api_key="test_key_placeholder", max_results_per_query=2)
            # The call was made (1 query); mock raised, so results should be empty
            assert results == []

    def test_called_when_key_exists_and_returns_tavily_compatible(self, monkeypatch):
        """When Exa returns results, they should be Tavily-compatible dicts."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import _search_exa

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://law.cornell.edu/section-230",
                    "title": "Section 230 Overview",
                    "text": "Section 230 grants platforms broad immunity from civil liability " * 10,
                    "highlights": ["Section 230 grants platforms immunity."],
                    "score": 0.9,
                    "publishedDate": "2024-01-15",
                }
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            results = _search_exa(["section 230 immunity"], api_key="fake_key")

        assert len(results) == 1
        r = results[0]
        assert r["url"] == "https://law.cornell.edu/section-230"
        assert r["title"] == "Section 230 Overview"
        assert r["_provider"] == "exa"
        assert "content" in r
        assert "score" in r

    def test_failures_dont_crash_whole_search(self, monkeypatch):
        """Exa failures should be caught and return empty list, not raise."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import _search_exa

        with patch("httpx.post", side_effect=Exception("Network error")):
            results = _search_exa(["query1", "query2"], api_key="fake_key")
        assert results == []

    def test_returned_results_are_tavily_compatible_dicts(self):
        """Each Exa result must have url, title, content, score, _provider keys."""
        from app.services.research_search import _search_exa

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.edu/paper",
                    "title": "Test Paper",
                    "text": "Some long text about policy and law " * 15,
                    "highlights": ["Policy insight here."],
                    "score": 0.8,
                }
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            results = _search_exa(["test query"], api_key="fake_key")

        assert len(results) >= 1
        for r in results:
            assert "url" in r
            assert "content" in r
            assert "score" in r
            assert r.get("_provider") == "exa"

    def test_provider_raw_content_in_returned_dict(self):
        """When Exa returns text >= 200 chars, it should appear as raw_content."""
        from app.services.research_search import _search_exa

        long_text = "This is useful debate evidence about Section 230 and platform liability. " * 10

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.gov/report",
                    "title": "Report",
                    "text": long_text,
                    "highlights": [],
                    "score": 0.85,
                }
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            results = _search_exa(["test"], api_key="key")

        assert len(results) == 1
        assert results[0].get("raw_content") == long_text

    def test_deduplication_across_queries(self):
        """Same URL from multiple queries should only appear once."""
        from app.services.research_search import _search_exa

        dup_result = {
            "url": "https://example.com/article?utm_source=google",
            "title": "Article",
            "text": "Some relevant text about policy " * 10,
            "highlights": ["Policy text."],
            "score": 0.7,
        }

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": [dup_result]}

        with patch("httpx.post", return_value=mock_response):
            results = _search_exa(["query1", "query2"], api_key="key", max_results_per_query=3)

        # The same canonical URL from 2 queries should be deduplicated
        urls = [r["url"] for r in results]
        assert len(urls) == len(set([r["url"] for r in results]))


# ── Task 3: Firecrawl Extraction ──────────────────────────────────────────────

class TestFirecrawlExtraction:
    def test_skipped_when_no_firecrawl_key(self, monkeypatch):
        """_extract_with_firecrawl returns None gracefully on any exception."""
        # This tests that if key is wrong/missing the function returns None
        with patch("httpx.post", side_effect=Exception("401 Unauthorized")):
            from app.services.research_search import _extract_with_firecrawl
            result = _extract_with_firecrawl("https://example.com", api_key="bad_key")
        assert result is None

    def test_called_when_key_exists_and_trafilatura_failed(self, monkeypatch):
        """Firecrawl should be called when extraction fails and key is available."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import _extract_with_firecrawl

        good_text = "Section 230 immunity protects platforms from civil liability " * 10

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "markdown": good_text,
            }
        }

        with patch("httpx.post", return_value=mock_response):
            result = _extract_with_firecrawl("https://example.com/article", api_key="test_fc_key")

        assert result is not None
        assert len(result) >= 200

    def test_short_extraction_returns_none(self):
        """If Firecrawl returns < 200 chars, return None."""
        from app.services.research_search import _extract_with_firecrawl

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {"markdown": "Too short."}
        }

        with patch("httpx.post", return_value=mock_response):
            result = _extract_with_firecrawl("https://example.com", api_key="key")

        assert result is None

    def test_boilerplate_text_rejected_by_looks_like_boilerplate(self):
        """_looks_like_boilerplate should catch nav/menu text."""
        from app.services.research_search import _looks_like_boilerplate

        nav_text = "\n".join([
            "Menu", "Sign in", "Log in", "Home", "About",
            "Subscribe", "Cookie policy", "Navigation", "Search",
            "Login", "Contact"
        ])
        assert _looks_like_boilerplate(nav_text) is True

    def test_legal_text_not_boilerplate(self):
        """Substantive legal text should not be flagged as boilerplate."""
        from app.services.research_search import _looks_like_boilerplate

        legal_text = (
            "Section 230 of the Communications Decency Act provides that no provider or user "
            "of an interactive computer service shall be treated as the publisher or speaker "
            "of any information provided by another information content provider. This provision "
            "has been interpreted by courts to provide broad immunity from civil liability for "
            "platforms hosting user-generated content, effectively shielding companies like "
            "Facebook and YouTube from lawsuits related to content posted by their users."
        )
        assert _looks_like_boilerplate(legal_text) is False

    def test_empty_text_is_boilerplate(self):
        from app.services.research_search import _looks_like_boilerplate
        assert _looks_like_boilerplate("") is True
        assert _looks_like_boilerplate("   \n  \n  ") is True


# ── Task 4: Boilerplate Detection ─────────────────────────────────────────────

class TestBoilerplateDetection:
    def _bp(self, text: str) -> bool:
        from app.services.research_search import _looks_like_boilerplate
        return _looks_like_boilerplate(text)

    def test_navigation_menu_text_is_boilerplate(self):
        nav = "\n".join(["Home", "About", "Contact", "Sign in", "Menu", "Products", "Blog", "FAQ"])
        assert self._bp(nav) is True

    def test_long_legal_passage_is_not_boilerplate(self):
        passage = (
            "The Communications Decency Act of 1996 established the foundational framework "
            "for internet platform liability in the United States. Under Section 230, platforms "
            "are granted broad immunity from civil liability for content created by third parties. "
            "This immunity has been consistently upheld by federal courts and has allowed the "
            "growth of user-generated content platforms. Critics argue that this immunity is "
            "overly broad and shields platforms from accountability for algorithmic amplification."
        )
        assert self._bp(passage) is False

    def test_mostly_short_lines_detected_as_boilerplate(self):
        short_lines = "\n".join(["OK", "Done", "Back", "Next", "Skip", "Yes", "No", "OK", "Done", "Back", "Search"])
        assert self._bp(short_lines) is True

    def test_mixed_content_not_boilerplate(self):
        mixed = (
            "Section 230 grants immunity from civil liability to internet platforms for "
            "user-generated content. Courts have repeatedly held that platforms are not "
            "publishers under this statute.\nHome\nAbout"
        )
        # Only 2 nav-ish short lines vs long substantive lines — should not be boilerplate
        assert self._bp(mixed) is False

    def test_subscribe_heavy_text_is_boilerplate(self):
        text = "\n".join([
            "Subscribe to our newsletter",
            "Sign in to continue reading",
            "Log in to access full content",
            "Cookie preferences",
            "Subscribe now",
            "Menu",
        ])
        assert self._bp(text) is True


# ── Task 5: Heuristic Reranking ───────────────────────────────────────────────

class TestHeuristicReranking:
    def _make_concepts(self, claim: str, topic: str = "section 230"):
        from app.services.research_search import expand_claim_concepts
        return expand_claim_concepts(claim, topic)

    def test_legal_mechanism_text_scores_higher_than_roman_history(self):
        from app.services.research_search import _rerank_chunks_heuristic, expand_claim_concepts

        claim = "Section 230 shields platforms from civil liability"
        concepts = expand_claim_concepts(claim, "section 230")

        legal_chunk = (
            "Section 230 of the Communications Decency Act grants platforms immunity from civil "
            "liability for user-generated content. Courts have repeatedly held that platforms are "
            "not liable as publishers under this statute. The immunity provision has been invoked "
            "in hundreds of lawsuits involving harmful content, defamation, and trafficking. "
            "Legal scholars argue this broad shield enables platforms to escape accountability."
        )
        history_chunk = (
            "Julius Caesar was a Roman general and statesman who played a critical role in "
            "the transformation of the Roman Republic into the Roman Empire. He was born in "
            "100 BC and assassinated on the Ides of March in 44 BC. His conquest of Gaul "
            "brought him fame and wealth. The Senate opposed his growing power."
        )

        reranked = _rerank_chunks_heuristic(
            [history_chunk, legal_chunk], concepts, source_quality_score=7.0, max_chunks=2
        )
        # Legal chunk should be ranked first
        assert reranked[0] == legal_chunk, "Legal mechanism text should rank higher than history text"

    def test_snippets_with_concept_overlap_score_higher(self):
        from app.services.research_search import _rerank_chunks_heuristic, expand_claim_concepts

        claim = "Section 230 reduces accountability for platform harmful content"
        concepts = expand_claim_concepts(claim, "section 230")

        relevant = (
            "Internet platforms have used Section 230 immunity to shield themselves from "
            "accountability for harmful content including misinformation and trafficking. "
            "Studies show that reducing Section 230 protections could lead to more responsible "
            "content moderation by platforms. Legal scholars argue that liability would increase "
            "platform accountability for the harms their algorithms cause."
        )
        irrelevant = (
            "The weather forecast for tomorrow shows sunny skies with temperatures reaching "
            "75 degrees. Meteorologists predict low humidity and light winds from the northwest. "
            "Perfect conditions for outdoor activities at the local park."
        )

        reranked = _rerank_chunks_heuristic(
            [irrelevant, relevant], concepts, source_quality_score=6.0, max_chunks=2
        )
        assert reranked[0] == relevant, "Concept-overlapping chunk should rank first"

    def test_boilerplate_gets_penalty(self):
        from app.services.research_search import _rerank_chunks_heuristic, expand_claim_concepts

        claim = "Section 230 reduces platform accountability"
        concepts = expand_claim_concepts(claim, "section 230")

        nav_boilerplate = "\n".join(["Home", "Sign in", "Menu", "Subscribe", "Log in", "Cookie"])
        substance = (
            "Section 230 immunity provisions have been applied by courts to shield platforms "
            "from accountability. Research shows platforms avoid liability through this statute."
        )

        reranked = _rerank_chunks_heuristic(
            [nav_boilerplate, substance], concepts, source_quality_score=5.0, max_chunks=2
        )
        assert reranked[0] == substance, "Substance should rank above boilerplate"

    def test_max_chunks_respected(self):
        from app.services.research_search import _rerank_chunks_heuristic, expand_claim_concepts

        concepts = expand_claim_concepts("Section 230 reduces accountability", "section 230")
        chunks = [f"Chunk {i}: Section 230 liability immunity platform content" for i in range(20)]

        reranked = _rerank_chunks_heuristic(chunks, concepts, source_quality_score=5.0, max_chunks=5)
        assert len(reranked) <= 5


# ── Task 6: Cohere Reranking ──────────────────────────────────────────────────

class TestCohereReranking:
    def test_skipped_when_no_key_returns_none(self):
        """_rerank_chunks_cohere should return None gracefully on failure."""
        with patch("httpx.post", side_effect=Exception("401 Unauthorized")):
            from app.services.research_search import _rerank_chunks_cohere
            result = _rerank_chunks_cohere(
                ["chunk 1", "chunk 2"],
                query="test query",
                api_key="bad_key",
            )
        assert result is None

    def test_returns_ordered_chunks_when_mocked(self):
        """When Cohere returns results, ordered chunks should be returned."""
        from app.services.research_search import _rerank_chunks_cohere

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"document": {"text": "Most relevant chunk about liability"}, "relevance_score": 0.95},
                {"document": {"text": "Second relevant chunk about immunity"}, "relevance_score": 0.75},
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            result = _rerank_chunks_cohere(
                ["Second relevant chunk about immunity", "Most relevant chunk about liability"],
                query="Section 230 platform liability",
                api_key="test_cohere_key",
            )

        assert result is not None
        assert len(result) == 2
        assert result[0] == "Most relevant chunk about liability"

    def test_falls_back_gracefully_on_failure(self):
        """Any Cohere failure returns None, not an exception."""
        from app.services.research_search import _rerank_chunks_cohere

        with patch("httpx.post", side_effect=ConnectionError("Cohere unreachable")):
            result = _rerank_chunks_cohere(
                ["chunk1", "chunk2"],
                query="test",
                api_key="key",
            )
        assert result is None

    def test_returns_none_on_empty_results(self):
        """Empty Cohere results should return None, triggering heuristic fallback."""
        from app.services.research_search import _rerank_chunks_cohere

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}

        with patch("httpx.post", return_value=mock_response):
            result = _rerank_chunks_cohere(["chunk1"], query="test", api_key="key")

        assert result is None


# ── Integration: graceful degradation ─────────────────────────────────────────

class TestGracefulDegradation:
    def test_generate_candidate_cards_uses_snippet_when_extraction_fails(self, monkeypatch):
        """When both trafilatura and Firecrawl fail, snippet fallback should be used."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards

        long_snippet = (
            "Section 230 of the Communications Decency Act grants platforms broad immunity "
            "from civil liability for third-party content. Courts have consistently applied "
            "this provision to dismiss lawsuits over user-generated harmful content, including "
            "defamation and sex trafficking claims. The statute has been invoked in hundreds "
            "of cases nationwide with platforms winning the majority."
        )
        search_results = [
            {
                "url": "https://law.cornell.edu/uscode/text/47/230",
                "content": long_snippet,
                "title": "47 U.S. Code § 230",
                "score": 0.9,
                "_provider": "tavily",
            }
        ]

        from app.services import web_article_extraction as wae
        # Simulate extraction failure
        mock_article_fail = MagicMock()
        mock_article_fail.extracted_text = ""
        mock_article_fail.status = "failed"
        mock_article_fail.error = "fetch failed"
        mock_article_fail.metadata.url = "https://law.cornell.edu/uscode/text/47/230"
        mock_article_fail.extraction_method = "failed"
        mock_article_fail.extraction_confidence = 0.0

        # No Firecrawl key configured
        with (
            patch.object(wae, "extract_article", return_value=mock_article_fail),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )

        # Should either have a snippet-only card or a possible_lead_url
        assert (
            len(result.card_drafts) > 0 or
            len(result.possible_lead_urls) > 0
        ), "Expected snippet card or possible_lead_url for failed extraction"

    def test_generate_candidate_cards_uses_provider_raw_when_available(self, monkeypatch):
        """When provider_raw >= 600 chars and not boilerplate, it should be used directly."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards

        raw_content = (
            "Section 230 of the Communications Decency Act grants internet platforms broad "
            "immunity from civil liability for content posted by third parties. This statute, "
            "enacted in 1996, has been consistently interpreted by courts to provide a sweeping "
            "liability shield that prevents plaintiffs from holding platforms accountable for "
            "user-generated harmful content. The law provides that no provider or user of an "
            "interactive computer service shall be treated as the publisher or speaker of any "
            "information provided by another information content provider. Courts have applied "
            "this provision to dismiss lawsuits involving defamation, harassment, sex trafficking, "
            "and other harms facilitated through platform infrastructure. Critics argue this "
            "broad interpretation was never intended by Congress and has allowed platforms to "
            "escape accountability even when they actively promoted or amplified harmful content."
        )
        search_results = [
            {
                "url": "https://law.cornell.edu/uscode/text/47/230",
                "content": "Short snippet",
                "raw_content": raw_content,
                "title": "Section 230",
                "score": 0.9,
                "_provider": "exa",
            }
        ]

        from app.services import web_article_extraction as wae

        # extract_article should NOT be called since raw_content is sufficient
        with (
            patch.object(wae, "extract_article", side_effect=AssertionError("Should not call extract_article")),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )

        # Should have processed the raw content (either card or diagnostic)
        assert result.sources_attempted == 1
        # extract_article was not called (would have raised AssertionError otherwise)

    def test_reranker_used_tracked_in_result(self, monkeypatch):
        """CandidateCardsResult.reranker_used should be set after processing."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards, EvidenceRoleOutput

        passage = (
            "Section 230 immunity protects platforms from civil liability for user content. "
            "Courts have held this provision broadly applies to dismiss lawsuits. Platforms "
            "benefit from this statute in hundreds of cases. Studies show accountability gaps."
        )
        search_results = [
            {
                "url": "https://law.cornell.edu/uscode/text/47/230",
                "content": passage,
                "title": "Section 230",
                "score": 0.9,
            }
        ]

        from app.services import web_article_extraction as wae
        mock_article = MagicMock()
        mock_article.extracted_text = passage * 3  # enough text
        mock_article.status = "ok"
        mock_article.metadata.title = "Section 230"
        mock_article.metadata.author = None
        mock_article.metadata.publication = None
        mock_article.metadata.published_date = None
        mock_article.metadata.url = "https://law.cornell.edu/uscode/text/47/230"
        mock_article.extraction_method = "trafilatura"
        mock_article.extraction_confidence = 0.9

        mechanism_role = EvidenceRoleOutput(
            evidence_role="mechanism_support",
            debate_usefulness_score=7.0,
            best_supported_claim="Section 230 grants platforms immunity",
            safe_tag_scope="Section 230 grants civil liability immunity",
        )

        with (
            patch.object(wae, "extract_article", return_value=mock_article),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
            patch("app.services.research_search._classify_role_deterministic", return_value=mechanism_role),
            patch("app.services.research_search._validate_card_tag", return_value=(
                "Section 230 grants civil liability immunity", None
            )),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )

        # reranker_used should be "heuristic" (no Cohere key in test env)
        assert result.reranker_used in ("heuristic", "cohere", "none"), (
            f"Expected a valid reranker_used value, got: {result.reranker_used}"
        )


# ── Task 7: SearchDiagnostics has reranker_used ───────────────────────────────

class TestSearchDiagnosticsModel:
    def test_reranker_used_field_exists_with_default_none(self):
        from app.models.research import SearchDiagnostics
        diag = SearchDiagnostics()
        assert hasattr(diag, "reranker_used")
        assert diag.reranker_used == "none"

    def test_reranker_used_can_be_set(self):
        from app.models.research import SearchDiagnostics
        diag = SearchDiagnostics(reranker_used="cohere")
        assert diag.reranker_used == "cohere"

    def test_reranker_used_heuristic(self):
        from app.models.research import SearchDiagnostics
        diag = SearchDiagnostics(reranker_used="heuristic")
        assert diag.reranker_used == "heuristic"

    def test_providers_used_field_exists(self):
        from app.models.research import SearchDiagnostics
        diag = SearchDiagnostics()
        assert hasattr(diag, "providers_used")
        assert diag.providers_used == []


# ── Card Builder redesign: instrumentation + reranker/firecrawl integration ────

def _section230_search_setup(monkeypatch):
    """Shared mock setup: one Section 230 source that extracts cleanly."""
    _inject_fake_tavily(monkeypatch)
    from app.services.research_search import EvidenceRoleOutput
    from app.services import web_article_extraction as wae

    passage = (
        "Section 230 immunity protects platforms from civil liability for user content. "
        "Courts have held this provision broadly applies to dismiss lawsuits. Platforms "
        "benefit from this statute in hundreds of cases. Studies show accountability gaps."
    )
    search_results = [
        {
            "url": "https://law.cornell.edu/uscode/text/47/230",
            "content": passage,
            "title": "Section 230",
            "score": 0.9,
        }
    ]
    mock_article = MagicMock()
    mock_article.extracted_text = passage * 3
    mock_article.status = "ok"
    mock_article.metadata.title = "Section 230"
    mock_article.metadata.author = None
    mock_article.metadata.publication = None
    mock_article.metadata.published_date = None
    mock_article.metadata.url = "https://law.cornell.edu/uscode/text/47/230"
    mock_article.extraction_method = "trafilatura"
    mock_article.extraction_confidence = 0.9

    mechanism_role = EvidenceRoleOutput(
        evidence_role="mechanism_support",
        debate_usefulness_score=7.0,
        best_supported_claim="Section 230 grants platforms immunity",
        safe_tag_scope="Section 230 grants civil liability immunity",
    )
    return search_results, wae, mock_article, mechanism_role


class TestRerankerUsedDiagnostics:
    def test_reranker_used_is_heuristic_when_no_cohere(self, monkeypatch):
        """With no Cohere key, reranker_used falls back to heuristic."""
        monkeypatch.setattr("app.config.settings.cohere_api_key", None, raising=False)
        search_results, wae, mock_article, mechanism_role = _section230_search_setup(monkeypatch)
        from app.services.research_search import generate_candidate_cards

        with (
            patch.object(wae, "extract_article", return_value=mock_article),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
            patch("app.services.research_search._classify_role_deterministic", return_value=mechanism_role),
            patch("app.services.research_search._validate_card_tag", return_value=(
                "Section 230 grants civil liability immunity", None
            )),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )
        # use_llm=False means cohere path is skipped → heuristic
        assert result.reranker_used == "heuristic"
        assert result.cohere_rerank_attempted == 0

    def test_reranker_used_is_cohere_when_key_present(self, monkeypatch):
        """When a Cohere key is set and LLM path active, cohere rerank is used."""
        monkeypatch.setattr("app.config.settings.cohere_api_key", "test_cohere_key", raising=False)
        search_results, wae, mock_article, mechanism_role = _section230_search_setup(monkeypatch)
        from app.services.research_search import generate_candidate_cards

        # Provide enough text for 2 chunks (chunker splits at ~400 words with ≥80-word minimum).
        # 15 repetitions of ~35 words = ~525 words → 2 chunks after splitting.
        long_passage = (
            "Section 230 immunity protects platforms from civil liability for user content. "
            "Courts have held this provision broadly applies to dismiss lawsuits. Platforms "
            "benefit from this statute in hundreds of cases. Studies show accountability gaps. "
        ) * 15
        mock_article.extracted_text = long_passage

        # Cohere returns a reordered (non-empty) chunk list
        def fake_cohere(chunks, query, api_key, max_chunks=10, timeout=10.0):
            return list(chunks)

        # Patch at the consumption site (research_search imports extract_article directly).
        with (
            patch("app.services.research_search.extract_article", return_value=mock_article),
            patch("app.services.research_search._rerank_chunks_cohere", side_effect=fake_cohere),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
            patch("app.services.research_search._classify_role_deterministic", return_value=mechanism_role),
            patch("app.services.research_search._validate_card_tag", return_value=(
                "Section 230 grants civil liability immunity", None
            )),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=True,
            )
        assert result.reranker_used == "cohere"
        assert result.cohere_rerank_attempted >= 1
        assert result.cohere_rerank_succeeded >= 1


class TestFirecrawlIntegrationInstrumentation:
    def test_firecrawl_skipped_when_key_none(self, monkeypatch):
        """firecrawl_api_key=None means Firecrawl is never attempted."""
        monkeypatch.setattr("app.config.settings.firecrawl_api_key", None, raising=False)
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards
        from app.services import web_article_extraction as wae

        # extraction fails (no text) → would reach firecrawl step, but key is None
        bad_article = MagicMock()
        bad_article.extracted_text = ""
        bad_article.status = "failed"
        bad_article.error = "no text"
        bad_article.metadata.url = "https://example.com/x"

        search_results = [{"url": "https://example.com/x", "content": "x", "title": "x", "score": 0.5}]

        with (
            patch.object(wae, "extract_article", return_value=bad_article),
            patch("app.services.research_search._extract_with_firecrawl") as fc_mock,
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="t",
                claim_to_support="c",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )
        fc_mock.assert_not_called()
        assert result.firecrawl_attempted == 0

    def test_firecrawl_called_when_key_present_and_extraction_short(self, monkeypatch):
        """With a Firecrawl key and failed primary extraction, Firecrawl is invoked."""
        monkeypatch.setattr("app.config.settings.firecrawl_api_key", "test_fc_key", raising=False)
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards
        from app.services import web_article_extraction as wae

        bad_article = MagicMock()
        bad_article.extracted_text = ""
        bad_article.status = "failed"
        bad_article.error = "no text"
        bad_article.metadata.url = "https://example.com/x"

        good_text = "Section 230 immunity protects platforms from civil liability. " * 20
        search_results = [{"url": "https://example.com/x", "content": "x", "title": "x", "score": 0.5}]

        with (
            patch.object(wae, "extract_article", return_value=bad_article),
            patch("app.services.web_article_extraction.validate_url", return_value=(True, "ok")),
            patch("app.services.research_search._extract_with_firecrawl", return_value=good_text) as fc_mock,
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )
        fc_mock.assert_called()
        assert result.firecrawl_attempted >= 1
        assert result.firecrawl_succeeded >= 1

    def test_firecrawl_failure_does_not_crash(self, monkeypatch):
        """Firecrawl returning None must not raise — pipeline completes."""
        monkeypatch.setattr("app.config.settings.firecrawl_api_key", "test_fc_key", raising=False)
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards
        from app.services import web_article_extraction as wae

        bad_article = MagicMock()
        bad_article.extracted_text = ""
        bad_article.status = "failed"
        bad_article.error = "no text"
        bad_article.metadata.url = "https://example.com/x"

        search_results = [{"url": "https://example.com/x", "content": "x", "title": "x", "score": 0.5}]

        with (
            patch.object(wae, "extract_article", return_value=bad_article),
            patch("app.services.web_article_extraction.validate_url", return_value=(True, "ok")),
            patch("app.services.research_search._extract_with_firecrawl", return_value=None) as fc_mock,
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )
        fc_mock.assert_called()
        assert result.firecrawl_attempted >= 1
        assert result.firecrawl_failed >= 1
        # No card produced, but no exception either
        assert isinstance(result.card_drafts, list)


class TestInstrumentationFieldsDefaults:
    def test_search_diagnostics_has_instrumentation_fields(self):
        from app.models.research import SearchDiagnostics
        diag = SearchDiagnostics()
        assert diag.firecrawl_attempted == 0
        assert diag.firecrawl_succeeded == 0
        assert diag.firecrawl_failed == 0
        assert diag.cohere_rerank_attempted == 0
        assert diag.cohere_rerank_succeeded == 0
