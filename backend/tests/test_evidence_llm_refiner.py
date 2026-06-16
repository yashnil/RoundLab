"""Tests for the optional LLM card refiner (mocked — no network)."""

import pytest
from unittest.mock import patch

from app.config import settings
from app.services import evidence_llm_refiner as refiner
from app.services.evidence_llm_refiner import (
    refine_card_with_llm,
    refined_to_intelligence,
    llm_refiner_available,
    _validate_quotes,
    _RefinerOutput,
)

PASSAGE = (
    "In 1995, sustained U.S. and NATO airstrikes combined with diplomacy at Dayton "
    "forced Serb forces to the negotiating table. The credible threat of force changed "
    "the incentives of the warring parties and brought an end to the war in Bosnia."
)


def _out(quotes, tagline="U.S. and NATO pressure helped end the Bosnian war"):
    return _RefinerOutput(
        tagline=tagline,
        read_aloud_quotes=quotes,
        warrant="The card shows credible force plus diplomacy ended the war in Bosnia.",
        impact="Bosnia proves intervention can change incentives and stop violence.",
        what_this_card_proves="Intervention paired with diplomacy can end a war.",
        strategic_strength="Concrete, documented case.",
        potential_weakness="Bosnia may be treated as Balkan-specific.",
        likely_counterargument="Opponents say it does not generalize.",
        best_response="Frame Bosnia as a mechanism, not a one-off.",
        crossfire_question="What about Bosnia would not repeat elsewhere?",
        crossfire_answer="Concede it is one case, keep the mechanism.",
        best_pairing="Pair with a legal/legitimacy card.",
        weighing_angle="Weigh on probability — Bosnia already happened.",
        best_use="rebuttal",
    )


# ── Fallback / availability ────────────────────────────────────────────────────

class TestAvailability:
    def test_disabled_when_feature_off(self, monkeypatch):
        monkeypatch.setattr(settings, "research_enable_llm_refiner", False)
        assert refine_card_with_llm(PASSAGE, claim="x") is None

    def test_no_key_returns_none(self, monkeypatch):
        monkeypatch.setattr(settings, "research_enable_llm_refiner", True)
        monkeypatch.setattr(refiner, "get_openai_api_key", lambda: None)
        assert llm_refiner_available() is False
        assert refine_card_with_llm(PASSAGE, claim="x") is None

    def test_short_passage_returns_none(self, monkeypatch):
        monkeypatch.setattr(settings, "research_enable_llm_refiner", True)
        monkeypatch.setattr(refiner, "get_openai_api_key", lambda: "sk-test")
        assert refine_card_with_llm("too short", claim="x") is None


# ── Span validation ────────────────────────────────────────────────────────────

class TestQuoteValidation:
    def test_exact_quotes_map_to_spans(self):
        spans = _validate_quotes(PASSAGE, [
            "sustained U.S. and NATO airstrikes combined with diplomacy at Dayton",
            "brought an end to the war in Bosnia",
        ])
        assert len(spans) == 2
        for s in spans:
            assert PASSAGE[s.start:s.end] == s.text

    def test_hallucinated_quote_rejected(self):
        spans = _validate_quotes(PASSAGE, ["the moon is made of cheese and tariffs"])
        assert spans == []

    def test_mixed_quotes_keeps_only_exact(self):
        spans = _validate_quotes(PASSAGE, [
            "brought an end to the war in Bosnia",
            "TOTALLY INVENTED SENTENCE NOT IN SOURCE",
        ])
        assert len(spans) == 1


# ── Full refine flow (mocked LLM) ──────────────────────────────────────────────

class TestRefineFlow:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch):
        monkeypatch.setattr(settings, "research_enable_llm_refiner", True)
        monkeypatch.setattr(refiner, "get_openai_api_key", lambda: "sk-test")

    def test_exact_substrings_produce_result(self, monkeypatch):
        monkeypatch.setattr(
            refiner, "_call_llm",
            lambda *a, **k: _out([
                "sustained U.S. and NATO airstrikes combined with diplomacy at Dayton forced Serb forces to the negotiating table",
            ]),
        )
        result = refine_card_with_llm(PASSAGE, topic="intervention", claim="intervention works", role="example_support")
        assert result is not None
        assert result.tagline.startswith("U.S. and NATO")
        assert result.read_aloud_spans
        assert result.validation and result.validation.passed
        # body stays exact source text
        assert result.cut_body == PASSAGE

    def test_hallucinated_spans_fall_back(self, monkeypatch):
        monkeypatch.setattr(refiner, "_call_llm", lambda *a, **k: _out(["INVENTED EVIDENCE NOT IN PASSAGE"]))
        assert refine_card_with_llm(PASSAGE, claim="x", role="example_support") is None

    def test_incoherent_output_falls_back(self, monkeypatch):
        # Verb-less single-word fragments fail validate_read_aloud_card on both passes.
        monkeypatch.setattr(refiner, "_call_llm", lambda *a, **k: _out(["Bosnia", "Dayton"]))
        assert refine_card_with_llm(PASSAGE, claim="x", role="example_support") is None

    def test_intelligence_conversion_populates_fields(self, monkeypatch):
        monkeypatch.setattr(
            refiner, "_call_llm",
            lambda *a, **k: _out(["The credible threat of force changed the incentives of the warring parties and brought an end to the war in Bosnia"]),
        )
        result = refine_card_with_llm(PASSAGE, claim="intervention works", role="example_support")
        assert result is not None
        intel = refined_to_intelligence(result)
        assert intel.warrant_analysis and intel.impact_analysis
        assert intel.weighing_angle and intel.crossfire_question
        assert intel.best_use == "rebuttal"

    def test_retry_with_stricter_then_succeeds(self, monkeypatch):
        calls = {"n": 0}

        def fake_call(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                return _out(["Bosnia"])  # incoherent → triggers strict retry
            return _out(["The credible threat of force changed the incentives of the warring parties and brought an end to the war in Bosnia"])

        monkeypatch.setattr(refiner, "_call_llm", fake_call)
        result = refine_card_with_llm(PASSAGE, claim="x", role="example_support")
        assert result is not None
        assert calls["n"] == 2
