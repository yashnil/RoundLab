"""Tests for per-slot evidence-set search behavior (Parts 2 + 6)."""

from unittest.mock import MagicMock, patch

from app.models.research import ArticleMetadata, ExtractedArticle
from app.services.research_search import (
    EvidenceRoleOutput,
    _post_process_card_set,
    CandidateCardsResult,
    generate_candidate_cards,
)


def _full_article(url: str, text: str) -> ExtractedArticle:
    return ExtractedArticle(
        url=url,
        metadata=ArticleMetadata(url=url, title="T", author="Jane Doe", published_date="2023"),
        extracted_text=text,
        extraction_method="trafilatura",
        extraction_confidence=0.85,
        status="ok",
    )


_PASSAGE = (
    "Section 230 grants online platforms broad immunity from civil liability for "
    "content posted by their users. Courts have consistently applied this provision "
    "to dismiss lawsuits over user-generated harmful content. This shields companies "
    "from most claims arising out of third-party speech, including defamation and "
    "trafficking allegations brought by injured plaintiffs nationwide."
)


def test_slot_metadata_on_each_card():
    results = [
        {"url": "https://law.cornell.edu/x", "content": _PASSAGE, "raw_content": _PASSAGE * 3},
        {"url": "https://brookings.edu/y", "content": _PASSAGE, "raw_content": _PASSAGE * 3},
    ]
    role = EvidenceRoleOutput(
        evidence_role="mechanism_support",
        debate_usefulness_score=8.0,
        best_supported_claim="Section 230 shields platforms from liability",
        safe_tag_scope="Section 230 immunity",
        reasoning_short="mechanism",
        overclaim_warning="",
    )
    with patch("app.services.research_search._classify_role_with_llm", return_value=role), \
         patch("app.services.research_search.rate_source_quality") as mq:
        mq.return_value = MagicMock(source_quality="high", credibility_notes="", warnings=[])
        out = generate_candidate_cards(
            search_results=results, topic="internet law",
            claim_to_support="Section 230 shields platforms from liability",
            side="pro", user_id="u1", use_llm=False, source_quality_min="low",
        )
    assert out.evidence_set_plan is not None
    for card in out.card_drafts:
        assert "slot_label" in card
        assert "slot_id" in card


def test_duplicate_urls_deduplicated():
    same = _PASSAGE
    results = [
        {"url": "https://law.cornell.edu/x", "content": same, "raw_content": same * 3},
        {"url": "https://law.cornell.edu/x", "content": same, "raw_content": same * 3},
    ]
    role = EvidenceRoleOutput(
        evidence_role="mechanism_support", debate_usefulness_score=8.0,
        best_supported_claim="Section 230 shields platforms",
        safe_tag_scope="x", reasoning_short="m", overclaim_warning="",
    )
    with patch("app.services.research_search._classify_role_with_llm", return_value=role), \
         patch("app.services.research_search.rate_source_quality") as mq:
        mq.return_value = MagicMock(source_quality="high", credibility_notes="", warnings=[])
        out = generate_candidate_cards(
            search_results=results, topic="internet law",
            claim_to_support="Section 230 shields platforms",
            side="pro", user_id="u1", use_llm=False, source_quality_min="low",
        )
    urls = [c.get("url") for c in out.card_drafts]
    assert len(urls) == len(set(urls)), f"duplicate URLs not deduped: {urls}"


def test_post_process_routes_snippet_to_weak_leads():
    result = CandidateCardsResult()
    result.card_drafts = [
        {"url": "https://a.com", "body_text": "Alpha beta gamma delta unique one.",
         "tag": "t1", "draft_json": {"is_snippet_source": True}, "debate_usefulness_score": 7.0},
        {"url": "https://b.com", "body_text": "Completely different words here entirely.",
         "tag": "t2", "draft_json": {"is_snippet_source": False}, "debate_usefulness_score": 6.0},
    ]
    _post_process_card_set(result, [], max_cards=5)
    assert len(result.weak_leads) == 1
    assert all(not c.get("draft_json", {}).get("is_snippet_source") for c in result.card_drafts)


def test_post_process_caps_and_sorts():
    # Each body uses entirely distinct vocabulary so none are near-duplicates.
    distinct_bodies = [
        "Quantum entanglement enables instantaneous correlation between particles.",
        "Coral reefs sustain marine biodiversity across tropical oceans worldwide.",
        "Inflation erodes purchasing power when monetary supply expands rapidly.",
        "Vaccines train immune systems to recognize specific viral antigens.",
        "Renewable turbines convert kinetic wind energy into electrical power.",
        "Tectonic plates shift gradually, reshaping continental landmasses over eons.",
        "Algorithms compress data by exploiting statistical redundancy patterns.",
    ]
    result = CandidateCardsResult()
    result.card_drafts = [
        {"url": f"https://s{i}.com", "body_text": distinct_bodies[i],
         "tag": f"t{i}", "draft_json": {"is_snippet_source": False},
         "debate_usefulness_score": float(i)}
        for i in range(7)
    ]
    _post_process_card_set(result, [], max_cards=5)
    assert len(result.card_drafts) == 5
    scores = [c["debate_usefulness_score"] for c in result.card_drafts]
    assert scores == sorted(scores, reverse=True)


def test_post_process_near_duplicate_removed():
    body = "Section 230 grants platforms broad immunity from civil liability for user content posted online."
    result = CandidateCardsResult()
    result.card_drafts = [
        {"url": "https://a.com", "body_text": body, "tag": "t1",
         "draft_json": {"is_snippet_source": False}, "debate_usefulness_score": 8.0},
        {"url": "https://b.com", "body_text": body + " Extra.", "tag": "t2",
         "draft_json": {"is_snippet_source": False}, "debate_usefulness_score": 5.0},
    ]
    _post_process_card_set(result, [], max_cards=5)
    assert len(result.card_drafts) == 1
    # The higher-usefulness card is kept.
    assert result.card_drafts[0]["debate_usefulness_score"] == 8.0


def test_post_process_unfilled_slots():
    from app.services.evidence_set_planner import plan_evidence_set
    plan = plan_evidence_set("internet law", "Section 230 shields platforms", "pro", use_llm=False)
    result = CandidateCardsResult()
    # One card filling only the first slot.
    first_slot = plan.slots[0]
    result.card_drafts = [{
        "url": "https://a.com", "body_text": "Some unique body text alpha beta gamma.",
        "tag": "t", "slot_id": first_slot.slot_id,
        "draft_json": {"is_snippet_source": False, "slot_id": first_slot.slot_id},
        "debate_usefulness_score": 7.0,
    }]
    _post_process_card_set(result, plan.slots, max_cards=5)
    assert first_slot.slot_label not in result.unfilled_slots
    assert len(result.unfilled_slots) == len(plan.slots) - 1
