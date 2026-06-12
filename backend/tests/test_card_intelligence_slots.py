"""Tests for slot-aware card intelligence (Part 9)."""

from app.services.card_cutting import derive_card_intelligence


def _base(**kw):
    defaults = dict(
        evidence_role="example_support",
        best_supported_claim="Kosovo intervention stopped atrocities",
        overclaim_warning="",
        source_quality="high",
        debate_usefulness_score=8.0,
        is_snippet_source=False,
        citation_quality="complete",
        compression_ratio=0.6,
        cut_style="medium_cut",
        is_counter_evidence=False,
        claim="Intervention prevents atrocities",
    )
    defaults.update(kw)
    return derive_card_intelligence(**defaults)


def test_legal_slot_differs_from_historical_slot():
    legal = _base(slot_function="legal/doctrinal support", slot_label="Legal/Doctrinal Warrant")
    hist = _base(slot_function="historical example", slot_label="Historical Example")
    assert legal.why_this_card != hist.why_this_card
    assert "legal" in legal.why_this_card.lower() or "doctrinal" in legal.why_this_card.lower()
    assert "historical" in hist.why_this_card.lower() or "case" in hist.why_this_card.lower()


def test_opponent_response_populated():
    intel = _base(evidence_role="example_support")
    assert intel.opponent_response
    assert "case" in intel.opponent_response.lower()


def test_crossfire_question_populated():
    intel = _base(evidence_role="authority_support")
    assert intel.crossfire_question
    assert "credential" in intel.crossfire_question.lower() or "who wrote" in intel.crossfire_question.lower()


def test_slot_label_in_suggested_block_label():
    intel = _base(slot_label="Legal/Doctrinal Warrant", slot_function="legal/doctrinal support")
    assert intel.suggested_block_label.startswith("Legal/Doctrinal Warrant")


def test_impact_role_opponent_and_crossfire():
    intel = _base(evidence_role="impact_support")
    assert "impact" in intel.opponent_response.lower() or "overstated" in intel.opponent_response.lower()
    assert "weigh" in intel.crossfire_question.lower()


def test_no_slot_context_still_works():
    intel = _base()
    assert intel.why_this_card
    assert intel.opponent_response  # role-based still populated
