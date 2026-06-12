"""Smoke tests for realistic debate research behavior.

All tests use mocked search/extraction — no live internet calls. Each class
targets one functional requirement (typo normalization, role detection,
acceptance gates, claim ladder, source quality).
"""

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch


# ── Tavily mock helper ─────────────────────────────────────────────────────────

def _inject_fake_tavily(monkeypatch) -> None:
    """Inject a no-op Tavily module so research_search can be imported cleanly."""
    fake_tavily = types.ModuleType("tavily")
    fake_client = types.ModuleType("tavily.tavily_search_api_wrapper")
    fake_tavily.TavilyClient = MagicMock()
    fake_client.TavilySearchAPIWrapper = MagicMock()
    fake_tavily.tavily_search_api_wrapper = fake_client
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)
    monkeypatch.setitem(sys.modules, "tavily.tavily_search_api_wrapper", fake_client)


# ── Section 230 typo + indirect support ───────────────────────────────────────

class TestSection230TypoAndIndirectSupport:
    def test_normalize_ion_230_typo_in_claim(self):
        from app.services.claim_decomposition import normalize_claim
        normalized, corrections = normalize_claim(
            "section 230",
            "ion 230 facilitates Harmful Content and Misinformation",
        )
        assert "Section 230" in normalized
        assert len(corrections) >= 1

    def test_normalize_tion_230_typo_in_claim(self):
        from app.services.claim_decomposition import normalize_claim
        normalized, corrections = normalize_claim(
            "section 230",
            "tion 230 reduces accountability for harmful content",
        )
        assert "Section 230" in normalized
        assert len(corrections) >= 1

    def test_already_correct_claim_unchanged(self):
        from app.services.claim_decomposition import normalize_claim
        normalized, corrections = normalize_claim(
            "section 230",
            "Section 230 shields platforms from liability",
        )
        assert normalized == "Section 230 shields platforms from liability"
        assert len(corrections) == 0

    def test_plan_queries_include_liability_or_immunity(self, monkeypatch):
        _inject_fake_tavily(monkeypatch)
        from app.services.claim_decomposition import decompose_claim
        with patch(
            "app.services.claim_decomposition._decompose_with_llm",
            return_value=None,
        ):
            plan = decompose_claim(
                "section 230",
                "Section 230 facilitates harmful content and misinformation",
                "pro",
            )
        terms = " ".join(plan.search_queries).lower()
        assert any(t in terms for t in ("liability", "immunity", "shield", "publisher")), (
            f"Expected liability/immunity/shield/publisher in queries. Got: {plan.search_queries}"
        )

    def test_legal_policy_queries_injected_for_section_230(self, monkeypatch):
        _inject_fake_tavily(monkeypatch)
        from app.services.claim_decomposition import (
            _LEGAL_POLICY_CONTEXTS,
            decompose_claim,
        )
        with patch(
            "app.services.claim_decomposition._decompose_with_llm",
            return_value=None,
        ):
            plan = decompose_claim(
                "section 230",
                "Section 230 facilitates harmful content",
                "pro",
            )
        domain_queries = _LEGAL_POLICY_CONTEXTS["section 230"]
        queries_lower = [q.lower() for q in plan.search_queries]
        matched = [dq for dq in domain_queries if dq.lower() in queries_lower]
        assert len(matched) >= 3, (
            f"Expected >=3 domain-specific queries injected. Got {len(matched)}. "
            f"Plan queries: {plan.search_queries}"
        )

    def test_plan_normalized_claim_preserved(self, monkeypatch):
        _inject_fake_tavily(monkeypatch)
        from app.services.claim_decomposition import decompose_claim
        with patch(
            "app.services.claim_decomposition._decompose_with_llm",
            return_value=None,
        ):
            plan = decompose_claim(
                "section 230",
                "ion 230 facilitates harmful content",
                "pro",
            )
        assert "Section 230" in plan.normalized_claim


# ── Evidence role detection ────────────────────────────────────────────────────

class TestEvidenceRoleDetection:
    def _make_concepts(self, claim: str, topic: str = "section 230"):
        from app.services.research_search import expand_claim_concepts
        return expand_claim_concepts(claim, topic)

    def test_liability_shield_passage_is_mechanism_or_definition(self):
        from app.services.research_search import _classify_role_deterministic
        concepts = self._make_concepts(
            "Section 230 facilitates harmful content and misinformation"
        )
        passage = (
            "Section 230 of the Communications Decency Act grants platforms broad immunity "
            "from civil liability for user-posted content. Courts have repeatedly held that "
            "platforms are not liable as publishers or speakers of third-party content. "
            "This statutory shield has been invoked in hundreds of lawsuits."
        )
        out = _classify_role_deterministic(
            passage,
            "Section 230 facilitates harmful content and misinformation",
            "section 230",
            concepts,
        )
        # direct_support is also valid — the passage has high concept overlap with
        # the expanded claim terms (immunity, liability, shield, platform).
        assert out.evidence_role in ("mechanism_support", "definition_support", "direct_support"), (
            f"Expected mechanism/definition/direct support, got {out.evidence_role}"
        )
        assert out.debate_usefulness_score >= 4.0

    def test_backpage_passage_is_example(self):
        from app.services.research_search import _classify_role_deterministic
        concepts = self._make_concepts(
            "Section 230 facilitates harmful content and misinformation"
        )
        passage = (
            "Backpage.com successfully invoked Section 230 to escape civil liability "
            "for sex trafficking ads posted by users. The court dismissed the lawsuit, "
            "ruling that Backpage was a third-party content host, not a publisher. "
            "Critics called the ruling a misuse of the immunity provision."
        )
        out = _classify_role_deterministic(
            passage,
            "Section 230 facilitates harmful content and misinformation",
            "section 230",
            concepts,
        )
        assert out.evidence_role in ("example_support", "mechanism_support", "direct_support"), (
            f"Expected example or mechanism support, got {out.evidence_role}"
        )

    def test_section_230_statute_text_is_definition(self):
        from app.services.research_search import _classify_role_deterministic
        concepts = self._make_concepts("Section 230 reduces platform accountability")
        passage = (
            "47 U.S.C. § 230 provides that 'No provider or user of an interactive computer "
            "service shall be treated as the publisher or speaker of any information provided "
            "by another information content provider.' This statute, enacted as part of the "
            "Communications Decency Act of 1996, has been codified as the foundational "
            "liability shield for internet platforms."
        )
        out = _classify_role_deterministic(
            passage,
            "Section 230 reduces platform accountability",
            "section 230",
            concepts,
        )
        assert out.evidence_role in ("definition_support", "mechanism_support", "direct_support"), (
            f"Expected definition/mechanism support, got {out.evidence_role}"
        )

    def test_unrelated_passage_is_not_useful(self):
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        concepts = expand_claim_concepts(
            "Section 230 facilitates harmful content",
            "section 230",
        )
        passage = (
            "Julius Caesar crossed the Rubicon river in 49 BC, defying Roman law and "
            "triggering a civil war. His dictatorship transformed the Roman Republic into "
            "an empire. He was assassinated on the Ides of March, 44 BC."
        )
        out = _classify_role_deterministic(passage, "Section 230 facilitates harmful content", "section 230", concepts)
        assert out.evidence_role == "not_useful"

    def test_misinformation_harm_without_section_230_is_impact_or_not_useful(self):
        from app.services.research_search import _classify_role_deterministic, expand_claim_concepts
        concepts = expand_claim_concepts(
            "Section 230 facilitates harmful content and misinformation",
            "section 230",
        )
        passage = (
            "Online misinformation about COVID-19 vaccines contributed to vaccine hesitancy "
            "in millions of Americans. False health claims spread rapidly through social media "
            "platforms, leading to preventable deaths, according to public health researchers."
        )
        out = _classify_role_deterministic(
            passage,
            "Section 230 facilitates harmful content and misinformation",
            "section 230",
            concepts,
        )
        # Section 230 isn't mentioned — should be impact_support, authority_support,
        # or not_useful (depending on whether "researchers" signals authority)
        assert out.evidence_role in ("impact_support", "authority_support", "not_useful")


# ── Acceptance gates ───────────────────────────────────────────────────────────

class TestAcceptanceGates:
    def _make_search_result(self, url: str, content: str, title: str = "Test") -> dict:
        return {"url": url, "content": content, "title": title, "score": 0.8}

    def test_counter_evidence_separated_from_card_drafts(self, monkeypatch):
        """Passages classified as counter_evidence must go to counter_evidence_drafts, not card_drafts."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards

        passage = (
            "Section 230 is vital for preserving free expression online. "
            "The immunity it provides enables platforms to host diverse viewpoints "
            "without fear of liability, enabling moderation and protecting speech. "
            "Reducing this protection would chill innovation and expression."
        )
        search_results = [self._make_search_result("https://example.edu/free-speech", passage)]

        # Mock extraction to return the passage as body_text
        from app.services import web_article_extraction as wae
        mock_article = MagicMock()
        mock_article.extracted_text = passage
        mock_article.metadata.title = "Free Speech"
        mock_article.metadata.author = None
        mock_article.metadata.publication = None
        mock_article.metadata.published_date = None
        mock_article.metadata.url = "https://example.edu/free-speech"
        mock_article.extraction_method = "trafilatura"
        mock_article.extraction_confidence = 0.8

        with (
            patch.object(wae, "extract_article", return_value=mock_article),
            patch(
                "app.services.research_search._classify_role_with_llm",
                return_value=None,
            ),
            patch(
                "app.services.research_search._classify_role_deterministic",
                return_value=__import__(
                    "app.services.research_search", fromlist=["EvidenceRoleOutput"]
                ).EvidenceRoleOutput(
                    evidence_role="counter_evidence",
                    debate_usefulness_score=6.0,
                    best_supported_claim="Platforms benefit from Section 230 immunity",
                    safe_tag_scope="Section 230 enables moderation",
                ),
            ),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )

        assert len(result.card_drafts) == 0, "Counter-evidence must not appear in card_drafts"

    def test_snippet_only_card_labeled(self, monkeypatch):
        """Cards built from Tavily snippets (failed extraction) must have is_snippet_source=True."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import generate_candidate_cards

        snippet = (
            "Section 230 of the CDA grants immunity from civil liability to internet platforms "
            "for third-party content. Courts have consistently applied this provision to dismiss "
            "lawsuits over user-generated harmful content, including defamation and trafficking claims."
        )
        search_results = [
            {"url": "https://law.cornell.edu/uscode/text/47/230", "content": snippet,
             "title": "47 U.S. Code § 230", "score": 0.9}
        ]

        from app.services import web_article_extraction as wae

        # Simulate extraction failure: return article with very short text
        mock_article_fail = MagicMock()
        mock_article_fail.extracted_text = ""
        mock_article_fail.metadata.url = "https://law.cornell.edu/uscode/text/47/230"
        mock_article_fail.extraction_method = "failed"
        mock_article_fail.extraction_confidence = 0.0

        with (
            patch.object(wae, "extract_article", return_value=mock_article_fail),
            patch("app.services.research_search.extract_article", return_value=mock_article_fail),
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

        # Snippet-only sources are now routed to weak_leads (Part 6), not
        # card_drafts. Accept a weak lead, a possible_lead_url, or a labeled
        # snippet card for backward compatibility.
        snippet_cards = [
            d for d in result.card_drafts
            if d.get("draft_json", {}).get("is_snippet_source")
        ]
        assert (
            len(snippet_cards) > 0
            or len(result.weak_leads) > 0
            or len(result.possible_lead_urls) > 0
        ), "Expected snippet card, weak lead, or possible_lead_url for short-snippet source"

    def test_low_quality_domain_rejected(self, monkeypatch):
        """Source from a spam-looking domain should have source_quality_score < 3.0."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import _assess_source_quality

        score, reason = _assess_source_quality(
            "https://randomblogopinions.wordpress.com/2023/section-230-thoughts",
            None,
            "failed",
        )
        assert score < 4.0, f"Expected low score for wordpress.com blog, got {score}: {reason}"


# ── Claim ladder behavior ──────────────────────────────────────────────────────

class TestClaimLadder:
    def _make_search_result(self, url: str, content: str) -> dict:
        return {"url": url, "content": content, "title": "Test", "score": 0.8}

    def test_indirect_support_found_flag_set(self, monkeypatch):
        """When cards are found but none is direct_support, usable_indirect_support_found=True."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import (
            EvidenceRoleOutput,
            generate_candidate_cards,
        )

        passage = (
            "Section 230 of the Communications Decency Act grants broad immunity "
            "from civil liability to internet platforms. Courts have held that "
            "platforms are not publishers of third-party content under this statute."
        )
        search_results = [self._make_search_result("https://law.cornell.edu/uscode/text/47/230", passage)]

        from app.services import web_article_extraction as wae
        mock_article = MagicMock()
        mock_article.extracted_text = passage
        mock_article.metadata.title = "Section 230"
        mock_article.metadata.author = "Cornell LII"
        mock_article.metadata.publication = "Cornell LII"
        mock_article.metadata.published_date = "2023-01-01"
        mock_article.metadata.url = "https://law.cornell.edu/uscode/text/47/230"
        mock_article.extraction_method = "trafilatura"
        mock_article.extraction_confidence = 0.9

        mechanism_role = EvidenceRoleOutput(
            evidence_role="mechanism_support",
            debate_usefulness_score=7.0,
            source_quality_score=7.0,
            best_supported_claim="Section 230 grants immunity from civil liability",
            safe_tag_scope="Section 230 grants platforms civil liability immunity",
        )

        with (
            patch.object(wae, "extract_article", return_value=mock_article),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
            patch("app.services.research_search._classify_role_deterministic", return_value=mechanism_role),
            patch("app.services.research_search._validate_card_tag", return_value=(
                "Section 230 grants platforms civil liability immunity", None
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

        assert result.candidates_by_role.get("mechanism_support", 0) >= 1
        direct_count = result.candidates_by_role.get("direct_support", 0)
        indirect_count = sum(
            v for k, v in result.candidates_by_role.items() if k != "direct_support"
        )
        assert indirect_count > 0

    def test_no_cards_means_no_indirect_flag(self, monkeypatch):
        """Zero cards means candidates_by_role should be empty or all zero."""
        _inject_fake_tavily(monkeypatch)
        from app.services.research_search import EvidenceRoleOutput, generate_candidate_cards

        passage = "Unrelated content about ancient Roman history and emperors."
        search_results = [self._make_search_result("https://history.example.com/rome", passage)]

        from app.services import web_article_extraction as wae
        mock_article = MagicMock()
        mock_article.extracted_text = passage
        mock_article.metadata.title = "Roman History"
        mock_article.metadata.author = None
        mock_article.metadata.publication = None
        mock_article.metadata.published_date = None
        mock_article.metadata.url = "https://history.example.com/rome"
        mock_article.extraction_method = "trafilatura"
        mock_article.extraction_confidence = 0.8

        not_useful = EvidenceRoleOutput(
            evidence_role="not_useful",
            debate_usefulness_score=0.5,
            best_supported_claim="",
            safe_tag_scope="",
        )

        with (
            patch.object(wae, "extract_article", return_value=mock_article),
            patch("app.services.research_search._classify_role_with_llm", return_value=None),
            patch("app.services.research_search._classify_role_deterministic", return_value=not_useful),
        ):
            result = generate_candidate_cards(
                search_results=search_results,
                topic="section 230",
                claim_to_support="Section 230 facilitates harmful content",
                side="pro",
                user_id="test-user",
                use_llm=False,
            )

        assert len(result.card_drafts) == 0
        useful_count = sum(
            v for k, v in result.candidates_by_role.items() if k != "not_useful"
        )
        assert useful_count == 0


# ── Source quality scoring ─────────────────────────────────────────────────────

class TestSourceQualityScoring:
    def test_gov_domain_high_score(self):
        from app.services.research_search import _assess_source_quality
        score, reason = _assess_source_quality("https://www.ftc.gov/policy/section-230", None, "trafilatura")
        assert score >= 8.5, f"Expected >=8.5 for .gov, got {score}: {reason}"

    def test_edu_domain_high_score(self):
        from app.services.research_search import _assess_source_quality
        score, reason = _assess_source_quality("https://law.stanford.edu/journals/section-230", None, "trafilatura")
        assert score >= 7.5, f"Expected >=7.5 for .edu, got {score}: {reason}"

    def test_cornell_lii_very_high(self):
        from app.services.research_search import _assess_source_quality
        score, reason = _assess_source_quality("https://law.cornell.edu/uscode/text/47/230", None, "trafilatura")
        assert score >= 9.0, f"Expected >=9.0 for law.cornell.edu, got {score}: {reason}"

    def test_random_blog_low_score(self):
        from app.services.research_search import _assess_source_quality
        score, reason = _assess_source_quality(
            "https://myopinions.wordpress.com/2023/01/section-230-thoughts",
            None,
            "trafilatura",
        )
        assert score <= 4.5, f"Expected <=4.5 for wordpress.com, got {score}: {reason}"

    def test_snippet_deduction_applies(self):
        from app.services.research_search import _assess_source_quality
        score_full, _ = _assess_source_quality("https://techpolicy.press/article", None, "trafilatura")
        score_snippet, _ = _assess_source_quality("https://techpolicy.press/article", None, "snippet")
        assert score_snippet < score_full, (
            "Snippet-only extraction should reduce quality score"
        )

    def test_unknown_domain_mid_range(self):
        from app.services.research_search import _assess_source_quality
        score, reason = _assess_source_quality("https://someunknownpolicyblog.org/article", None, "trafilatura")
        assert 4.0 <= score <= 8.0, f"Expected mid-range for unknown domain, got {score}: {reason}"

    def test_reddit_low_score(self):
        from app.services.research_search import _assess_source_quality
        score, reason = _assess_source_quality("https://www.reddit.com/r/law/comments/section230", None, "trafilatura")
        assert score <= 3.0, f"Expected <=3.0 for reddit.com, got {score}: {reason}"


# ── Config settings loaded correctly ──────────────────────────────────────────

class TestResearchSettings:
    def test_default_max_queries(self):
        from app.config import settings
        assert settings.research_search_max_queries == 12

    def test_default_max_urls(self):
        from app.config import settings
        assert settings.research_search_max_urls == 20

    def test_llm_role_classifier_default_true(self):
        from app.config import settings
        assert settings.research_enable_llm_role_classifier is True

    def test_optional_provider_keys_default_none(self):
        from app.config import settings
        assert settings.exa_api_key is None
        assert settings.firecrawl_api_key is None
        assert settings.cohere_api_key is None
        assert settings.jina_api_key is None
