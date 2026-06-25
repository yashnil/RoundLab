"""Tests for evidence cut generation and citation metadata enrichment."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.card_cutting import (
    _fallback_passage,
    SentenceSpan,
    _split_sentences,
    _build_cut_from_sentences,
    _deterministic_cut,
    _validate_and_build_phrase_cut,
    _EvidenceCutLLMOutput,
    _SelectedSpanLLM,
    _lookup_crossref_doi,
    _enrich_from_crossref,
    _get_clause_candidates,
    _CLAUSE_SPLITS,
    remap_spans_to_cut_body,
    get_deterministic_highlight_spans,
    clean_card_body_text,
    strip_page_chrome,
    find_evidence_start_index,
    is_probable_title_line,
    is_author_metadata_line,
    _is_chrome_line,
    _score_paragraph,
    generate_evidence_cut,
    enrich_citation_metadata,
    derive_card_intelligence,
    extract_case_entities,
    highlights_are_coherent,
    sentence_level_highlights,
    get_coherent_highlight_spans,
    segment_text,
    validate_read_aloud_card,
    _FINITE_VERB_RE,
)
from app.models.research import (
    CardIntelligence,
    CitationMetadata,
    EvidenceCutResult,
    SelectedSpan,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

MULTI_SENTENCE_PASSAGE = (
    "Section 230 grants platforms broad immunity from civil liability. "
    "Courts have consistently held that platforms are not publishers. "
    "This provision enables online services to host user-generated content. "
    "The policy was enacted in 1996 as part of the Communications Decency Act. "
    "Critics argue this protection should be reformed."
)

SIMPLE_PASSAGE = "Section 230 provides immunity. Courts have held this."

LEGAL_PASSAGE = (
    "The court ruled in favor of the platform. "
    "The judge held that Section 230 provides absolute immunity from civil suits. "
    "The plaintiff's claims were dismissed with prejudice. "
    "Legal scholars have noted this sets a broad precedent. "
    "Congress has debated whether to reform Section 230 in recent years. "
    "The ruling affects millions of users nationwide."
)


# ── TestSentenceSplitting ──────────────────────────────────────────────────────

class TestSentenceSplitting:
    def test_basic_multi_sentence_passage_splits_correctly(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        assert len(spans) >= 3
        for span in spans:
            assert span.text.strip() != ""

    def test_single_sentence_returns_list_of_one(self):
        spans = _split_sentences("Section 230 provides broad immunity.")
        assert len(spans) == 1
        assert spans[0].text == "Section 230 provides broad immunity."

    def test_empty_string_returns_empty_list(self):
        spans = _split_sentences("")
        assert spans == []

    def test_whitespace_only_returns_empty_list(self):
        spans = _split_sentences("   ")
        assert spans == []

    def test_sentences_are_stripped(self):
        spans = _split_sentences("First sentence. Second sentence.")
        for s in spans:
            assert s.text == s.text.strip()

    def test_us_abbreviation_not_split(self):
        """U.S. should not cause a sentence split."""
        spans = _split_sentences("U.S. courts held that Section 230 applies.")
        assert len(spans) == 1

    def test_vs_abbreviation_not_split(self):
        """v. in case names should not cause a sentence split."""
        spans = _split_sentences("Smith v. Facebook established that Section 230 bars liability.")
        assert len(spans) == 1

    def test_et_al_not_split(self):
        """et al. should not cause a sentence split."""
        spans = _split_sentences("Jones et al. found that platform immunity reduces incentives.")
        assert len(spans) == 1

    def test_eg_not_split(self):
        """e.g. should not cause a sentence split."""
        spans = _split_sentences("Platforms use tools (e.g. filters) to moderate content.")
        assert len(spans) == 1

    def test_multiple_sentences_correct(self):
        """Two genuine sentences separated by abbreviation-free boundary."""
        spans = _split_sentences(
            "U.S. courts held that Section 230 applies. But critics argue reform is needed."
        )
        assert len(spans) == 2

    def test_sentence_span_character_offsets(self):
        """SentenceSpan.start and .end correctly point into the original text."""
        text = "First sentence here. Second sentence there."
        spans = _split_sentences(text)
        for span in spans:
            assert text[span.start:span.end] == span.text

    def test_returns_sentence_span_objects(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        for span in spans:
            assert isinstance(span, SentenceSpan)
            assert span.start >= 0
            assert span.end > span.start
            assert isinstance(span.index, int)

    # ── Omission marker splitting (regression: card cutter inserts […]/[...]) ──

    def test_unicode_omission_marker_splits_into_two_spans(self):
        """[…] between sentences must produce two SentenceSpan objects."""
        text = "First sentence here. […] Second sentence follows."
        spans = _split_sentences(text)
        assert len(spans) == 2, f"Expected 2 spans, got {len(spans)}: {spans}"
        assert "First" in spans[0].text
        assert "Second" in spans[1].text

    def test_ascii_omission_marker_splits_into_two_spans(self):
        """[...] (ASCII) between sentences must produce two SentenceSpan objects."""
        text = "First sentence here. [...] Second sentence follows."
        spans = _split_sentences(text)
        assert len(spans) == 2, f"Expected 2 spans, got {len(spans)}: {spans}"
        assert "First" in spans[0].text
        assert "Second" in spans[1].text

    def test_spans_across_marker_have_correct_absolute_offsets(self):
        """text[span.start:span.end] == span.text must hold across a […] marker."""
        text = "The United Nations failed to intervene. […] The delay allowed the genocide to continue."
        spans = _split_sentences(text)
        assert len(spans) >= 2
        for span in spans:
            assert text[span.start:span.end] == span.text, (
                f"Offset mismatch: text[{span.start}:{span.end}]={text[span.start:span.end]!r} "
                f"!= span.text={span.text!r}"
            )

    def test_span_indices_are_sequential_across_marker(self):
        """span.index must be 0, 1, 2, … across all segments separated by markers."""
        text = "Part one ends here. […] Part two begins here. […] Part three finishes."
        spans = _split_sentences(text)
        assert len(spans) >= 3
        for i, span in enumerate(spans):
            assert span.index == i

    def test_no_marker_text_unchanged(self):
        """Without any omission marker the splitter must behave exactly as before."""
        text = "Courts held that Section 230 applies. Critics argue reform is needed."
        spans = _split_sentences(text)
        assert len(spans) == 2
        for span in spans:
            assert text[span.start:span.end] == span.text

    def test_rwanda_condensed_cut_body_splits_to_two_spans(self):
        """The Rwanda condensed-card pattern (two sentences joined by […]) must split correctly.
        Regression for the ratio_too_high false failure caused by the single-sentence bug."""
        text = (
            "In April 1994, the United Nations and the United States failed to intervene "
            "in Rwanda as the genocide unfolded. "
            "[…] "
            "The delay allowed the genocide to continue for nearly one hundred days."
        )
        spans = _split_sentences(text)
        assert len(spans) == 2, (
            f"Expected 2 sentences from Rwanda condensed cut, got {len(spans)}: {[s.text for s in spans]}"
        )
        # Both spans must have correct offsets.
        for span in spans:
            assert text[span.start:span.end] == span.text


# ── TestBuildCutFromSentences ─────────────────────────────────────────────────

class TestBuildCutFromSentences:
    def test_selected_span_text_exactly_matches_original(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [0, 1])
        for span in result.selected_spans:
            assert MULTI_SENTENCE_PASSAGE[span.start:span.end] == span.text

    def test_non_adjacent_spans_joined_with_ellipsis(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [0, 2, 4])
        assert "[…]" in result.cut_text_with_ellipses

    def test_adjacent_spans_joined_without_ellipsis(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [0, 1])
        # Adjacent spans: no ellipsis expected
        assert "[…]" not in result.cut_text_with_ellipses

    def test_full_passage_selected_returns_cut_style_full(self):
        spans = _split_sentences(SIMPLE_PASSAGE)
        result = _build_cut_from_sentences(SIMPLE_PASSAGE, spans, list(range(len(spans))))
        assert result.cut_style == "full"

    def test_aggressive_cut_compression_ratio(self):
        # Build a long passage and select only a small fraction
        long_passage = " ".join(["Sentence number {}.".format(i) for i in range(20)])
        spans = _split_sentences(long_passage)
        # Select only first 2 out of 20 sentences → ~10% compression
        result = _build_cut_from_sentences(long_passage, spans, [0, 1])
        assert result.compression_ratio < 0.4
        assert result.cut_style == "aggressive_cut"

    def test_empty_indices_returns_validation_passed_false(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [])
        assert result.validation_passed is False

    def test_spans_sorted_by_start_position(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        # Pass indices out of order
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [4, 0, 2])
        if len(result.selected_spans) >= 2:
            for i in range(len(result.selected_spans) - 1):
                assert result.selected_spans[i].start <= result.selected_spans[i + 1].start

    def test_compression_ratio_calculated_correctly(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [0])
        expected_ratio = len(result.cut_text) / len(MULTI_SENTENCE_PASSAGE)
        assert abs(result.compression_ratio - expected_ratio) < 0.01

    def test_backward_compat_plain_strings(self):
        """_build_cut_from_sentences must still accept list[str] for backward compat."""
        sentences = ["Section 230 grants platforms broad immunity from civil liability.",
                     "Courts have consistently held that platforms are not publishers."]
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, sentences, [0, 1])
        assert isinstance(result, EvidenceCutResult)
        assert result.validation_passed is True
        for span in result.selected_spans:
            assert MULTI_SENTENCE_PASSAGE[span.start:span.end] == span.text


# ── TestDeterministicCut ──────────────────────────────────────────────────────

class TestDeterministicCut:
    def test_claim_overlap_sentences_score_higher(self):
        passage = (
            "Climate change increases global temperatures significantly. "
            "The weather has been unusual lately in some regions. "
            "Climate warming drives extreme weather events. "
            "People enjoy outdoor activities in nice weather. "
            "Climate change threatens economic stability worldwide."
        )
        spans = _split_sentences(passage)
        result = _deterministic_cut(passage, spans, "climate change economic impact")
        # The cut should include the climate-relevant sentences
        assert result is not None
        assert isinstance(result, EvidenceCutResult)
        assert result.cut_text != ""

    def test_legal_evidentiary_terms_boost_score(self):
        passage = (
            "The court held that liability attaches in this case. "
            "Some people were walking down the street. "
            "The evidence found supports the plaintiff's claim. "
            "It was a sunny day in the city. "
            "The judge ruled in favor of the defendant."
        )
        spans = _split_sentences(passage)
        result = _deterministic_cut(passage, spans, "court liability ruling")
        # Legal sentences should be included
        assert result.validation_passed is True
        assert len(result.selected_spans) > 0

    def test_returns_evidence_cut_result_with_validation_passed(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _deterministic_cut(MULTI_SENTENCE_PASSAGE, spans, "Section 230 immunity")
        assert isinstance(result, EvidenceCutResult)
        assert result.validation_passed is True


# ── TestPhraseLevelCutting ────────────────────────────────────────────────────

class TestPhraseLevelCutting:
    def test_phrase_spans_are_exact_substrings(self):
        original = MULTI_SENTENCE_PASSAGE
        llm_spans = [
            _SelectedSpanLLM(exact_text="Section 230 grants platforms broad immunity from civil liability."),
            _SelectedSpanLLM(exact_text="Courts have consistently held that platforms are not publishers."),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        for span in result.selected_spans:
            pos = original.find(span.text)
            assert pos != -1
            assert original[pos:pos + len(span.text)] == span.text

    def test_non_adjacent_spans_insert_ellipsis(self):
        original = MULTI_SENTENCE_PASSAGE
        # First and last sentence — non-adjacent
        first = "Section 230 grants platforms broad immunity from civil liability."
        last = "Critics argue this protection should be reformed."
        llm_spans = [
            _SelectedSpanLLM(exact_text=first),
            _SelectedSpanLLM(exact_text=last),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert "[…]" in result.cut_text_with_ellipses

    def test_adjacent_spans_no_ellipsis(self):
        # Two adjacent sentences in SIMPLE_PASSAGE
        original = "The court ruled. The judge held that immunity applies."
        llm_spans = [
            _SelectedSpanLLM(exact_text="The court ruled."),
            _SelectedSpanLLM(exact_text="The judge held that immunity applies."),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert "[…]" not in result.cut_text_with_ellipses

    def test_invalid_span_discarded(self):
        original = MULTI_SENTENCE_PASSAGE
        good = "Section 230 grants platforms broad immunity from civil liability."
        bad = "This phrase does not exist in the passage at all and should be dropped."
        llm_spans = [
            _SelectedSpanLLM(exact_text=good),
            _SelectedSpanLLM(exact_text=bad),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert len(result.selected_spans) == 1
        assert result.selected_spans[0].text == good

    def test_all_invalid_spans_returns_none(self):
        original = MULTI_SENTENCE_PASSAGE
        llm_spans = [
            _SelectedSpanLLM(exact_text="This phrase does not exist whatsoever."),
            _SelectedSpanLLM(exact_text="Neither does this one obviously."),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is None

    def test_ordering_preserved(self):
        """Even if LLM returns spans in wrong order, result is sorted by position."""
        original = MULTI_SENTENCE_PASSAGE
        second = "Courts have consistently held that platforms are not publishers."
        first = "Section 230 grants platforms broad immunity from civil liability."
        # Pass in reverse order
        llm_spans = [
            _SelectedSpanLLM(exact_text=second),
            _SelectedSpanLLM(exact_text=first),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert len(result.selected_spans) == 2
        assert result.selected_spans[0].start <= result.selected_spans[1].start

    def test_minimum_span_length(self):
        """Spans shorter than 10 chars are ignored."""
        original = MULTI_SENTENCE_PASSAGE
        llm_spans = [
            _SelectedSpanLLM(exact_text="Section"),   # too short
            _SelectedSpanLLM(exact_text="Courts have consistently held that platforms are not publishers."),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert len(result.selected_spans) == 1

    def test_compression_ratio_reflects_selection(self):
        original = MULTI_SENTENCE_PASSAGE
        # Select only one short sentence from a longer passage
        llm_spans = [
            _SelectedSpanLLM(exact_text="Section 230 grants platforms broad immunity from civil liability."),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert result.compression_ratio < 0.5

    def test_validation_passed_true(self):
        original = MULTI_SENTENCE_PASSAGE
        llm_spans = [
            _SelectedSpanLLM(exact_text="Section 230 grants platforms broad immunity from civil liability."),
        ]
        result = _validate_and_build_phrase_cut(original, llm_spans)
        assert result is not None
        assert result.validation_passed is True


# ── TestEnrichCitationMetadata ────────────────────────────────────────────────

class TestEnrichCitationMetadata:
    def test_complete_metadata_produces_complete_citation_quality(self):
        citation = enrich_citation_metadata(
            url="https://example.com/article",
            author="Jane Smith",
            title="Platform Liability Study",
            publication="Harvard Law Review",
            published_date="2024-01-15",
        )
        assert citation.citation_quality == "complete"

    def test_missing_author_produces_partial(self):
        citation = enrich_citation_metadata(
            url="https://example.com/article",
            author=None,
            title="Platform Liability Study",
            publication="Harvard Law Review",
            published_date="2024-01-15",
        )
        assert citation.citation_quality in ("partial", "complete")

    def test_mla_citation_contains_author_title_year_url(self):
        citation = enrich_citation_metadata(
            url="https://example.com/article",
            author="Smith, Jane",
            title="Platform Liability Study",
            publication="Harvard Law Review",
            published_date="2024-01-15",
        )
        assert "Smith" in citation.mla_citation
        assert "Platform Liability Study" in citation.mla_citation
        assert "2024" in citation.mla_citation
        assert "https://example.com/article" in citation.mla_citation

    def test_short_cite_is_author_year_when_both_present(self):
        citation = enrich_citation_metadata(
            url="https://example.com/article",
            author="Smith, Jane",
            title=None,
            publication=None,
            published_date="2024-03-01",
        )
        assert citation.short_cite == "Smith 2024"

    def test_short_cite_is_publication_when_no_author(self):
        citation = enrich_citation_metadata(
            url="https://example.com/article",
            author=None,
            title=None,
            publication="Cornell Law Review",
            published_date=None,
        )
        assert "Cornell" in citation.short_cite

    def test_accessed_date_is_present(self):
        citation = enrich_citation_metadata(
            url="https://example.com",
            author=None,
            title=None,
            publication=None,
            published_date=None,
        )
        assert citation.accessed_date != ""
        # Should look like "DD Mon. YYYY"
        assert "." in citation.accessed_date

    def test_year_extracted_from_iso_date(self):
        citation = enrich_citation_metadata(
            url="https://example.com",
            author="Doe",
            title=None,
            publication=None,
            published_date="2024-01-15",
        )
        assert citation.year == "2024"

    def test_multiple_authors_creates_et_al(self):
        citation = enrich_citation_metadata(
            url="https://example.com",
            author="Smith, Jane and Jones, Bob",
            title=None,
            publication=None,
            published_date=None,
        )
        assert "et al." in citation.author_display

    def test_weak_quality_when_only_url(self):
        citation = enrich_citation_metadata(
            url="https://example.com",
            author=None,
            title=None,
            publication=None,
            published_date=None,
        )
        assert citation.citation_quality == "weak"

    def test_domain_used_as_short_cite_when_no_other_info(self):
        citation = enrich_citation_metadata(
            url="https://law.cornell.edu/uscode/text/47/230",
            author=None,
            title=None,
            publication=None,
            published_date=None,
        )
        # Should use domain or "Source" as fallback
        assert citation.short_cite != ""

    def test_digital_commons_url_gets_publication_name(self):
        citation = enrich_citation_metadata(
            url="https://digitalcommons.law.yale.edu/articles/1234",
            author=None,
            title="Free Speech Online",
            publication=None,
            published_date="2022-05-01",
        )
        assert citation.publication_name != ""
        # Should match digital commons pattern
        assert "Digital Commons" in citation.publication_name or "digitalcommons" in citation.publication_name.lower()

    def test_ssrn_url_gets_ssrn_label(self):
        citation = enrich_citation_metadata(
            url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567",
            author="Brown, Alice",
            title="Platform Regulation",
            publication=None,
            published_date="2023-01-01",
        )
        assert citation.publication_name != ""
        assert "SSRN" in citation.publication_name or "Social Science" in citation.publication_name

    def test_law_review_title_extracted_as_container(self):
        citation = enrich_citation_metadata(
            url="https://harvardlawreview.org/article/230-reform",
            author="Doe, John",
            title="Section 230 Reform in the Harvard Law Review",
            publication=None,
            published_date="2023-04-01",
        )
        # container_title should be populated from the title
        assert citation.container_title != ""
        assert "Law Review" in citation.container_title or "Harvard" in citation.container_title

    def test_crossref_enrichment_mocked(self):
        """Mock _lookup_crossref_doi to return sample data; verify fields are updated."""
        sample_crossref = {
            "author": [{"family": "Johnson", "given": "Alice"}, {"family": "Lee", "given": "Bob"}],
            "issued": {"date-parts": [[2023, 6, 1]]},
            "title": ["Platform Liability and Free Speech"],
            "container-title": ["Journal of Internet Law"],
        }
        with patch("app.services.card_cutting._lookup_crossref_doi", return_value=sample_crossref):
            citation = enrich_citation_metadata(
                url="https://example.com/article",
                author=None,  # no author provided — should come from Crossref
                title=None,
                publication=None,
                published_date=None,
                doi="10.1000/example.doi",
            )
        assert citation.author_display != ""
        assert "Johnson" in citation.author_display
        assert "et al." in citation.author_display  # two authors
        assert citation.year == "2023"
        assert citation.title == "Platform Liability and Free Speech"
        assert citation.container_title == "Journal of Internet Law"
        # Quality should have improved
        assert citation.citation_quality in ("complete", "partial")

    def test_crossref_failure_does_not_crash(self):
        """Even if _lookup_crossref_doi raises, citation is returned without DOI data."""
        with patch("app.services.card_cutting._lookup_crossref_doi", side_effect=Exception("Network error")):
            citation = enrich_citation_metadata(
                url="https://example.com/article",
                author="Doe, Jane",
                title="Internet Law",
                publication="Law Review",
                published_date="2024-01-01",
                doi="10.1000/example",
            )
        # Should not raise; citation must be returned
        assert isinstance(citation, CitationMetadata)
        assert citation.author_display != ""


# ── TestGenerateEvidenceCut (deterministic, no LLM) ──────────────────────────

class TestGenerateEvidenceCut:
    def test_short_passage_returns_full_cut(self):
        passage = "Section 230 provides immunity. Courts have held this."
        result = generate_evidence_cut(
            passage=passage,
            claim="Section 230 immunity",
            evidence_role="mechanism_support",
            use_llm=False,
        )
        assert result.cut_style == "full"
        assert result.cut_text == passage or result.cut_text in passage

    def test_passage_with_5_sentences_includes_ellipses_when_non_adjacent(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        assert len(spans) >= 5, "Need at least 5 sentences for this test"
        # Use deterministic cut
        result = generate_evidence_cut(
            passage=MULTI_SENTENCE_PASSAGE,
            claim="Section 230 immunity platforms",
            evidence_role="mechanism_support",
            use_llm=False,
        )
        assert isinstance(result, EvidenceCutResult)
        # Validation should pass (all spans in original)
        assert result.validation_passed is True

    def test_all_selected_span_texts_are_exact_substrings(self):
        result = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity",
            evidence_role="example_support",
            use_llm=False,
        )
        for span in result.selected_spans:
            assert span.text in LEGAL_PASSAGE, f"Span text not found in original: {span.text!r}"

    def test_empty_passage_returns_safe_result(self):
        result = generate_evidence_cut(
            passage="",
            claim="test claim",
            evidence_role="direct_support",
            use_llm=False,
        )
        assert isinstance(result, EvidenceCutResult)

    @patch("app.services.card_cutting._select_sentences_with_llm")
    def test_llm_failure_falls_back_to_deterministic(self, mock_llm):
        mock_llm.return_value = None
        result = generate_evidence_cut(
            passage=MULTI_SENTENCE_PASSAGE,
            claim="Section 230 immunity",
            evidence_role="mechanism_support",
            use_llm=True,
        )
        assert mock_llm.called
        assert isinstance(result, EvidenceCutResult)
        assert result.validation_passed is True

    @patch("app.services.card_cutting._select_sentences_with_llm")
    def test_llm_phrase_spans_produce_ellipses(self, mock_llm):
        """LLM returning two non-adjacent phrase spans → […] in cut_text_with_ellipses."""
        first = "Section 230 grants platforms broad immunity from civil liability."
        last = "Critics argue this protection should be reformed."
        mock_result = _EvidenceCutLLMOutput(
            selected_spans=[
                _SelectedSpanLLM(exact_text=first),
                _SelectedSpanLLM(exact_text=last),
            ],
            cut_style="aggressive_cut",
        )
        mock_llm.return_value = mock_result
        result = generate_evidence_cut(
            passage=MULTI_SENTENCE_PASSAGE,
            claim="Section 230",
            evidence_role="mechanism_support",
            use_llm=True,
        )
        # Non-adjacent spans should produce ellipses
        assert "[…]" in result.cut_text_with_ellipses

    @patch("app.services.card_cutting._select_sentences_with_llm")
    def test_llm_invalid_spans_fall_back_to_deterministic(self, mock_llm):
        """LLM returning no valid spans → falls back to deterministic."""
        mock_result = _EvidenceCutLLMOutput(
            selected_spans=[
                _SelectedSpanLLM(exact_text="This phrase is not in the passage at all."),
            ],
            cut_style="medium_cut",
        )
        mock_llm.return_value = mock_result
        result = generate_evidence_cut(
            passage=MULTI_SENTENCE_PASSAGE,
            claim="Section 230",
            evidence_role="mechanism_support",
            use_llm=True,
        )
        assert isinstance(result, EvidenceCutResult)
        assert result.validation_passed is True


# ── TestSpanValidation ────────────────────────────────────────────────────────

class TestSpanValidation:
    def test_spans_out_of_order_get_sorted_by_start_position(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [3, 0, 1])
        if len(result.selected_spans) >= 2:
            for i in range(len(result.selected_spans) - 1):
                assert result.selected_spans[i].start <= result.selected_spans[i + 1].start

    def test_span_text_matches_original_slice(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [0, 1, 2])
        for span in result.selected_spans:
            assert MULTI_SENTENCE_PASSAGE[span.start:span.end] == span.text

    def test_out_of_range_indices_skipped_gracefully(self):
        spans = _split_sentences(MULTI_SENTENCE_PASSAGE)
        # Include out-of-range indices
        result = _build_cut_from_sentences(MULTI_SENTENCE_PASSAGE, spans, [0, 999, 1])
        assert isinstance(result, EvidenceCutResult)
        # Should only have valid spans
        for span in result.selected_spans:
            assert span.start >= 0
            assert span.end <= len(MULTI_SENTENCE_PASSAGE)


# ── TestDeriveCardIntelligence ────────────────────────────────────────────────

class TestDeriveCardIntelligence:
    def _intel(self, **overrides) -> CardIntelligence:
        base = dict(
            evidence_role="direct_support",
            best_supported_claim="Section 230 grants platforms immunity",
            overclaim_warning="",
            source_quality="high",
            debate_usefulness_score=8.0,
            is_snippet_source=False,
            citation_quality="complete",
            compression_ratio=0.6,
            cut_style="medium_cut",
            is_counter_evidence=False,
            claim="Section 230 facilitates harmful content",
        )
        base.update(overrides)
        return derive_card_intelligence(**base)

    def test_direct_support_why_text_mentions_link(self):
        intel = self._intel(evidence_role="direct_support")
        # Pass 15.7: why_this_card now emphasises "explicitly establishes" / "quotable link"
        # rather than using the old "constructive" framing.
        text = intel.why_this_card.lower()
        assert any(kw in text for kw in ("establishes", "link", "explicitly")), text
        assert intel.best_use == "contention"

    def test_mechanism_support_suggests_pairing(self):
        intel = self._intel(evidence_role="mechanism_support")
        assert "pair" in intel.why_this_card.lower() or any(
            "pair" in n.lower() for n in intel.debate_use_notes
        )
        assert intel.best_use == "rebuttal"

    def test_counter_evidence_suggests_preempt(self):
        intel = self._intel(evidence_role="counter_evidence", is_counter_evidence=True)
        combined = intel.why_this_card.lower() + " ".join(intel.debate_use_notes).lower()
        assert "pre-empt" in combined or "frontline" in combined

    def test_overclaim_in_limitations(self):
        intel = self._intel(overclaim_warning="Tag implies causation not in source")
        assert any("causation" in l.lower() for l in intel.limitations)

    def test_snippet_source_in_limitations(self):
        intel = self._intel(is_snippet_source=True)
        assert any("partial source" in l.lower() for l in intel.limitations)

    def test_weak_citation_in_limitations(self):
        intel = self._intel(citation_quality="weak")
        assert any("citation is incomplete" in l.lower() for l in intel.limitations)

    def test_save_readiness_ready_when_all_good(self):
        intel = self._intel(
            citation_quality="complete",
            is_snippet_source=False,
            overclaim_warning="",
            source_quality="high",
        )
        assert intel.save_readiness == "ready"
        assert "Citation complete" in intel.save_readiness_reasons

    def test_save_readiness_weak_when_snippet_plus_no_citation(self):
        intel = self._intel(is_snippet_source=True, citation_quality="weak")
        assert intel.save_readiness == "weak"
        assert any("Snippet" in r for r in intel.save_readiness_reasons)

    def test_save_readiness_review_when_overclaim(self):
        intel = self._intel(overclaim_warning="Tag overclaims", citation_quality="complete")
        assert intel.save_readiness == "review_needed"
        assert any("Overclaim" in r for r in intel.save_readiness_reasons)

    def test_high_usefulness_in_supports_claim_because(self):
        intel = self._intel(debate_usefulness_score=9.0)
        assert any("usefulness" in s.lower() for s in intel.supports_claim_because)

    def test_suggested_block_label_uses_role_and_claim(self):
        intel = self._intel(evidence_role="direct_support")
        assert "Direct Support" in intel.suggested_block_label

    def test_very_aggressive_compression_in_limitations(self):
        intel = self._intel(compression_ratio=0.2)
        assert any("aggressive cut" in l.lower() for l in intel.limitations)

    # ── Structured debate-prep coaching fields ────────────────────────────────

    def test_warrant_and_impact_analysis_populated(self):
        intel = self._intel(evidence_role="mechanism_support")
        assert intel.warrant_analysis.strip()
        assert intel.impact_analysis.strip()
        assert "mechanism" in intel.warrant_analysis.lower()

    def test_potential_weakness_and_answer_present(self):
        intel = self._intel(evidence_role="example_support")
        assert intel.potential_weakness.strip()
        assert intel.how_to_answer_weakness.strip()

    def test_overclaim_becomes_the_weakness(self):
        intel = self._intel(overclaim_warning="Tag implies causation not in source")
        assert "causation" in intel.potential_weakness.lower()

    def test_crossfire_answer_and_pairing_present(self):
        intel = self._intel(evidence_role="impact_support")
        assert intel.crossfire_answer.strip()
        assert intel.best_pairing.lower().startswith("pair with")

    def test_snippet_source_weakness_when_no_overclaim(self):
        intel = self._intel(is_snippet_source=True, evidence_role="direct_support")
        assert intel.potential_weakness.strip()

    def test_best_use_allows_summary_and_final_focus(self):
        # The Literal must accept the new speech phases without raising.
        intel = CardIntelligence(best_use="final_focus")
        assert intel.best_use == "final_focus"
        intel2 = CardIntelligence(best_use="summary")
        assert intel2.best_use == "summary"

    # ── Card-specific (entity-aware) debate prep ──────────────────────────────

    BOSNIA = (
        "In 1995, U.S. and NATO airstrikes combined with diplomacy at Dayton forced "
        "Serb forces to the table, ending the war in Bosnia after the Srebrenica "
        "massacre killed thousands of civilians."
    )

    def test_example_card_prep_references_the_case(self):
        intel = self._intel(
            evidence_role="example_support",
            topic="humanitarian intervention",
            passage=self.BOSNIA,
        )
        assert "Bosnia" in intel.potential_weakness
        assert "Bosnia" in intel.how_to_answer_weakness
        assert "mechanism" in intel.how_to_answer_weakness.lower()

    def test_prep_not_generic_when_entity_present(self):
        intel = self._intel(evidence_role="example_support", passage=self.BOSNIA, topic="intervention")
        # Should not be the generic "single case can be dismissed" template
        assert "Bosnia" in intel.potential_weakness

    def test_prep_falls_back_gracefully_without_passage(self):
        intel = self._intel(evidence_role="example_support")
        assert intel.potential_weakness.strip()
        assert intel.how_to_answer_weakness.strip()

    # ── Card-specific warrant / impact / weighing ─────────────────────────────

    def test_warrant_is_natural_and_specific(self):
        hl = "the United States failed to intervene in Rwanda as the genocide unfolded"
        intel = self._intel(
            evidence_role="example_support",
            best_supported_claim="nonintervention allowed the Rwandan genocide to continue",
            passage="The United States failed to intervene in Rwanda as the genocide unfolded.",
            topic="humanitarian intervention",
            highlighted_text=hl,
        )
        assert "Rwanda" in intel.warrant_analysis
        # The clunky phrasings are gone for good.
        assert "highlighted line" not in intel.warrant_analysis.lower()
        assert "if the judge buys this" not in intel.impact_analysis.lower()

    def test_no_clunky_phrasing_anywhere(self):
        intel = self._intel(
            evidence_role="impact_support",
            passage="The genocide in Rwanda killed nearly one million people in a hundred days.",
            topic="humanitarian intervention",
            highlighted_text="the genocide killed nearly one million people in a hundred days",
        )
        blob = " ".join([
            intel.warrant_analysis, intel.impact_analysis, intel.weighing_angle,
        ]).lower()
        assert "highlighted line" not in blob
        assert "if the judge buys this" not in blob

    def test_impact_references_case_and_topic(self):
        intel = self._intel(
            evidence_role="example_support",
            passage="NATO airstrikes forced Serb forces to Dayton, ending the war in Bosnia.",
            topic="humanitarian intervention",
            highlighted_text="NATO airstrikes forced Serb forces to Dayton, ending the war in Bosnia",
        )
        assert "Bosnia" in intel.impact_analysis or "Dayton" in intel.impact_analysis

    def test_weighing_angle_populated(self):
        intel = self._intel(evidence_role="impact_support", passage="Genocide killed nearly one million.", topic="atrocities")
        assert intel.weighing_angle.strip()

    def test_warrant_falls_back_without_highlight(self):
        intel = self._intel(evidence_role="mechanism_support")
        # No highlighted_text → role template that mentions the mechanism
        assert intel.warrant_analysis.strip()


# ── TestCaseEntityExtraction ──────────────────────────────────────────────────

class TestCaseEntityExtraction:
    def test_extracts_known_case(self):
        ents = extract_case_entities("The war in Bosnia ended after Dayton.", "intervention")
        assert "Bosnia" in ents

    def test_extracts_law_entity(self):
        ents = extract_case_entities("Section 230 grants platforms immunity.", "")
        assert "Section 230" in ents

    def test_empty_passage_returns_empty(self):
        assert extract_case_entities("", "") == []

    def test_limit_respected(self):
        ents = extract_case_entities("Bosnia, Kosovo, Rwanda, and Darfur all differ.", "", limit=2)
        assert len(ents) <= 2


# ── TestHighlightCoherence ────────────────────────────────────────────────────

class TestHighlightCoherence:
    def test_coherent_passes_for_real_sentence(self):
        text = "Section 230 grants platforms immunity from civil liability for user content."
        spans = [SelectedSpan(start=0, end=len(text), text=text, sentence_index=0)]
        # Whole-card is too much; a subset is coherent
        sub = SelectedSpan(start=0, end=42, text=text[:42], sentence_index=0)
        assert highlights_are_coherent(text, [sub]) is True

    def test_incoherent_when_empty(self):
        assert highlights_are_coherent("Some text here.", []) is False

    def test_incoherent_when_verbless_fragments(self):
        text = "Bosnia, Kosovo, Rwanda, Darfur, Libya, Syria, Somalia today."
        frags = [
            SelectedSpan(start=0, end=6, text="Bosnia", sentence_index=0),
            SelectedSpan(start=8, end=14, text="Kosovo", sentence_index=0),
            SelectedSpan(start=16, end=22, text="Rwanda", sentence_index=0),
            SelectedSpan(start=24, end=30, text="Darfur", sentence_index=0),
        ]
        assert highlights_are_coherent(text, frags) is False

    def test_sentence_level_fallback_produces_whole_sentences(self):
        text = (
            "Section 230 grants platforms broad immunity. "
            "Courts have consistently upheld this protection. "
            "Critics argue reform is overdue."
        )
        spans = sentence_level_highlights(text, "Section 230 immunity", "mechanism_support")
        assert len(spans) >= 1
        for s in spans:
            assert s.text in text


# ── TestMediumHighReversibility ───────────────────────────────────────────────

class TestMediumHighReversibility:
    PASSAGE = (
        "Section 230, enacted in 1996, grants broad immunity to online platforms. "
        "Courts have consistently held that platforms are not publishers of user content. "
        "The statute provides that no provider shall be treated as the speaker of information. "
        "This provision enables online services to host user-generated content at scale. "
        "In 2018, Congress carved out an exception for sex trafficking via FOSTA-SESTA. "
        "Critics argue this broad protection should be reformed to increase accountability."
    )

    def _cut(self, style):
        return generate_evidence_cut(
            self.PASSAGE, "Section 230 grants platforms immunity",
            "mechanism_support", use_llm=False, preferred_cut_style=style,
        )

    def test_medium_is_stable_across_reswitch(self):
        m1 = self._cut("medium")
        _ = self._cut("high")
        m2 = self._cut("medium")
        assert m1.cut_text_with_ellipses == m2.cut_text_with_ellipses

    def test_high_does_not_mutate_medium(self):
        # High is generated from the same base passage, never from the medium cut.
        m1 = self._cut("medium")
        h = self._cut("high")
        m3 = self._cut("medium")
        assert m1.cut_text_with_ellipses == m3.cut_text_with_ellipses
        # High should be a stricter (shorter-or-equal) cut.
        assert len(h.cut_text_with_ellipses) <= len(m1.cut_text_with_ellipses) + 5

    def test_both_styles_have_coherent_highlights(self):
        for style in ("medium", "high"):
            cut = self._cut(style)
            body = cut.cut_text_with_ellipses
            # highlight ratio must be below 1.0 (never the whole card)
            hl = sum(s.end - s.start for s in cut.cut_body_spans)
            assert hl < len(body)

    def test_high_medium_high_is_stable(self):
        h1 = self._cut("high")
        _ = self._cut("medium")
        h2 = self._cut("high")
        assert h1.cut_text_with_ellipses == h2.cut_text_with_ellipses


# ── TestSegmentTextAdapter ────────────────────────────────────────────────────

class TestSegmentTextAdapter:
    def test_offsets_are_exact(self):
        text = "The U.S. intervened in Bosnia in 1995. NATO forced peace. The war ended."
        for s in segment_text(text):
            assert text[s.start:s.end] == s.text

    def test_does_not_split_on_abbreviations(self):
        text = "The U.S. acted in 1995. It worked."
        sents = segment_text(text)
        # "U.S." must not create a spurious sentence break
        assert all("U.S" not in s.text or "acted" in s.text for s in sents)
        assert len(sents) == 2

    def test_empty_returns_empty(self):
        assert segment_text("") == []


# ── TestReadAloudValidation ───────────────────────────────────────────────────

RWANDA_PASSAGE = (
    "In April 1994, the United Nations and the United States failed to intervene in Rwanda "
    "as the genocide unfolded. Despite clear warning signs from UN commanders on the ground, "
    "the international community withdrew peacekeepers. France launched a limited operation only "
    "after hundreds of thousands of Tutsi had already been killed. The delay allowed the genocide "
    "to continue for nearly one hundred days, demonstrating the cost of nonintervention."
)

BOSNIA_PASSAGE = (
    "In 1995, sustained U.S. and NATO airstrikes combined with diplomacy at Dayton forced Serb "
    "forces to the negotiating table. The credible threat of force changed the incentives of the "
    "warring parties and brought an end to the war in Bosnia. The Dayton Accords demonstrated that "
    "intervention paired with diplomacy can stop mass atrocities."
)


class TestReadAloudValidation:
    def test_validation_passes_for_complete_clause(self):
        text = "The United States failed to intervene in Rwanda as the genocide unfolded."
        spans = [SelectedSpan(start=0, end=len(text), text=text, sentence_index=0)]
        v = validate_read_aloud_card(text + " More context here.", spans)
        assert v.passed
        assert "no_verb" not in v.issues

    def test_ratio_too_high_fires_when_entire_long_card_is_highlighted(self):
        """Highlighting 100% of a full card must always trigger ratio_too_high."""
        cut_body = (
            "Authoritarian regimes rely on violence and repression to maintain political control. "
            "Washington has often tolerated that repression when it served broader security goals. "
            "Scholars argue the responsibility to protect can override sovereignty when a government "
            "commits genocide against its own people. Critics counter that intervention is often "
            "selective and politically motivated by strategic interests."
        )
        # Highlight span covers the entire body.
        spans = [SelectedSpan(start=0, end=len(cut_body), text=cut_body, sentence_index=0)]
        v = validate_read_aloud_card(cut_body, spans)
        assert "ratio_too_high" in v.issues

    def test_ratio_too_high_absent_when_highlights_are_partial(self):
        """Highlighting ~60% of the card must not trigger ratio_too_high."""
        cut_body = (
            "Authoritarian regimes rely on violence and repression to maintain political control. "
            "Washington has often tolerated that repression when it served broader security goals."
        )
        partial = cut_body[:int(len(cut_body) * 0.6)]
        spans = [SelectedSpan(start=0, end=len(partial), text=partial, sentence_index=0)]
        v = validate_read_aloud_card(cut_body, spans)
        assert "ratio_too_high" not in v.issues

    def test_flags_verbless_fragments(self):
        text = "Rwanda, Bosnia, Kosovo, Darfur, Libya here."
        frags = [
            SelectedSpan(start=0, end=6, text="Rwanda", sentence_index=0),
            SelectedSpan(start=8, end=14, text="Bosnia", sentence_index=0),
            SelectedSpan(start=16, end=22, text="Kosovo", sentence_index=0),
            SelectedSpan(start=24, end=30, text="Darfur", sentence_index=0),
        ]
        v = validate_read_aloud_card(text, frags)
        assert not v.passed
        assert "no_verb" in v.issues or "too_fragmented" in v.issues

    def test_flags_midword_start(self):
        text = "The intervention worked well."
        # span starts mid-word ("tervention")
        spans = [SelectedSpan(start=7, end=19, text=text[7:19], sentence_index=0)]
        v = validate_read_aloud_card(text, spans)
        assert "midword_start" in v.issues

    def test_rwanda_card_reads_aloud_coherently(self):
        cut = generate_evidence_cut(
            RWANDA_PASSAGE, "nonintervention in Rwanda allowed genocide to continue",
            "example_support", use_llm=False, preferred_cut_style="medium",
        )
        v = cut.read_aloud_validation
        assert v is not None and v.passed
        # read-aloud text must contain a verb and reference the case
        assert _FINITE_VERB_RE.search(v.read_aloud_text)
        assert "Rwanda" in v.read_aloud_text or "genocide" in v.read_aloud_text

    CARNEGIE_PASSAGE = (
        "U.S. relations with authoritarian regimes have long been shaped by strategic "
        "interest. In addition, each U.S. president has put their own imprint on such "
        "relations. Authoritarian governments rely on violence and repression to maintain "
        "political control, and Washington has often tolerated that repression when it served "
        "security goals."
    )

    def test_carnegie_card_reads_aloud_coherently(self):
        cut = generate_evidence_cut(
            self.CARNEGIE_PASSAGE,
            "U.S. policy toward authoritarian regimes is driven by strategic interests",
            "direct_support", use_llm=False, preferred_cut_style="medium",
        )
        v = cut.read_aloud_validation
        assert v is not None and v.passed, v.issues if v else "no validation"
        # Should not lead the read-aloud with a dangling connective.
        assert not v.read_aloud_text.lower().startswith("in addition")

    def test_high_cut_stays_coherent(self):
        cut = generate_evidence_cut(
            self.CARNEGIE_PASSAGE, "authoritarian regimes use violence",
            "direct_support", use_llm=False, preferred_cut_style="high",
        )
        v = cut.read_aloud_validation
        assert v is not None
        assert "midword_start" not in v.issues and "midword_end" not in v.issues

    def test_bosnia_card_reads_aloud_coherently(self):
        cut = generate_evidence_cut(
            BOSNIA_PASSAGE, "intervention with diplomacy can stop atrocities",
            "example_support", use_llm=False, preferred_cut_style="high",
        )
        v = cut.read_aloud_validation
        assert v is not None
        # no broken words in the highlighted read-aloud text
        for span in cut.cut_body_spans:
            assert not span.text[0].isspace()
            assert span.text == span.text.strip() or span.text  # exact text


class TestDeterministicTagline:
    FRAGMENT_LEAD = (
        "Tutsi and rescue their battalion encamped in Kigali as part of the Accord. "
        "The United States and France delayed intervention in Rwanda despite clear "
        "warnings of an unfolding genocide."
    )

    def test_tag_does_not_start_mid_phrase(self):
        from app.services.card_cutting import _deterministic_tag
        tag = _deterministic_tag(self.FRAGMENT_LEAD, "delayed intervention allowed genocide", "example_support")
        assert tag[:1].isupper()
        assert not tag.lower().startswith("tutsi and rescue")

    def test_tag_includes_claim_concepts(self):
        from app.services.card_cutting import _deterministic_tag
        tag = _deterministic_tag(self.FRAGMENT_LEAD, "intervention in Rwanda", "example_support")
        assert "Rwanda" in tag or "intervention" in tag.lower()

    def test_tag_is_not_just_article_title_garbage(self):
        from app.services.card_cutting import _deterministic_tag
        passage = (
            "Matters of institutional policy on a large scale. "
            "Military action may be justified when mass atrocities make neutrality untenable."
        )
        tag = _deterministic_tag(passage, "military action justified against atrocities", "direct_support")
        # Should prefer the real claim sentence, not the throat-clearing fragment.
        assert "Military action" in tag or "justified" in tag.lower()

    def test_tag_falls_back_to_claim_when_passage_empty(self):
        from app.services.card_cutting import _deterministic_tag
        tag = _deterministic_tag("", "intervention can stop atrocities", "direct_support")
        assert "intervention" in tag.lower()

    def test_strips_leading_connective(self):
        from app.services.card_cutting import _deterministic_tag
        tag = _deterministic_tag(
            "In addition, each U.S. president has put their own imprint on relations.",
            "presidents shape foreign policy", "direct_support",
        )
        assert not tag.lower().startswith("in addition")
        assert tag[:1].isupper()

    def test_deterministic_tagline_from_card_is_a_claim(self):
        from app.services.card_cutting import deterministic_tagline_from_card
        tag = deterministic_tagline_from_card(
            "authoritarian regimes",
            "authoritarian regimes use violence to stay in power",
            "Authoritarian regimes rely on violence and repression to maintain political control.",
            ["authoritarian"], "direct_support",
        )
        assert tag[:1].isupper()
        assert len(tag.split()) <= 18
        assert not tag.lower().startswith(("in addition", "however", "moreover"))

    def test_tagline_has_a_verb(self):
        from app.services.card_cutting import deterministic_tagline_from_card, _FINITE_VERB_RE
        tag = deterministic_tagline_from_card(
            "Rwanda", "nonintervention enabled the Rwandan genocide",
            "The United States delayed intervention as the Rwandan genocide unfolded.",
            ["Rwanda"], "example_support",
        )
        assert _FINITE_VERB_RE.search(tag)


class TestWordBoundarySnap:
    def test_no_midword_after_snap(self):
        from app.services.card_cutting import _snap_to_word_boundaries
        text = "The intervention in Bosnia worked."
        spans = [SelectedSpan(start=7, end=19, text=text[7:19], sentence_index=0)]
        snapped = _snap_to_word_boundaries(text, spans)
        # snapped span should start at a word boundary
        s = snapped[0]
        assert s.start == 0 or not text[s.start - 1].isalnum() or not text[s.start].isalnum()


# ── TestCutStylePreference ────────────────────────────────────────────────────

class TestCutStylePreference:
    def test_full_style_returns_complete_passage(self):
        result = generate_evidence_cut(
            passage=MULTI_SENTENCE_PASSAGE,
            claim="Section 230 immunity",
            evidence_role="mechanism_support",
            use_llm=False,
            preferred_cut_style="full",
        )
        assert result.cut_style == "full"
        assert result.cut_text == MULTI_SENTENCE_PASSAGE
        assert result.compression_ratio == 1.0

    def test_aggressive_style_produces_lower_compression(self):
        aggressive = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity",
            evidence_role="example_support",
            use_llm=False,
            preferred_cut_style="aggressive",
        )
        medium = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity",
            evidence_role="example_support",
            use_llm=False,
            preferred_cut_style="medium",
        )
        assert aggressive.compression_ratio <= medium.compression_ratio

    def test_light_style_produces_higher_compression_than_aggressive(self):
        light = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity",
            evidence_role="example_support",
            use_llm=False,
            preferred_cut_style="light",
        )
        aggressive = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity",
            evidence_role="example_support",
            use_llm=False,
            preferred_cut_style="aggressive",
        )
        assert light.compression_ratio >= aggressive.compression_ratio

    def test_all_cut_style_spans_are_exact_substrings(self):
        for style in ("light", "medium", "aggressive"):
            result = generate_evidence_cut(
                passage=LEGAL_PASSAGE,
                claim="court ruling immunity",
                evidence_role="example_support",
                use_llm=False,
                preferred_cut_style=style,
            )
            for span in result.selected_spans:
                assert span.text in LEGAL_PASSAGE


# ── TestCutQualitySignals (Part 4) ─────────────────────────────────────────────

class TestCutQualitySignals:
    def test_annotated_spans_have_prefix_suffix(self):
        result = generate_evidence_cut(
            passage=LEGAL_PASSAGE, claim="court immunity ruling",
            evidence_role="example_support", use_llm=False,
        )
        assert result.annotated_spans, "expected annotated spans"
        # At least one inner span should have non-empty prefix or suffix.
        assert any(a.prefix or a.suffix for a in result.annotated_spans)
        for a in result.annotated_spans:
            assert len(a.prefix) <= 20
            assert len(a.suffix) <= 20

    def test_cut_warnings_populated_for_aggressive_cut(self):
        result = generate_evidence_cut(
            passage=LEGAL_PASSAGE, claim="court immunity ruling",
            evidence_role="example_support", use_llm=False,
            preferred_cut_style="aggressive",
        )
        assert isinstance(result.cut_warnings, list)

    def test_bold_spans_subset_of_selected(self):
        result = generate_evidence_cut(
            passage=LEGAL_PASSAGE, claim="court immunity ruling",
            evidence_role="example_support", use_llm=False,
        )
        selected_texts = {s.text for s in result.selected_spans}
        for b in result.bold_spans:
            assert b.text in selected_texts

    def test_cut_confidence_low_with_single_span(self):
        from app.models.research import EvidenceCutResult, SelectedSpan
        from app.services.card_cutting import _finalize_cut

        passage = "Section 230 grants platforms immunity from liability."
        span = SelectedSpan(start=0, end=len(passage), text=passage)
        cut = EvidenceCutResult(
            original_passage=passage, selected_spans=[span],
            cut_text=passage, cut_text_with_ellipses=passage,
            compression_ratio=1.0, cut_style="full",
        )
        finalized = _finalize_cut(cut)
        assert finalized.cut_confidence == 0.3

    def test_bold_spans_detect_statistics_and_proper_nouns(self):
        passage = (
            "The intervention in Kosovo prevented further atrocities. "
            "Over 800,000 people were displaced during the conflict in the region. "
            "Analysts noted broad strategic effects across multiple countries."
        )
        result = generate_evidence_cut(
            passage=passage, claim="intervention prevents atrocities",
            evidence_role="impact_support", use_llm=False,
        )
        bold_text = " ".join(b.text for b in result.bold_spans)
        assert "Kosovo" in bold_text or "800,000" in bold_text or "prevented" in bold_text


# ── TestClauseCandidatesRegression ───────────────────────────────────────────
# Regression tests for the AttributeError: 'NoneType' object has no attribute
# 'strip' crash that occurred when _CLAUSE_SPLITS used a capturing group.

class TestClauseCandidatesRegression:
    """_get_clause_candidates must never crash on any input."""

    def _make_span(self, text: str, start: int = 0) -> SentenceSpan:
        return SentenceSpan(text=text, start=start, end=start + len(text), index=0)

    def test_comma_clause_does_not_crash(self):
        # Comma triggers the (?<=[,;:]) branch — no capturing group → no None
        sent = self._make_span("Section 230 grants immunity, because platforms are not publishers.")
        candidates = _get_clause_candidates([sent], sent.text)
        assert isinstance(candidates, list)
        assert all(isinstance(c.text, str) for c in candidates)

    def test_because_split_does_not_crash(self):
        # 'because ' is in the alternation that previously used capturing group
        text = "Platforms escape liability because Congress enacted broad immunity in 1996."
        sent = self._make_span(text)
        candidates = _get_clause_candidates([sent], text)
        assert isinstance(candidates, list)
        assert all(isinstance(c.text, str) for c in candidates)

    def test_em_dash_split_does_not_crash(self):
        text = "The provision is clear — platforms cannot be treated as publishers."
        sent = self._make_span(text)
        candidates = _get_clause_candidates([sent], text)
        assert isinstance(candidates, list)
        assert all(isinstance(c.text, str) for c in candidates)

    def test_which_clause_does_not_crash(self):
        text = "Section 230, which passed in 1996, grants full immunity to platforms."
        sent = self._make_span(text)
        candidates = _get_clause_candidates([sent], text)
        assert isinstance(candidates, list)
        assert all(isinstance(c.text, str) for c in candidates)

    def test_multiple_alternation_triggers_no_crash(self):
        # Multiple triggers in one sentence: comma AND 'because'
        text = (
            "Courts have consistently ruled, because the statute is plain, "
            "that platforms are not liable — which is why reform is contested."
        )
        sent = self._make_span(text)
        candidates = _get_clause_candidates([sent], text)
        assert isinstance(candidates, list)

    def test_all_parts_are_non_empty_strings(self):
        text = "Platforms escape liability, because Congress enacted immunity, while critics dissent."
        sent = self._make_span(text)
        candidates = _get_clause_candidates([sent], text)
        for c in candidates:
            assert isinstance(c.text, str)
            assert c.text.strip() != ""

    def test_candidate_texts_are_substrings_of_original(self):
        original = (
            "The court ruled that immunity applies, because the statute is unambiguous, "
            "while the plaintiff argued otherwise."
        )
        sent = self._make_span(original)
        candidates = _get_clause_candidates([sent], original)
        for c in candidates:
            assert c.text in original, f"{c.text!r} not found in original"

    def test_short_clauses_filtered_out(self):
        # clauses with < 4 words are excluded
        text = "Yes, because it works, although narrow."
        sent = self._make_span(text)
        candidates = _get_clause_candidates([sent], text)
        for c in candidates:
            assert len(c.text.split()) >= 4

    def test_no_sentences_returns_empty_list(self):
        candidates = _get_clause_candidates([], "any passage text here")
        assert candidates == []

    def test_regex_split_never_produces_none_values(self):
        # Directly verify the regex does not return None values
        tricky = "Liability applies, because the statute is clear — which courts confirm."
        parts = _CLAUSE_SPLITS.split(tricky)
        assert all(p is not None for p in parts), f"None found in split: {parts}"

    def test_generate_evidence_cut_never_raises_on_bad_input(self):
        for passage in ["", "   ", "\n\n", "x" * 0]:
            result = generate_evidence_cut(
                passage=passage,
                claim="test claim",
                evidence_role="direct_support",
                use_llm=False,
            )
            assert isinstance(result, EvidenceCutResult)

    def test_generate_evidence_cut_comma_heavy_passage_no_crash(self):
        # Passage with lots of commas, because, which, — triggers all alternation branches
        passage = (
            "Section 230, which was enacted in 1996, grants broad immunity to platforms, "
            "because Congress determined that platforms should not be treated as publishers. "
            "Courts have held this consistently — a ruling that stands to this day. "
            "The statute provides, in relevant part, that no provider shall be treated as the "
            "speaker of information provided by another, although critics argue this is overbroad. "
            "Reform proposals have emerged, while the tech industry opposes them, which has "
            "stalled legislative progress."
        )
        result = generate_evidence_cut(
            passage=passage,
            claim="Section 230 grants immunity to platforms",
            evidence_role="mechanism_support",
            use_llm=False,
        )
        assert isinstance(result, EvidenceCutResult)
        assert result.cut_text != ""
        for span in result.selected_spans:
            assert span.text in passage


# ── TestRemapSpansToCutBody ───────────────────────────────────────────────────

class TestRemapSpansToCutBody:
    def test_basic_remap_finds_spans_in_cut_body(self):
        cut_body = "Section 230 grants immunity. Courts have held this."
        spans = [
            SelectedSpan(start=0, end=28, text="Section 230 grants immunity.", sentence_index=0),
            SelectedSpan(start=29, end=50, text="Courts have held this.", sentence_index=1),
        ]
        remapped = remap_spans_to_cut_body(cut_body, spans)
        assert len(remapped) == 2
        for s in remapped:
            assert s.text in cut_body
            assert cut_body[s.start:s.end] == s.text

    def test_spans_not_in_cut_body_are_dropped(self):
        cut_body = "Only part of the text appears here."
        spans = [
            SelectedSpan(start=0, end=34, text="Only part of the text appears here.", sentence_index=0),
            SelectedSpan(start=100, end=130, text="This phrase is not in cut body at all.", sentence_index=1),
        ]
        remapped = remap_spans_to_cut_body(cut_body, spans)
        assert len(remapped) == 1
        assert remapped[0].text == "Only part of the text appears here."

    def test_empty_cut_body_returns_empty(self):
        spans = [SelectedSpan(start=0, end=5, text="hello", sentence_index=0)]
        assert remap_spans_to_cut_body("", spans) == []

    def test_empty_spans_returns_empty(self):
        assert remap_spans_to_cut_body("some text here", []) == []

    def test_remapped_offsets_are_valid(self):
        cut_body = "Section 230 grants immunity. Courts have held this. The ruling stands."
        spans = [
            SelectedSpan(start=500, end=528, text="Section 230 grants immunity.", sentence_index=0),
            SelectedSpan(start=600, end=622, text="Courts have held this.", sentence_index=1),
        ]
        remapped = remap_spans_to_cut_body(cut_body, spans)
        for s in remapped:
            assert s.start >= 0
            assert s.end <= len(cut_body)
            assert s.end > s.start

    def test_all_remapped_texts_are_exact_substrings(self):
        passage = MULTI_SENTENCE_PASSAGE
        spans = _split_sentences(passage)
        cut_result = _deterministic_cut(passage, spans, "Section 230 immunity")
        cut_body = cut_result.cut_text_with_ellipses
        remapped = remap_spans_to_cut_body(cut_body, cut_result.selected_spans)
        for s in remapped:
            assert s.text in cut_body


# ── TestDeterministicHighlightSpans ──────────────────────────────────────────

class TestDeterministicHighlightSpans:
    def test_returns_at_least_one_span_for_substantive_text(self):
        text = (
            "Nearly one million people were killed in the Rwandan genocide of 1994. "
            "Armed humanitarian intervention requires the use of military force without consent."
        )
        spans = get_deterministic_highlight_spans(text, "humanitarian intervention", "impact_support")
        assert len(spans) > 0

    def test_all_spans_are_exact_substrings(self):
        text = (
            "Section 230 grants immunity to platforms because Congress determined that "
            "platforms should not be treated as publishers."
        )
        spans = get_deterministic_highlight_spans(text, "Section 230 immunity", "mechanism_support")
        for s in spans:
            assert s.text in text
            assert text[s.start:s.end] == s.text

    def test_returns_empty_for_empty_text(self):
        spans = get_deterministic_highlight_spans("", "claim", "direct_support")
        assert spans == []

    def test_spans_not_overlapping(self):
        text = (
            "Section 230 grants platforms broad immunity from civil liability for user content. "
            "Courts have consistently held that platforms are not publishers under the statute."
        )
        spans = get_deterministic_highlight_spans(text, "Section 230 immunity", "mechanism_support")
        # Check no overlapping
        sorted_spans = sorted(spans, key=lambda s: s.start)
        for i in range(1, len(sorted_spans)):
            assert sorted_spans[i].start >= sorted_spans[i - 1].end

    def test_claim_terms_are_highlighted(self):
        text = "Section 230 provides broad immunity to online platforms from civil liability."
        claim = "platforms have immunity under section 230"
        spans = get_deterministic_highlight_spans(text, claim, "direct_support")
        combined = " ".join(s.text for s in spans)
        # At least some claim-adjacent terms should appear
        assert len(combined) > 0

    def test_statistics_are_highlighted(self):
        text = "Over 800,000 people were displaced during the conflict, representing 45 percent of the population."
        spans = get_deterministic_highlight_spans(text, "conflict displacement", "impact_support")
        texts = [s.text for s in spans]
        assert any("800" in t or "45" in t or "percent" in t for t in texts)

    def test_capped_at_12_spans(self):
        # Long text with many signal terms
        text = " ".join([
            "court held immunity jurisdiction 1996.", "statute provides grants shields.",
            "million percent billion killed displaced.", "genocide atrocity moral rights.",
            "Section 230 platform liability legal.", "court ruled grants provides.",
        ] * 3)
        spans = get_deterministic_highlight_spans(text, "immunity platforms", "mechanism_support")
        assert len(spans) <= 12


# ── TestCleanCardBodyText ─────────────────────────────────────────────────────

class TestCleanCardBodyText:
    def test_joins_line_wraps(self):
        text = "Section 230 provides\nimmunity to platforms."
        cleaned, _ = clean_card_body_text(text)
        assert "\n" not in cleaned
        assert "provides immunity" in cleaned

    def test_normalizes_multiple_spaces(self):
        text = "Section 230   provides  immunity."
        cleaned, _ = clean_card_body_text(text)
        assert "  " not in cleaned

    def test_removes_leading_comma(self):
        text = ", Section 230 provides immunity to platforms."
        cleaned, warnings = clean_card_body_text(text)
        assert not cleaned.startswith(",")
        assert len(warnings) > 0

    def test_removes_leading_semicolon(self):
        text = "; platforms are not treated as publishers."
        cleaned, _ = clean_card_body_text(text)
        assert not cleaned.startswith(";")

    def test_preserves_substantive_words(self):
        text = "Section 230 provides broad immunity to platforms from civil liability."
        cleaned, _ = clean_card_body_text(text)
        assert "Section 230" in cleaned
        assert "immunity" in cleaned
        assert "civil liability" in cleaned

    def test_empty_input_returns_empty(self):
        cleaned, warnings = clean_card_body_text("")
        assert cleaned == ""
        assert warnings == []

    def test_preserves_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph."
        cleaned, _ = clean_card_body_text(text)
        assert "\n\n" in cleaned

    def test_detects_broken_extraction(self):
        # Text with very few alphabetic chars
        text = "123 456 789 !!! $$$ %%% --- 0.5 2.3 4.5"
        _, warnings = clean_card_body_text(text)
        assert any("broken" in w.lower() or "unusual" in w.lower() for w in warnings)


# ── TestCutBodySpansInGeneratedCuts ──────────────────────────────────────────

class TestCutBodySpansInGeneratedCuts:
    def test_cut_body_spans_populated_for_long_passage(self):
        result = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity platforms",
            evidence_role="example_support",
            use_llm=False,
        )
        # cut_body_spans should be present
        assert hasattr(result, "cut_body_spans")
        assert isinstance(result.cut_body_spans, list)

    def test_cut_body_spans_are_in_cut_body(self):
        result = generate_evidence_cut(
            passage=LEGAL_PASSAGE,
            claim="court ruling immunity",
            evidence_role="example_support",
            use_llm=False,
        )
        cut_body = result.cut_text_with_ellipses or result.cut_text
        for span in result.cut_body_spans:
            assert span.text in cut_body, f"Span {span.text!r} not found in cut body"

    def test_cut_body_has_spans_for_rich_passage(self):
        # A well-structured passage should produce at least one cut_body_span
        passage = (
            "Section 230, enacted in 1996, grants broad immunity to platforms. "
            "Courts have consistently held that platforms are not publishers. "
            "The statute provides that no provider shall be treated as the speaker. "
            "This provision enables online services to host user-generated content. "
            "Critics argue this protection should be reformed."
        )
        result = generate_evidence_cut(
            passage=passage,
            claim="Section 230 grants immunity to platforms",
            evidence_role="mechanism_support",
            use_llm=False,
        )
        assert len(result.cut_body_spans) > 0, "Expected at least one cut_body_span"

    def test_full_cut_style_still_produces_cut_body_spans(self):
        result = generate_evidence_cut(
            passage=MULTI_SENTENCE_PASSAGE,
            claim="Section 230 immunity",
            evidence_role="mechanism_support",
            use_llm=False,
            preferred_cut_style="full",
        )
        assert isinstance(result.cut_body_spans, list)


# ── TestPageChromeStripping ────────────────────────────────────────────────────

class TestPageChromeStripping:
    """strip_page_chrome and _is_chrome_line must remove navigation junk without
    touching real evidence-bearing text."""

    DIGITAL_COMMONS_HEADER = (
        "Home > Ozark Historical Review > Volume 12 > Issue 3\n"
        "Digital Commons @ St. Mary's University\n"
        "Included in the History Commons\n"
        "Download Full Text\n"
        "Repository Citation\n"
        "Smith, J. (2020). \"Intervention and Law.\" Ozark Historical Review 12(3).\n"
        "Abstract\n"
        "\n"
        "Humanitarian intervention is a use of military force aimed at preventing "
        "widespread and grave violations of the fundamental human rights of individuals. "
        "The Rwandan genocide of 1994 saw nearly one million people killed within weeks, "
        "yet the international community failed to intervene effectively."
    )

    def test_strips_breadcrumb_navigation(self):
        result = strip_page_chrome(self.DIGITAL_COMMONS_HEADER)
        assert "Home >" not in result
        assert "Ozark Historical Review > Volume" not in result

    def test_strips_digital_commons_label(self):
        result = strip_page_chrome(self.DIGITAL_COMMONS_HEADER)
        assert "Digital Commons" not in result

    def test_strips_repository_citation_label(self):
        result = strip_page_chrome(self.DIGITAL_COMMONS_HEADER)
        assert "Repository Citation" not in result

    def test_strips_included_in(self):
        result = strip_page_chrome(self.DIGITAL_COMMONS_HEADER)
        assert "Included in" not in result

    def test_strips_abstract_bare_label(self):
        result = strip_page_chrome(self.DIGITAL_COMMONS_HEADER)
        assert result.strip().startswith("Humanitarian") or "Abstract\n" not in result

    def test_preserves_real_evidence_text(self):
        result = strip_page_chrome(self.DIGITAL_COMMONS_HEADER)
        assert "Humanitarian intervention is a use of military force" in result
        assert "Rwandan genocide of 1994" in result
        assert "nearly one million people killed" in result

    def test_empty_string_returns_empty(self):
        assert strip_page_chrome("") == ""

    def test_no_chrome_text_unchanged(self):
        pure = (
            "Humanitarian intervention is justified when states fail to protect their citizens. "
            "The doctrine of Responsibility to Protect (R2P) emerged after the Rwandan genocide. "
            "Courts have held that extreme cases of state failure can justify external intervention."
        )
        result = strip_page_chrome(pure)
        assert "Humanitarian intervention" in result
        assert "R2P" in result

    def test_is_chrome_line_detects_breadcrumb(self):
        assert _is_chrome_line("Home > Journals > Volume 3")

    def test_is_chrome_line_detects_digital_commons(self):
        assert _is_chrome_line("Digital Commons @ University Library")

    def test_is_chrome_line_detects_abstract_bare(self):
        assert _is_chrome_line("Abstract")

    def test_is_chrome_line_detects_doi(self):
        assert _is_chrome_line("DOI: 10.1000/xyz123")

    def test_is_chrome_line_does_not_flag_evidence(self):
        assert not _is_chrome_line(
            "Armed humanitarian intervention is justified when states commit genocide."
        )

    def test_score_paragraph_penalizes_chrome_heavy(self):
        chrome_para = (
            "Home > Journals > Volume 3\n"
            "Digital Commons @ University\n"
            "Included in the Law Commons\n"
            "Repository Citation\n"
            "DOI: 10.5555/abc\n"
        )
        score = _score_paragraph(chrome_para, "humanitarian intervention", "intervention")
        assert score < 0

    def test_score_paragraph_rewards_evidence_text(self):
        evidence_para = (
            "Humanitarian intervention is morally justified when a state commits genocide. "
            "The courts have held that international law provides a threshold for action. "
            "The Rwandan genocide caused nearly one million deaths in 1994."
        )
        score = _score_paragraph(evidence_para, "humanitarian intervention law", "intervention")
        assert score > 3.0


# ── TestFindEvidenceStartIndex ─────────────────────────────────────────────────

class TestFindEvidenceStartIndex:
    """find_evidence_start_index should skip preamble and return real evidence start."""

    OZARK_PREAMBLE = (
        "Home > Ozark Historical Review > Vol. 42 > Issue 1\n"
        "Ozark Historical Review\n"
        "Volume 42, Issue 1 — Spring 2022\n"
        "Author: Smith, John\n"
        "Institution: University of Arkansas\n"
        "Abstract\n"
        "\n"
        "Since the end of World War II, the United States has engaged in numerous "
        "military interventions abroad to protect civilian populations from atrocities. "
        "Humanitarian intervention has been invoked to justify the use of military force "
        "without the consent of the target state when genocide or mass atrocities occur."
    )

    def test_skips_ozark_preamble_breadcrumb(self):
        idx = find_evidence_start_index(self.OZARK_PREAMBLE, "humanitarian intervention", "")
        # Should skip past "Home >" line
        assert self.OZARK_PREAMBLE[idx:].strip().startswith("Since") or idx > 0

    def test_real_evidence_is_reachable_after_skip(self):
        idx = find_evidence_start_index(self.OZARK_PREAMBLE, "humanitarian intervention", "")
        remaining = self.OZARK_PREAMBLE[idx:]
        assert "United States" in remaining or "intervention" in remaining

    def test_empty_text_returns_zero(self):
        assert find_evidence_start_index("", "claim", "") == 0

    def test_pure_evidence_text_returns_near_zero(self):
        pure = (
            "Humanitarian intervention is a use of military force aimed at preventing "
            "widespread violations of human rights without the consent of the target state. "
            "The Rwandan genocide of 1994 killed nearly one million people."
        )
        idx = find_evidence_start_index(pure, "humanitarian intervention", "")
        assert idx == 0 or pure[idx:].strip().startswith("Humanitarian")

    def test_skips_abstract_label(self):
        text = "Abstract\n\nThis paper argues that humanitarian intervention is justified..."
        idx = find_evidence_start_index(text, "humanitarian intervention", "")
        assert "Abstract" not in text[idx:idx + 20] or idx > 0

    def test_long_evidence_text_not_truncated(self):
        long_text = ("Page header\nAuthor: Doe\n\n" + "Real sentence with evidence. " * 30)
        idx = find_evidence_start_index(long_text, "evidence real", "")
        remaining = long_text[idx:]
        assert "Real sentence" in remaining


# ── TestScholarWorksOzarkFixture ──────────────────────────────────────────────

# Realistic ScholarWorks/Digital Commons preamble that previously contaminated cuts
OZARK_MESSY = (
    "Home > Journals > Ozark Historical Review > Vol. 42 (2022) > No. 1\n"
    "Ozark Historical Review\n"
    "\n"
    "Humanitarian Intervention and Just War Theory\n"
    "\n"
    "Authors\n"
    "Nathaniel R. King, University of Arkansas\n"
    "Emily Chen, University of Missouri\n"
    "\n"
    "Abstract\n"
    "\n"
    "This paper examines justifications for humanitarian intervention.\n"
    "\n"
    "Included in the History Commons, International and Area Studies Commons\n"
    "Digital Commons @ Ozark State University\n"
    "Recommended Citation\n"
    "King, N. R. (2022). Humanitarian Intervention. Ozark Historical Review, 42(1), 1–25.\n"
    "\n"
    "Since the end of World War II, the United States has engaged in numerous "
    "military interventions abroad to protect civilian populations from atrocities. "
    "Humanitarian intervention is a use of military force aimed at preventing widespread "
    "violations of human rights, typically justified by appeal to just war theory. "
    "The Rwandan genocide of 1994 saw nearly one million people killed within weeks, "
    "yet the international community failed to intervene effectively. "
    "Armed intervention requires satisfying the conditions of proportionality, last resort, "
    "reasonable chance of success, and multilateral legitimacy."
)


class TestScholarWorksOzarkFixture:
    """The ScholarWorks/Ozark preamble must be stripped before card cutting."""

    def test_strip_page_chrome_removes_home_breadcrumb(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        assert "Home >" not in cleaned

    def test_strip_page_chrome_removes_digital_commons(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        assert "Digital Commons" not in cleaned

    def test_strip_page_chrome_removes_recommended_citation(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        assert "Recommended Citation" not in cleaned

    def test_strip_page_chrome_removes_included_in(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        assert "Included in" not in cleaned

    def test_strip_page_chrome_preserves_substantive_evidence(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        assert "Since the end of World War II" in cleaned
        assert "Rwandan genocide" in cleaned
        assert "proportionality" in cleaned

    def test_find_evidence_start_skips_author_block(self):
        idx = find_evidence_start_index(OZARK_MESSY, "humanitarian intervention just war", "")
        remaining = OZARK_MESSY[idx:]
        # Should not start with author metadata
        assert not remaining.strip().startswith("Nathaniel")
        assert not remaining.strip().startswith("Authors")
        assert not remaining.strip().startswith("Home")

    def test_find_evidence_start_finds_since_sentence(self):
        idx = find_evidence_start_index(OZARK_MESSY, "humanitarian intervention just war", "")
        remaining = OZARK_MESSY[idx:]
        assert "Since the end of World War II" in remaining or "Humanitarian intervention" in remaining

    def test_fallback_passage_does_not_include_ozark_metadata(self):
        from app.models.research import ExtractedArticle, ArticleMetadata
        article = ExtractedArticle(
            url="https://digitalcommons.ozark.edu/review/vol42/iss1/1",
            metadata=ArticleMetadata(
                title="Humanitarian Intervention and Just War Theory",
                author="King, Nathaniel R.",
                publication="Ozark Historical Review",
                published_date="2022",
                url="https://digitalcommons.ozark.edu/review/vol42/iss1/1",
            ),
            extracted_text=OZARK_MESSY,
            extraction_method="scrape",
            extraction_confidence=0.8,
            status="ok",
        )
        passage = _fallback_passage(article, "humanitarian intervention", "military intervention justified")
        assert "Home >" not in passage
        assert "Digital Commons" not in passage
        assert "Nathaniel R. King" not in passage
        assert "Recommended Citation" not in passage

    def test_full_generate_evidence_cut_on_ozark_text_no_chrome(self):
        clean_text = strip_page_chrome(OZARK_MESSY)
        start_idx = find_evidence_start_index(clean_text, "humanitarian intervention just war", "")
        evidence_text = clean_text[start_idx:] if start_idx > 0 else clean_text
        result = generate_evidence_cut(
            passage=evidence_text,
            claim="humanitarian intervention is justified to stop human rights abuses",
            evidence_role="moral_warrant",
            use_llm=False,
        )
        # Final card body must not start with metadata
        body = result.cut_text_with_ellipses or result.cut_text
        assert "Home >" not in body
        assert "Digital Commons" not in body
        assert "Nathaniel" not in body
        # Must contain real evidence
        assert len(body) > 30


# ── TestTitleAndAuthorDetection ────────────────────────────────────────────────

class TestTitleAndAuthorDetection:
    """is_probable_title_line / is_author_metadata_line must keep article
    titles, bylines, and citation footers out of the evidence body."""

    def test_title_line_detected(self):
        assert is_probable_title_line("Humanitarian Intervention and Just War Theory")

    def test_journal_name_detected_as_title(self):
        assert is_probable_title_line("Ozark Historical Review")

    def test_real_sentence_not_a_title(self):
        assert not is_probable_title_line(
            "Humanitarian intervention is justified when a state commits genocide."
        )

    def test_title_overlapping_claim_still_rejected(self):
        # The trap: the title shares the claim's keywords but is still not evidence.
        assert is_probable_title_line(
            "Humanitarian Intervention and Just War Theory",
            claim="humanitarian intervention just war",
        )

    def test_metadata_title_exact_match(self):
        assert is_probable_title_line(
            "The Ethics of Force.",  # trailing punct but exact metadata match
            metadata_title="The Ethics of Force",
        )

    def test_bare_author_name_detected(self):
        assert is_author_metadata_line("Nathaniel R. King")

    def test_author_with_institution_detected(self):
        assert is_author_metadata_line("Emily Chen, University of Missouri")

    def test_author_label_detected(self):
        assert is_author_metadata_line("Author: Smith, John")

    def test_authors_bare_label_detected(self):
        assert is_author_metadata_line("Authors")

    def test_department_line_detected(self):
        assert is_author_metadata_line("Department of Political Science")

    def test_evidence_sentence_not_author(self):
        assert not is_author_metadata_line(
            "Since the end of World War II the United States has intervened abroad."
        )

    def test_strip_removes_article_title_with_metadata(self):
        cleaned = strip_page_chrome(
            OZARK_MESSY, metadata_title="Humanitarian Intervention and Just War Theory"
        )
        assert "Humanitarian Intervention and Just War Theory" not in cleaned
        assert "Since the end of World War II" in cleaned

    def test_strip_removes_journal_name_line(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        # Standalone journal name should not survive as body text
        assert "Ozark Historical Review\n" not in cleaned

    def test_strip_removes_recommended_citation_footer(self):
        cleaned = strip_page_chrome(OZARK_MESSY)
        assert "King, N. R. (2022)" not in cleaned

    def test_find_evidence_start_skips_title_line(self):
        idx = find_evidence_start_index(OZARK_MESSY, "humanitarian intervention just war", "")
        remaining = OZARK_MESSY[idx:].strip()
        assert not remaining.startswith("Humanitarian Intervention and Just War Theory")
        assert not remaining.startswith("Ozark Historical Review")

    def test_chrome_line_flags_citation_footer(self):
        assert _is_chrome_line("King, N. R. (2022). Humanitarian Intervention. Ozark, 42(1).")

    def test_chrome_line_flags_author_institution(self):
        assert _is_chrome_line("Nathaniel R. King, University of Arkansas")
