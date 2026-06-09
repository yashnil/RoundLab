"""
Deterministic delivery analysis service.

Computes speaking quality metrics from a transcript and optional duration.
No LLM required — all metrics are derived deterministically from text.

Outputs DeliveryMetricsResult which maps directly to the delivery_metrics table.
"""

import re
from collections import Counter
from typing import Optional
from pydantic import BaseModel

# ── Configurable thresholds ────────────────────────────────────────────────────

WPM_TOO_SLOW = 110
WPM_TOO_FAST = 180
WPM_IDEAL_LOW = 130
WPM_IDEAL_HIGH = 165

FILLER_RATE_HIGH = 0.10     # >10% of words are fillers → many_fillers flag
FILLER_RATE_MEDIUM = 0.05   # >5% → note but no flag

LONG_SENTENCE_WORDS = 30    # sentence longer than this is "long"
LONG_SENTENCE_DENSITY_HIGH = 0.40  # >40% of sentences are long

REPEATED_PHRASE_MIN_FREQ = 3  # phrase must appear this many times to count
REPEATED_PHRASE_MIN_WORDS = 2
REPEATED_PHRASE_MAX_WORDS = 4

VERY_SHORT_SPEECH_WORDS = 75   # speech shorter than this gets short-speech flag
TIMELINE_CHUNKS = 5             # number of approximate timeline segments

# ── Filler words (multi-word before single-word to avoid double-counting) ─────

MULTI_WORD_FILLERS = [
    "you know",
    "kind of",
    "sort of",
    "you see",
    "i mean",
    "i guess",
]

SINGLE_WORD_FILLERS = [
    "um",
    "uh",
    "like",
    "basically",
    "actually",
    "literally",
    "right",
    "so",
]

# Common short phrases to exclude from repeated-phrase detection
_STOP_PHRASES = {
    "in the", "of the", "to the", "on the", "at the", "for the",
    "and the", "is the", "that the", "this is", "it is", "there is",
    "there are", "we have", "we are", "we will", "we can", "we should",
    "they are", "they have", "they will",
    "and we", "but we", "so we", "and they", "but they",
    "of our", "in our", "of their", "in their",
    "and so", "so that", "and that", "but that",
    "not only", "not just",
    "in this case", "as a result", "in fact",
    "the resolution", "this resolution",
}


# ── Output models ──────────────────────────────────────────────────────────────

class TimelineSegment(BaseModel):
    segment_index: int
    approx_start_seconds: Optional[float] = None
    approx_end_seconds: Optional[float] = None
    word_count: int
    filler_count: int
    repeated_phrase_hits: int
    excerpt: str
    flags: list[str]


class DeliveryMetricsResult(BaseModel):
    word_count: int
    duration_seconds: Optional[int] = None
    words_per_minute: Optional[float] = None
    filler_word_count: int
    filler_words_json: dict[str, int]
    repeated_phrases_json: list[dict]
    long_sentence_count: int
    average_sentence_words: float
    delivery_score: int
    pacing_band: str
    clarity_flags_json: list[str]
    timeline_json: list[dict]


# ── Filler detection ───────────────────────────────────────────────────────────

def _count_fillers(text: str) -> tuple[int, dict[str, int]]:
    """Count filler words/phrases. Multi-word fillers are counted first."""
    lower = text.lower()
    counts: dict[str, int] = {}

    # Replace multi-word fillers with placeholders to avoid partial double-counts
    masked = lower
    for phrase in MULTI_WORD_FILLERS:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        hits = len(re.findall(pattern, masked))
        if hits:
            counts[phrase] = hits
        masked = re.sub(pattern, "__FILLER__", masked)

    # Single-word fillers on the masked text
    for word in SINGLE_WORD_FILLERS:
        pattern = r"\b" + re.escape(word) + r"\b"
        hits = len(re.findall(pattern, masked))
        if hits:
            counts[word] = hits

    total = sum(counts.values())
    return total, counts


# ── Repeated phrase detection ──────────────────────────────────────────────────

def _find_repeated_phrases(text: str) -> list[dict]:
    """Find 2–4 word phrases that appear REPEATED_PHRASE_MIN_FREQ or more times."""
    # Tokenize: keep only word characters, lowercase
    tokens = re.findall(r"\b[a-z']+\b", text.lower())

    if len(tokens) < REPEATED_PHRASE_MIN_WORDS:
        return []

    phrase_counts: Counter = Counter()
    for n in range(REPEATED_PHRASE_MIN_WORDS, REPEATED_PHRASE_MAX_WORDS + 1):
        for i in range(len(tokens) - n + 1):
            phrase = " ".join(tokens[i : i + n])
            # Skip stop phrases and phrases consisting entirely of short words
            if phrase not in _STOP_PHRASES:
                phrase_counts[phrase] += 1

    results = []
    for phrase, count in phrase_counts.items():
        if count >= REPEATED_PHRASE_MIN_FREQ:
            results.append({"phrase": phrase, "count": count})

    # Sort by count descending; keep top 10
    results.sort(key=lambda x: x["count"], reverse=True)
    return results[:10]


# ── Sentence analysis ──────────────────────────────────────────────────────────

def _analyze_sentences(text: str) -> tuple[int, int, float]:
    """Return (total_sentences, long_sentence_count, average_words_per_sentence)."""
    # Split on sentence-ending punctuation; also split on long run-on clauses
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 0, 0, 0.0

    word_counts = [len(s.split()) for s in sentences]
    total = len(sentences)
    long_count = sum(1 for wc in word_counts if wc >= LONG_SENTENCE_WORDS)
    avg = sum(word_counts) / total

    return total, long_count, round(avg, 1)


# ── Pacing band ────────────────────────────────────────────────────────────────

def _pacing_band(wpm: Optional[float]) -> str:
    if wpm is None:
        return "unknown"
    if wpm < WPM_TOO_SLOW:
        return "too_slow"
    if wpm > WPM_TOO_FAST:
        return "too_fast"
    return "steady"


# ── Delivery score ─────────────────────────────────────────────────────────────

def _compute_delivery_score(
    word_count: int,
    wpm: Optional[float],
    filler_count: int,
    repeated_phrases: list[dict],
    long_sentence_count: int,
    total_sentences: int,
) -> int:
    score = 100

    # Pacing penalty
    if wpm is not None:
        if wpm < 90 or wpm > 220:
            score -= 20
        elif wpm < WPM_TOO_SLOW or wpm > 200:
            score -= 12
        elif wpm < WPM_IDEAL_LOW or wpm > WPM_IDEAL_HIGH:
            score -= 5

    # Filler penalty
    filler_rate = filler_count / max(word_count, 1)
    if filler_rate > FILLER_RATE_HIGH:
        score -= 25
    elif filler_rate > FILLER_RATE_MEDIUM:
        score -= 12
    elif filler_rate > 0.02:
        score -= 5

    # Repetition penalty (capped at 15)
    score -= min(15, len(repeated_phrases) * 5)

    # Long sentence density penalty
    if total_sentences > 0:
        long_density = long_sentence_count / total_sentences
        if long_density > LONG_SENTENCE_DENSITY_HIGH:
            score -= 10
        elif long_density > 0.25:
            score -= 5

    # Short speech penalty
    if word_count < VERY_SHORT_SPEECH_WORDS:
        score -= 15
    elif word_count < 100:
        score -= 5

    return max(0, min(100, score))


# ── Clarity flags ──────────────────────────────────────────────────────────────

def _compute_clarity_flags(
    word_count: int,
    wpm: Optional[float],
    filler_count: int,
    repeated_phrases: list[dict],
    long_sentence_count: int,
    total_sentences: int,
) -> list[str]:
    flags: list[str] = []
    if wpm is not None and wpm > WPM_TOO_FAST:
        flags.append("too_fast")
    if wpm is not None and wpm < WPM_TOO_SLOW:
        flags.append("too_slow")
    filler_rate = filler_count / max(word_count, 1)
    if filler_rate > FILLER_RATE_MEDIUM:
        flags.append("many_fillers")
    if len(repeated_phrases) >= 2:
        flags.append("repetitive_wording")
    if total_sentences > 0 and (long_sentence_count / total_sentences) > LONG_SENTENCE_DENSITY_HIGH:
        flags.append("long_sentences")
    if word_count < VERY_SHORT_SPEECH_WORDS:
        flags.append("very_short_speech")
    return flags


# ── Timeline chunking ──────────────────────────────────────────────────────────

def _build_timeline(
    text: str,
    word_count: int,
    duration_seconds: Optional[int],
    filler_words: dict[str, int],
    repeated_phrases: list[dict],
) -> list[dict]:
    """Split transcript into TIMELINE_CHUNKS segments with approx timestamps."""
    words = text.split()
    n_chunks = TIMELINE_CHUNKS
    chunk_size = max(1, len(words) // n_chunks)

    # Build a set of repeated phrase tokens for quick lookup
    rep_phrase_set = {entry["phrase"] for entry in repeated_phrases}

    # Build a per-word filler mask
    lower_text = text.lower()
    # We need per-word-position filler info; rebuild by scanning tokens in order
    lower_words = [w.lower().strip(".,!?;:\"'") for w in words]

    # Build multi-word filler positions
    filler_positions: set[int] = set()
    for phrase in MULTI_WORD_FILLERS:
        phrase_tokens = phrase.split()
        n = len(phrase_tokens)
        for i in range(len(lower_words) - n + 1):
            if lower_words[i : i + n] == phrase_tokens:
                for j in range(n):
                    filler_positions.add(i + j)
    for i, w in enumerate(lower_words):
        if i not in filler_positions and w in SINGLE_WORD_FILLERS:
            filler_positions.add(i)

    segments = []
    for chunk_idx in range(n_chunks):
        start_word = chunk_idx * chunk_size
        end_word = min(start_word + chunk_size, len(words))
        if start_word >= len(words):
            break

        chunk_words = words[start_word:end_word]
        chunk_lower_words = lower_words[start_word:end_word]
        chunk_word_count = len(chunk_words)

        # Filler count in this chunk
        chunk_filler_count = sum(1 for i in range(start_word, end_word) if i in filler_positions)

        # Repeated phrase hits in this chunk
        chunk_text_lower = " ".join(chunk_lower_words)
        rep_hits = 0
        for phrase in rep_phrase_set:
            if phrase in chunk_text_lower:
                rep_hits += len(re.findall(r"\b" + re.escape(phrase) + r"\b", chunk_text_lower))

        # Excerpt: first 120 chars of chunk
        excerpt = " ".join(chunk_words)[:120]
        if len(" ".join(chunk_words)) > 120:
            excerpt += "…"

        # Approximate timestamps
        approx_start: Optional[float] = None
        approx_end: Optional[float] = None
        if duration_seconds and word_count > 0:
            approx_start = round((start_word / word_count) * duration_seconds, 1)
            approx_end = round((end_word / word_count) * duration_seconds, 1)

        # Per-segment flags
        flags: list[str] = []
        if chunk_word_count > 0:
            if (chunk_filler_count / chunk_word_count) > FILLER_RATE_MEDIUM:
                flags.append("high_fillers")
            if rep_hits >= 2:
                flags.append("repetitive")

        segments.append(TimelineSegment(
            segment_index=chunk_idx,
            approx_start_seconds=approx_start,
            approx_end_seconds=approx_end,
            word_count=chunk_word_count,
            filler_count=chunk_filler_count,
            repeated_phrase_hits=rep_hits,
            excerpt=excerpt,
            flags=flags,
        ).model_dump())

    return segments


# ── Main entry point ───────────────────────────────────────────────────────────

def analyze_delivery(
    transcript: str,
    duration_seconds: Optional[int] = None,
) -> DeliveryMetricsResult:
    """Compute delivery metrics from a speech transcript.

    Args:
        transcript: Full transcript text.
        duration_seconds: Audio duration in seconds (optional).

    Returns:
        DeliveryMetricsResult with all computed fields.
    """
    # Basic counts
    word_count = len(transcript.split()) if transcript else 0

    # WPM
    wpm: Optional[float] = None
    if duration_seconds and duration_seconds > 0 and word_count > 0:
        wpm = round((word_count / duration_seconds) * 60, 1)

    # Filler words
    filler_count, filler_breakdown = _count_fillers(transcript)

    # Repeated phrases
    repeated_phrases = _find_repeated_phrases(transcript)

    # Sentence analysis
    total_sentences, long_sentence_count, avg_sentence_words = _analyze_sentences(transcript)

    # Pacing band
    band = _pacing_band(wpm)

    # Clarity flags
    clarity_flags = _compute_clarity_flags(
        word_count=word_count,
        wpm=wpm,
        filler_count=filler_count,
        repeated_phrases=repeated_phrases,
        long_sentence_count=long_sentence_count,
        total_sentences=total_sentences,
    )

    # Delivery score
    score = _compute_delivery_score(
        word_count=word_count,
        wpm=wpm,
        filler_count=filler_count,
        repeated_phrases=repeated_phrases,
        long_sentence_count=long_sentence_count,
        total_sentences=total_sentences,
    )

    # Timeline
    timeline = _build_timeline(
        text=transcript,
        word_count=word_count,
        duration_seconds=duration_seconds,
        filler_words=filler_breakdown,
        repeated_phrases=repeated_phrases,
    )

    return DeliveryMetricsResult(
        word_count=word_count,
        duration_seconds=duration_seconds,
        words_per_minute=wpm,
        filler_word_count=filler_count,
        filler_words_json=filler_breakdown,
        repeated_phrases_json=repeated_phrases,
        long_sentence_count=long_sentence_count,
        average_sentence_words=avg_sentence_words,
        delivery_score=score,
        pacing_band=band,
        clarity_flags_json=clarity_flags,
        timeline_json=timeline,
    )
