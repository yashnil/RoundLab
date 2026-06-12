"""Tests for debate tag generation (Part 5)."""

import re

from app.services.card_cutting import generate_debate_tag

_GENERIC_RE = re.compile(
    r"[—-]\s+(direct|mechanism|example|impact|definition|authority|counter)\s+support",
    re.IGNORECASE,
)

_MECH_PASSAGE = (
    "Section 230 grants online platforms broad immunity from civil liability for "
    "content posted by their users. This provision shields companies from most "
    "lawsuits arising out of third-party speech."
)
_EXAMPLE_PASSAGE = (
    "In Zeran v. America Online, the court held that Section 230 barred the "
    "plaintiff's defamation claims against the platform, dismissing the case."
)
_IMPACT_PASSAGE = (
    "The failure to intervene in Rwanda contributed to roughly 800,000 deaths over "
    "one hundred days, a catastrophic humanitarian toll."
)


def test_tag_not_starting_with_evidence():
    tag, _ = generate_debate_tag(_MECH_PASSAGE, "Section 230 shields platforms",
                                 "mechanism_support", use_llm=False)
    assert not tag.lower().startswith("evidence:")


def test_tag_not_generic_format():
    tag, _ = generate_debate_tag(_MECH_PASSAGE, "Section 230 shields platforms",
                                 "mechanism_support", use_llm=False)
    assert not _GENERIC_RE.search(tag), f"tag used generic role format: {tag}"


def test_tag_not_truncated_mid_word():
    tag, _ = generate_debate_tag(_MECH_PASSAGE, "Section 230 shields platforms",
                                 "mechanism_support", use_llm=False)
    # No trailing partial word artifacts: tag should end on a complete token.
    assert tag == tag.strip()
    assert not tag.endswith("-")
    # All words should be real words present-ish (no dangling single chars from a cut)
    assert len(tag.split()) <= 20


def test_mechanism_tag_grounded_in_passage():
    tag, _ = generate_debate_tag(_MECH_PASSAGE, "Section 230 shields platforms",
                                 "mechanism_support", use_llm=False)
    assert "grants" in tag.lower() or "immunity" in tag.lower() or "shields" in tag.lower()


def test_example_tag_grounded_in_case():
    tag, _ = generate_debate_tag(_EXAMPLE_PASSAGE, "Section 230 protects platforms",
                                 "example_support", use_llm=False)
    assert "held" in tag.lower() or "court" in tag.lower() or "zeran" in tag.lower()


def test_impact_tag_grounded():
    tag, _ = generate_debate_tag(_IMPACT_PASSAGE, "Non-intervention enables atrocities",
                                 "impact_support", use_llm=False)
    assert "deaths" in tag.lower() or "800,000" in tag or "rwanda" in tag.lower()


def test_slot_context_accepted():
    # Slot context should be accepted without error and produce a grounded tag.
    tag, _ = generate_debate_tag(
        _MECH_PASSAGE, "Section 230 shields platforms", "mechanism_support",
        slot_label="Mechanism/Warrant",
        slot_target_claim="Section 230 shields platforms from liability for user content",
        use_llm=False,
    )
    assert tag and len(tag.split()) <= 20


def test_card_draft_fallback_tag_not_evidence_prefixed():
    """generate_card_draft should never produce an 'Evidence:' tag fallback."""
    from app.models.research import ArticleMetadata, ExtractedArticle
    from app.services.card_cutting import generate_card_draft

    art = ExtractedArticle(
        url="https://example.com/a",
        metadata=ArticleMetadata(url="https://example.com/a"),
        extracted_text=_MECH_PASSAGE * 3,
        extraction_method="paste",
        extraction_confidence=1.0,
        status="ok",
    )
    draft = generate_card_draft(
        article=art, topic="internet law", claim_goal="Section 230 shields platforms",
        slot_label="Mechanism/Warrant",
        slot_target_claim="Section 230 shields platforms from liability",
    )
    assert not draft["tag"].lower().startswith("evidence:")
    assert draft["slot_label"] == "Mechanism/Warrant"
