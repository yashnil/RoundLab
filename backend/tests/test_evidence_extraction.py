"""Tests for the evidence_extraction service.

All tests are pure — no LLM calls (generate_summaries=False).
Validates structured CARD-marker extraction, heuristic extraction,
and the safety rule that missing metadata fields are None (never invented).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.services.document_parsing import TextChunk, _chunk_text, _chunk_by_card_markers, _CARD_MARKER_RE
from app.services.evidence_extraction import (
    ExtractedCard,
    _extract_from_chunk,
    _extract_structured_card,
    _extract_heuristic,
    extract_evidence_cards,
    _MIN_CARD_CHARS_HEURISTIC,
)


# ── Shared fixture text ────────────────────────────────────────────────────────

# A realistic 5-card structured evidence file matching roundlab_test_evidence.txt format
_FIVE_CARD_DOC = """
ROUNDLAB TEST EVIDENCE FILE
TOPIC: Resolved: The United States federal government should substantially reform its social media regulation policies.

This file contains five evidence cards for testing extraction.

CARD 1

Tag: Algorithmic Amplification Undermines Democratic Discourse
Author: Dr. Sarah Chen
Source: Journal of Democracy
Date: 2023

Social media platforms' recommendation algorithms disproportionately promote outrage-inducing content because engagement metrics reward emotional reactions. Research tracking 2.1 million users across major platforms found algorithmic amplification increased exposure to politically extreme content by 47 percent compared to chronological feeds.

The mechanism is straightforward: platforms optimize for time-on-site, which correlates with emotional arousal, which correlates with content that provokes anger or fear.

Claim supported:
Algorithmic amplification by social media platforms systematically promotes emotionally provocative content over factual information, measurably harming public discourse quality.

CARD 2

Tag: Transparency Requirements Reduce Harmful Content
Author: Williams and Patel
Source: Harvard Kennedy School Policy Review
Date: 2022

Platform transparency mandates requiring disclosure of algorithmic ranking criteria have demonstrated measurable reductions in viral misinformation. An analysis of the EU Digital Services Act pilot program found that transparency requirements reduced sharing of fact-checker-flagged content by 23 percent within 90 days of implementation.

Claim supported:
Mandatory algorithmic transparency requirements measurably reduce misinformation spread without requiring content removal mandates.

CARD 3

Tag: Antitrust Reform Needed for Platform Competition
Author: Rodriguez
Source: Yale Law Journal
Date: 2023

Current antitrust frameworks are insufficient to address platform monopolization because they rely on price-based harm analysis. Social media platforms extract value through data and attention rather than price, creating a regulatory gap. The five largest platforms collectively control over 90 percent of social media engagement time in the United States.

Claim supported:
Existing antitrust law cannot adequately address social media platform market consolidation because of its reliance on price-harm analysis.

CARD 4

Tag: Self-Regulation Has Failed
Author: Thompson and Lee
Source: Brookings Institution
Date: 2021

A ten-year retrospective analysis of platform self-regulatory commitments found systematic pattern of non-compliance. Of 47 voluntary commitments made between 2011 and 2020, only 12 were implemented as announced. The remaining 35 were either quietly abandoned, significantly weakened, or implemented in ways that created exceptions capturing the vast majority of harmful content.

Claim supported:
Social media platform voluntary self-regulatory commitments have a documented pattern of non-compliance, making mandatory regulation the necessary alternative.

CARD 5

Tag: First Amendment Permits Algorithmic Transparency Requirements
Author: Anderson
Source: Constitutional Commentary
Date: 2022

Section 230 immunity does not derive from First Amendment protection of platform editorial discretion. Courts have consistently held that commercial entities face constitutional constraints on their ability to claim unlimited editorial privilege when operating as general public forums. Targeted transparency and algorithmic disclosure requirements survive First Amendment scrutiny because they regulate process rather than content.

Claim supported:
Algorithmic transparency and disclosure requirements are constitutionally permissible under First Amendment doctrine because they regulate process rather than restrict speech content.
""".strip()


def _chunks_from_doc(text: str) -> list[TextChunk]:
    """Helper: run the full chunking pipeline on a text string."""
    return _chunk_text(text, page_count=None)


# ── CARD marker detection ──────────────────────────────────────────────────────

class TestCardMarkerDetection:
    def test_detects_card_markers_in_five_card_doc(self):
        assert _CARD_MARKER_RE.search(_FIVE_CARD_DOC) is not None

    def test_does_not_detect_markers_in_plain_text(self):
        plain = "This is a plain paragraph.\n\nAnd another paragraph here."
        assert _CARD_MARKER_RE.search(plain) is None

    def test_case_insensitive_marker(self):
        text = "card 1\n\nsome body text here"
        assert _CARD_MARKER_RE.search(text) is not None

    def test_card_marker_with_surrounding_whitespace(self):
        text = "\n  CARD 3  \n\nbody text"
        assert _CARD_MARKER_RE.search(text) is not None


# ── Card-marker chunking ───────────────────────────────────────────────────────

class TestCardMarkerChunking:
    def test_five_card_doc_produces_five_chunks(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        assert len(chunks) == 5, f"Expected 5 chunks, got {len(chunks)}"

    def test_chunk_headings_are_card_labels(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        for i, chunk in enumerate(chunks):
            assert chunk.heading is not None
            assert chunk.heading.upper().startswith("CARD")

    def test_intro_is_not_a_chunk(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        for chunk in chunks:
            assert "ROUNDLAB TEST EVIDENCE FILE" not in chunk.chunk_text
            assert "TOPIC:" not in chunk.chunk_text

    def test_chunk_bodies_do_not_contain_card_markers(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        for chunk in chunks:
            # The body text should not start with another CARD label
            assert not chunk.chunk_text.strip().upper().startswith("CARD ")

    def test_chunks_are_sequentially_indexed(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_card_one_body_contains_algorithmic(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        assert "algorithmic" in chunks[0].chunk_text.lower()

    def test_card_bodies_do_not_merge(self):
        chunks = _chunks_from_doc(_FIVE_CARD_DOC)
        # CARD 2 body should NOT appear in CARD 1 chunk
        assert "Williams and Patel" not in chunks[0].chunk_text
        assert "Rodriguez" not in chunks[1].chunk_text


# ── Structured extraction ──────────────────────────────────────────────────────

class TestStructuredExtraction:
    def _card_chunks(self) -> list[TextChunk]:
        return _chunks_from_doc(_FIVE_CARD_DOC)

    def test_five_card_doc_extracts_five_cards(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert len(cards) == 5, f"Expected 5 cards, got {len(cards)}"

    def test_card_one_tag(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].tag == "Algorithmic Amplification Undermines Democratic Discourse"

    def test_card_one_author(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].author == "Dr. Sarah Chen"

    def test_card_one_source(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].source == "Journal of Democracy"

    def test_card_one_year(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].year == 2023

    def test_card_one_attribution_complete(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].attribution_complete is True

    def test_card_one_claim_summary(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].claim_summary is not None
        assert "algorithmic" in cards[0].claim_summary.lower()

    def test_card_two_multi_word_author(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[1].author == "Williams and Patel"

    def test_card_two_year_2022(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[1].year == 2022

    def test_card_four_author_and_source(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[3].author == "Thompson and Lee"
        assert cards[3].source == "Brookings Institution"

    def test_card_body_excludes_metadata_lines(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        for card in cards:
            # Body should not start with Tag:/Author:/Source:/Date: lines
            first_line = card.card_text.strip().split("\n")[0].lower()
            for prefix in ("tag:", "author:", "source:", "date:"):
                assert not first_line.startswith(prefix), (
                    f"Card body starts with metadata line: {first_line!r}"
                )

    def test_card_body_excludes_claim_supported_section(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        for card in cards:
            assert "Claim supported:" not in card.card_text
            assert "claim supported:" not in card.card_text.lower()

    def test_document_title_not_extracted_as_card(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        for card in cards:
            assert "ROUNDLAB TEST EVIDENCE FILE" not in card.card_text
            assert "TOPIC:" not in (card.tag or "")

    def test_all_cards_have_tags(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        for card in cards:
            assert card.tag is not None and len(card.tag) > 5

    def test_all_cards_attribution_complete(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        for card in cards:
            assert card.attribution_complete is True

    def test_cards_preserve_order(self):
        chunks = self._card_chunks()
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards[0].tag == "Algorithmic Amplification Undermines Democratic Discourse"
        assert cards[4].tag == "First Amendment Permits Algorithmic Transparency Requirements"


# ── Missing metadata safety ────────────────────────────────────────────────────

class TestMissingMetadataSafety:
    def test_card_with_no_author_is_incomplete(self):
        text = (
            "Tag: Some important argument\n"
            "Source: Harvard\n"
            "Date: 2023\n\n"
            "This is the body of the card with enough text to be extracted. "
            "It makes an important claim about the topic at hand."
        )
        chunk = TextChunk(chunk_text=text, chunk_index=0, heading="CARD 1")
        card = _extract_from_chunk(chunk)
        assert card is not None
        assert card.author is None
        assert card.attribution_complete is False

    def test_card_with_no_date_is_incomplete(self):
        text = (
            "Tag: Some argument\n"
            "Author: Smith\n"
            "Source: Journal of Policy\n\n"
            "This is the body of the evidence card with enough text for extraction."
        )
        chunk = TextChunk(chunk_text=text, chunk_index=0, heading="CARD 1")
        card = _extract_from_chunk(chunk)
        assert card is not None
        assert card.year is None
        assert card.attribution_complete is False

    def test_no_invented_author_when_missing(self):
        text = "Date: 2023\n\nLong body text about the argument at hand. " * 3
        chunk = TextChunk(chunk_text=text, chunk_index=0, heading="CARD 1")
        card = _extract_from_chunk(chunk)
        if card is not None:
            assert card.author is None

    def test_no_invented_year_when_missing(self):
        text = "Tag: Test\nAuthor: Smith\n\nBody text without any year anywhere in sight. " * 2
        chunk = TextChunk(chunk_text=text, chunk_index=0, heading="CARD 1")
        card = _extract_from_chunk(chunk)
        if card is not None:
            assert card.year is None


# ── Heuristic extraction (unchanged behavior for plain chunks) ─────────────────

class TestHeuristicExtraction:
    def _make_chunk(self, text: str, index: int = 0, heading: str | None = None) -> TextChunk:
        return TextChunk(chunk_text=text, chunk_index=index, heading=heading)

    def test_returns_none_for_short_chunk(self):
        chunk = self._make_chunk("Short.")
        assert _extract_from_chunk(chunk) is None

    def test_extracts_author_and_year_from_body(self):
        text = (
            "Smith 2023 — The United States defense industrial base faces significant "
            "capacity constraints. Foreign Affairs reports that production shortfalls "
            "in key munitions categories reached crisis levels by 2022."
        )
        card = _extract_from_chunk(self._make_chunk(text))
        assert card is not None
        assert card.author == "Smith"
        assert card.year == 2023

    def test_attribution_incomplete_without_author(self):
        text = (
            "Research published in 2022 demonstrates that military basing costs have "
            "increased by 40 percent over the prior decade, creating fiscal pressure "
            "on domestic defense investment priorities across all service branches."
        )
        card = _extract_from_chunk(self._make_chunk(text))
        assert card is not None
        assert card.author is None
        assert card.attribution_complete is False

    def test_extracts_known_source(self):
        text = (
            "Jones 2021 — Brookings Institution analysis finds that alliance credibility "
            "depends on forward presence. This is the body of the evidence card. "
            "The research is comprehensive and covers multiple regions."
        )
        card = _extract_from_chunk(self._make_chunk(text))
        assert card is not None
        assert card.source == "Brookings Institution" or (card.source and "Brookings" in card.source)

    def test_extracts_multiple_cards(self):
        chunks = [
            self._make_chunk(
                "Smith 2022 — Military bases impose fiscal costs. "
                "The Congressional Budget Office estimates presence costs exceed 150 billion annually. "
                "This represents a major portion of defense spending.",
                index=0,
            ),
            self._make_chunk("Too short.", index=1),
            self._make_chunk(
                "Jones 2023 — Regional stability depends on credible deterrence. "
                "The Brookings Institution finds alliance guarantees backed by physical "
                "presence reduce conflict probability by 30 percent on average.",
                index=2,
            ),
        ]
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert len(cards) == 2

    def test_skips_short_chunks(self):
        chunks = [
            self._make_chunk("Too short.", index=0),
            self._make_chunk("Also short.", index=1),
        ]
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards == []

    def test_empty_chunk_list(self):
        cards = extract_evidence_cards([], generate_summaries=False)
        assert cards == []

    def test_card_chunk_index_preserved(self):
        chunks = [
            self._make_chunk(
                "Smith 2020 — Long body text about deterrence stability and military "
                "presence providing meaningful benefits that exceed alternative strategies.",
                index=7,
            )
        ]
        cards = extract_evidence_cards(chunks, generate_summaries=False)
        assert cards
        assert cards[0].chunk_index == 7
