"""Tests for the deterministic delivery analysis service."""

import pytest

from app.services.delivery_analysis import (
    analyze_delivery,
    _count_fillers,
    _find_repeated_phrases,
    _analyze_sentences,
    _pacing_band,
    _compute_delivery_score,
    _compute_clarity_flags,
    _build_timeline,
    WPM_TOO_SLOW,
    WPM_TOO_FAST,
    FILLER_RATE_MEDIUM,
    VERY_SHORT_SPEECH_WORDS,
    TIMELINE_CHUNKS,
)


# ── _count_fillers ─────────────────────────────────────────────────────────────

class TestCountFillers:
    def test_single_word_fillers(self):
        total, breakdown = _count_fillers("Um, I think that, uh, we need to")
        assert breakdown.get("um", 0) == 1
        assert breakdown.get("uh", 0) == 1
        assert total >= 2

    def test_multi_word_filler_not_double_counted(self):
        total, breakdown = _count_fillers("you know, that's the thing you know")
        # "you know" appears twice — should count as 2 not 4 individual words
        assert breakdown.get("you know", 0) == 2
        # "you" alone should not appear
        assert breakdown.get("you", 0) == 0

    def test_kind_of_phrase(self):
        total, breakdown = _count_fillers("it's kind of like the thing")
        assert breakdown.get("kind of", 0) == 1

    def test_sort_of_phrase(self):
        total, breakdown = _count_fillers("it's sort of what we mean")
        assert breakdown.get("sort of", 0) == 1

    def test_like_as_filler(self):
        total, breakdown = _count_fillers("I like go to the thing like every day")
        assert breakdown.get("like", 0) >= 1

    def test_no_fillers(self):
        total, breakdown = _count_fillers("The United States ought to prioritize economic security.")
        assert total == 0
        assert breakdown == {}

    def test_empty_text(self):
        total, breakdown = _count_fillers("")
        assert total == 0
        assert breakdown == {}

    def test_so_as_filler(self):
        total, breakdown = _count_fillers("So we can see that so the evidence says")
        # "so" should be counted
        assert breakdown.get("so", 0) >= 1


# ── _find_repeated_phrases ─────────────────────────────────────────────────────

class TestFindRepeatedPhrases:
    def test_repeated_phrase_detected(self):
        text = "the economic impact is great. the economic impact matters. the economic impact outweighs."
        phrases = _find_repeated_phrases(text)
        phrase_texts = [p["phrase"] for p in phrases]
        assert any("economic impact" in p for p in phrase_texts)

    def test_phrase_below_threshold_not_returned(self):
        text = "we argue that economic growth is real. economic growth is good."
        phrases = _find_repeated_phrases(text)
        # only 2 occurrences — below threshold of 3
        phrase_texts = [p["phrase"] for p in phrases]
        assert "economic growth" not in phrase_texts

    def test_stop_phrases_excluded(self):
        text = "in the morning in the afternoon in the evening we work"
        phrases = _find_repeated_phrases(text)
        phrase_texts = [p["phrase"] for p in phrases]
        # "in the" is a stop phrase and should not be returned
        assert "in the" not in phrase_texts

    def test_empty_text(self):
        assert _find_repeated_phrases("") == []

    def test_short_text(self):
        assert _find_repeated_phrases("hi") == []


# ── _analyze_sentences ─────────────────────────────────────────────────────────

class TestAnalyzeSentences:
    def test_single_short_sentence(self):
        total, long_count, avg = _analyze_sentences("The warrant is strong.")
        assert total == 1
        assert long_count == 0
        assert avg > 0

    def test_long_sentence_detected(self):
        # 40+ words in one sentence
        text = (
            "The economic contention demonstrates that the continued growth of international "
            "trade partnerships under the resolution creates sustainable development in emerging "
            "markets which ultimately leads to reduced systemic poverty and better living standards globally."
        )
        total, long_count, avg = _analyze_sentences(text)
        assert long_count >= 1

    def test_multiple_sentences(self):
        text = "First sentence. Second sentence! Third sentence?"
        total, long_count, avg = _analyze_sentences(text)
        assert total == 3

    def test_empty_text(self):
        total, long_count, avg = _analyze_sentences("")
        assert total == 0
        assert avg == 0.0


# ── _pacing_band ──────────────────────────────────────────────────────────────

class TestPacingBand:
    def test_too_slow(self):
        assert _pacing_band(80) == "too_slow"

    def test_edge_too_slow(self):
        assert _pacing_band(WPM_TOO_SLOW - 1) == "too_slow"

    def test_steady_low_edge(self):
        assert _pacing_band(WPM_TOO_SLOW) == "steady"

    def test_steady_high_edge(self):
        assert _pacing_band(WPM_TOO_FAST) == "steady"

    def test_too_fast(self):
        assert _pacing_band(WPM_TOO_FAST + 1) == "too_fast"

    def test_no_wpm(self):
        assert _pacing_band(None) == "unknown"


# ── _compute_delivery_score ────────────────────────────────────────────────────

class TestComputeDeliveryScore:
    def test_perfect_delivery(self):
        score = _compute_delivery_score(
            word_count=200,
            wpm=150.0,
            filler_count=0,
            repeated_phrases=[],
            long_sentence_count=0,
            total_sentences=10,
        )
        assert score == 100

    def test_score_very_low_with_many_issues(self):
        score = _compute_delivery_score(
            word_count=30,    # short speech penalty
            wpm=250.0,        # way too fast
            filler_count=20,  # many fillers
            repeated_phrases=[{"phrase": "x", "count": 3}] * 5,
            long_sentence_count=5,
            total_sentences=5,
        )
        # Many stacked penalties → score should be very low (below 25)
        assert score <= 25

    def test_score_clamped_to_100_maximum(self):
        score = _compute_delivery_score(
            word_count=300,
            wpm=155.0,
            filler_count=0,
            repeated_phrases=[],
            long_sentence_count=0,
            total_sentences=15,
        )
        assert score == 100

    def test_fast_pacing_penalized(self):
        score_fast = _compute_delivery_score(200, 210.0, 0, [], 0, 10)
        score_ideal = _compute_delivery_score(200, 150.0, 0, [], 0, 10)
        assert score_fast < score_ideal

    def test_high_filler_rate_penalized(self):
        score_fillers = _compute_delivery_score(100, 150.0, 15, [], 0, 10)
        score_clean = _compute_delivery_score(100, 150.0, 0, [], 0, 10)
        assert score_fillers < score_clean

    def test_very_short_speech_penalized(self):
        score_short = _compute_delivery_score(40, 150.0, 0, [], 0, 5)
        score_normal = _compute_delivery_score(200, 150.0, 0, [], 0, 10)
        assert score_short < score_normal

    def test_unknown_wpm_no_pacing_penalty(self):
        score_no_wpm = _compute_delivery_score(200, None, 0, [], 0, 10)
        assert score_no_wpm == 100


# ── _compute_clarity_flags ─────────────────────────────────────────────────────

class TestComputeClarityFlags:
    def test_too_fast_flag(self):
        flags = _compute_clarity_flags(200, 190.0, 0, [], 0, 10)
        assert "too_fast" in flags

    def test_too_slow_flag(self):
        flags = _compute_clarity_flags(200, 90.0, 0, [], 0, 10)
        assert "too_slow" in flags

    def test_many_fillers_flag(self):
        flags = _compute_clarity_flags(100, 150.0, 10, [], 0, 10)
        assert "many_fillers" in flags

    def test_repetitive_wording_flag(self):
        phrases = [{"phrase": "x", "count": 5}, {"phrase": "y", "count": 4}]
        flags = _compute_clarity_flags(200, 150.0, 0, phrases, 0, 10)
        assert "repetitive_wording" in flags

    def test_long_sentences_flag(self):
        flags = _compute_clarity_flags(200, 150.0, 0, [], 6, 10)
        assert "long_sentences" in flags

    def test_very_short_speech_flag(self):
        flags = _compute_clarity_flags(50, 150.0, 0, [], 0, 5)
        assert "very_short_speech" in flags

    def test_clean_delivery_no_flags(self):
        flags = _compute_clarity_flags(200, 150.0, 1, [], 1, 15)
        assert flags == []


# ── _build_timeline ────────────────────────────────────────────────────────────

class TestBuildTimeline:
    def test_returns_timeline_chunks(self):
        text = " ".join(["word"] * 100)
        timeline = _build_timeline(text, 100, 60, {}, [])
        assert len(timeline) == TIMELINE_CHUNKS

    def test_timestamps_computed_with_duration(self):
        text = " ".join(["word"] * 100)
        timeline = _build_timeline(text, 100, 60, {}, [])
        # First segment should start at 0
        assert timeline[0]["approx_start_seconds"] == 0.0
        # Last segment should end at 60 (± rounding)
        assert timeline[-1]["approx_end_seconds"] <= 60.0

    def test_no_timestamps_without_duration(self):
        text = " ".join(["word"] * 100)
        timeline = _build_timeline(text, 100, None, {}, [])
        for seg in timeline:
            assert seg["approx_start_seconds"] is None
            assert seg["approx_end_seconds"] is None

    def test_filler_flagged_in_segment(self):
        # Put many fillers in first 20 words
        filler_words = " ".join(["um"] * 20)
        content_words = " ".join(["word"] * 80)
        text = filler_words + " " + content_words
        timeline = _build_timeline(text, 100, None, {"um": 20}, [])
        assert "high_fillers" in timeline[0]["flags"]

    def test_empty_text_returns_empty(self):
        timeline = _build_timeline("", 0, None, {}, [])
        assert timeline == []


# ── analyze_delivery (integration) ────────────────────────────────────────────

class TestAnalyzeDelivery:
    SAMPLE_TEXT = (
        "The economic growth contention demonstrates that trade liberalization reduces poverty. "
        "Um, the warrant here is that, uh, when tariffs are lowered, you know, market access increases. "
        "So, basically, the impact is significant. Economic growth economic growth economic growth. "
        "This is a very important point that we need to address because the evidence shows clearly "
        "that international trade is essential for developing nations and emerging economies worldwide."
    )

    def test_returns_delivery_metrics_result(self):
        result = analyze_delivery(self.SAMPLE_TEXT, duration_seconds=30)
        assert result.word_count > 0
        assert result.delivery_score >= 0
        assert result.delivery_score <= 100

    def test_word_count_matches_text(self):
        result = analyze_delivery(self.SAMPLE_TEXT, duration_seconds=30)
        expected = len(self.SAMPLE_TEXT.split())
        assert result.word_count == expected

    def test_wpm_computed_with_duration(self):
        result = analyze_delivery("one two three four five six seven eight nine ten", duration_seconds=10)
        # 10 words in 10 seconds → 60 WPM
        assert result.words_per_minute == pytest.approx(60.0, rel=0.01)

    def test_wpm_none_without_duration(self):
        result = analyze_delivery(self.SAMPLE_TEXT)
        assert result.words_per_minute is None
        assert result.pacing_band == "unknown"

    def test_filler_detection_in_sample(self):
        result = analyze_delivery(self.SAMPLE_TEXT)
        assert result.filler_word_count > 0

    def test_pacing_band_too_fast(self):
        # 200 words in 30 seconds = 400 WPM → too_fast
        text = " ".join(["word"] * 200)
        result = analyze_delivery(text, duration_seconds=30)
        assert result.pacing_band == "too_fast"

    def test_pacing_band_too_slow(self):
        # 50 words in 60 seconds = 50 WPM → too_slow
        text = " ".join(["word"] * 50)
        result = analyze_delivery(text, duration_seconds=60)
        assert result.pacing_band == "too_slow"

    def test_pacing_band_steady(self):
        # 150 words in 60 seconds = 150 WPM → steady
        text = " ".join(["word"] * 150)
        result = analyze_delivery(text, duration_seconds=60)
        assert result.pacing_band == "steady"

    def test_timeline_has_chunks(self):
        result = analyze_delivery(self.SAMPLE_TEXT)
        assert len(result.timeline_json) == TIMELINE_CHUNKS

    def test_empty_transcript(self):
        result = analyze_delivery("")
        assert result.word_count == 0
        assert result.filler_word_count == 0
        assert result.delivery_score >= 0

    def test_repeated_phrases_detected(self):
        result = analyze_delivery(self.SAMPLE_TEXT)
        # "economic growth" appears 3 times in sample text
        phrase_texts = [p["phrase"] for p in result.repeated_phrases_json]
        assert any("economic growth" in p for p in phrase_texts)

    def test_delivery_score_penalized_for_fillers(self):
        clean = analyze_delivery("The warrant is clear. The evidence supports it. The impact is severe.")
        dirty = analyze_delivery("Um the warrant is uh clear you know. Like basically it supports it so.")
        assert clean.delivery_score >= dirty.delivery_score

    def test_delivery_no_duration_no_pacing_penalty(self):
        # Without duration, no pacing penalty should apply.
        # Use realistic varied text to avoid repetition penalty from identical tokens.
        clean_text = (
            "The United States ought to prioritize diplomatic engagement over military intervention. "
            "The warrant is straightforward: economic sanctions have historically led to political change "
            "without the humanitarian costs of armed conflict. Evidence from multiple case studies confirms "
            "that diplomatic solutions preserve long-term stability. The impact is a more peaceful and "
            "stable international order that benefits all nations involved."
        )
        result = analyze_delivery(clean_text)
        # No filler, no pacing penalty (no duration), good length → score should be high
        assert result.delivery_score >= 80


# ── Delivery drill generation ──────────────────────────────────────────────────

class TestMakeDeliveryDrill:
    def test_too_fast_returns_pacing_drill(self):
        from app.services.drill_generation import make_delivery_drill
        drill = make_delivery_drill(
            clarity_flags=["too_fast"],
            wpm=200.0,
            filler_count=2,
            word_count=200,
        )
        assert drill is not None
        assert drill.skill_target == "pacing_control"

    def test_many_fillers_returns_filler_drill(self):
        from app.services.drill_generation import make_delivery_drill
        drill = make_delivery_drill(
            clarity_flags=["many_fillers"],
            wpm=150.0,
            filler_count=20,
            word_count=100,
        )
        assert drill is not None
        assert drill.skill_target == "filler_reduction"

    def test_long_sentences_returns_clarity_drill(self):
        from app.services.drill_generation import make_delivery_drill
        drill = make_delivery_drill(
            clarity_flags=["long_sentences"],
            wpm=150.0,
            filler_count=1,
            word_count=200,
        )
        assert drill is not None
        assert drill.skill_target == "clarity_delivery"

    def test_no_issues_returns_none(self):
        from app.services.drill_generation import make_delivery_drill
        drill = make_delivery_drill(
            clarity_flags=[],
            wpm=150.0,
            filler_count=1,
            word_count=200,
        )
        assert drill is None

    def test_too_fast_prioritized_over_long_sentences(self):
        from app.services.drill_generation import make_delivery_drill
        # too_fast should take priority
        drill = make_delivery_drill(
            clarity_flags=["too_fast", "long_sentences"],
            wpm=210.0,
            filler_count=2,
            word_count=200,
        )
        assert drill is not None
        assert drill.skill_target == "pacing_control"
