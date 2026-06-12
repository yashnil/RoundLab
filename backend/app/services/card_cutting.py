"""Passage selection and card drafting for Research-to-Card Evidence Builder.

CRITICAL SAFETY RULE: body_text is ALWAYS exact source text. The LLM may only:
  - select which passage to use (by returning character indices)
  - suggest a tag (debater-written, clearly labeled as generated)
  - suggest highlight/underline span offsets
  - summarize warrant and impact
The LLM CANNOT modify, rephrase, or extend the body text.
"""

import logging
import re
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.research import (
    AnnotatedSpan,
    CardIntelligence,
    CitationMetadata,
    EvidenceCutResult,
    ExtractedArticle,
    SelectedSpan,
    SourceQuality,
)

logger = logging.getLogger(__name__)

_MAX_ARTICLE_CHARS = 12_000   # chars sent to LLM
_MIN_PARA_CHARS    = 80
_MAX_CANDIDATE_PARAS = 20
_MIN_BODY_CHARS    = 60


# ── LLM output schema ─────────────────────────────────────────────────────────

class _SpanOutput(BaseModel):
    start: int
    end: int
    reason: str = ""


class _CardCuttingOutput(BaseModel):
    body_start_idx: int = Field(description="Start char index of selected passage in article text")
    body_end_idx: int   = Field(description="End char index of selected passage in article text")
    tag: str            = Field(description="Debater-written tag (~15-20 words, active voice)")
    highlight_spans: list[_SpanOutput] = Field(
        default=[],
        description="Key warrant phrases within body_text (char offsets relative to body start)",
    )
    underline_spans: list[_SpanOutput] = Field(
        default=[],
        description="Impact/warrant phrases within body_text (char offsets relative to body start)",
    )
    warrant_summary: str  = Field(description="What this passage proves (1-2 sentences)")
    impact_summary: str   = Field(description="Why this matters in a debate (1-2 sentences)")
    selection_reason: str = Field(description="Why this passage was chosen over others", default="")
    confidence: float     = Field(default=0.5, ge=0.0, le=1.0)


# ── Evidence cut LLM schema ────────────────────────────────────────────────────

class _SelectedSpanLLM(BaseModel):
    exact_text: str       # must be exact substring of passage
    rationale: str = ""


class _EvidenceCutLLMOutput(BaseModel):
    """LLM selects exact phrase spans to include in the cut."""
    improved_tag: str = ""
    selected_spans: list[_SelectedSpanLLM] = []
    cut_style: Literal["full", "light_cut", "medium_cut", "aggressive_cut"] = "medium_cut"
    tag_overclaim_warning: str = ""
    safe_tag_scope: str = ""


# ── Candidate scoring ─────────────────────────────────────────────────────────

_CAUSAL_WORDS = frozenset({
    "because", "therefore", "thus", "hence", "result", "cause", "leads",
    "increases", "decreases", "reduces", "promotes", "threatens", "enables",
    "prevents", "requires", "proves", "shows", "demonstrates", "finds",
    "according", "percent", "study", "research", "data", "evidence",
})

_IMPACT_WORDS = frozenset({
    "economic", "security", "death", "crisis", "risk", "threat", "war",
    "poverty", "climate", "inequality", "harm", "benefit", "affect",
    "impact", "consequence", "million", "billion", "percent", "jobs",
})


def _score_paragraph(para: str, claim_goal: str, topic: str) -> float:
    """Simple heuristic score for how card-worthy a paragraph is."""
    words = set(para.lower().split())
    goal_words = set((claim_goal + " " + topic).lower().split())

    # Strong penalty for chrome/navigation paragraphs
    para_lines = [l.strip() for l in para.splitlines() if l.strip()]
    if para_lines:
        chrome_line_ratio = sum(1 for l in para_lines if _is_chrome_line(l)) / len(para_lines)
        if chrome_line_ratio > 0.5:
            return -10.0  # essentially excluded
        if chrome_line_ratio > 0.25:
            return -3.0   # heavily penalized

    # Penalty for paragraphs that look like repository/metadata chrome
    lower = para.lower()
    chrome_keywords = ["digital commons", "included in", "recommended citation",
                       "repository citation", "download", "issn:", "doi:", "abstract\n",
                       "keywords:", "follow this", "posted at", "vol.", "no.", "pages "]
    chrome_hits = sum(1 for k in chrome_keywords if k in lower)
    if chrome_hits >= 2:
        return -5.0
    if chrome_hits == 1:
        return 0.0  # not negative but no positive score

    # Keyword overlap with claim goal
    overlap = len(words & goal_words & {w for w in goal_words if len(w) > 3})
    score = overlap * 1.5

    # Evidence signal words
    causal_hits = len(words & _CAUSAL_WORDS)
    score += causal_hits * 0.8

    impact_hits = len(words & _IMPACT_WORDS)
    score += impact_hits * 0.6

    # Length bonus (prefer 100-500 word paragraphs)
    char_len = len(para)
    if 400 <= char_len <= 2000:
        score += 2.0
    elif 200 <= char_len < 400:
        score += 1.0
    elif char_len > 2000:
        score += 0.3

    # Number/statistic presence
    if re.search(r"\d+(\.\d+)?%", para):
        score += 1.5
    if re.search(r"\b\d{4}\b", para):  # year-like number
        score += 0.5

    # Bonus for sentences that look like real evidence
    if any(kw in lower for kw in ["court", "held", "ruled", "states", "argues", "demonstrates",
                                    "evidence", "study", "research", "percent", "million"]):
        score += 1.0

    return score


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, filtering noise."""
    paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in paragraphs if len(p.strip()) >= _MIN_PARA_CHARS]


# ── Span verification ────────────────────────────────────────────────────────

def verify_spans(body_text: str, spans: list[dict]) -> list[dict]:
    """Remove spans that don't map to valid character offsets in body_text.
    All returned spans are verified to exist exactly in body_text."""
    verified: list[dict] = []
    body_len = len(body_text)
    for span in spans:
        start = span.get("start", -1)
        end = span.get("end", -1)
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end <= start or end > body_len:
            continue
        verified.append(span)
    return verified


# ── Abbreviation set for sentence splitting ───────────────────────────────────

# Common abbreviations that end with a period but are NOT sentence ends
_ABBREVS = frozenset({
    "u.s", "u.k", "d.c", "u.n", "e.u", "u.s.a",
    "inc", "ltd", "co", "corp", "llc",
    "no", "nos", "vol", "pp", "p", "sec",
    "mr", "ms", "mrs", "dr", "prof", "sen", "rep", "gov", "pres",
    "v", "vs",
    "e.g", "i.e", "etc", "cf",
    "et al", "ibid", "id",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "fig", "eq", "approx",
})


@dataclass
class SentenceSpan:
    text: str
    start: int
    end: int
    index: int


# ── Sentence splitting ────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[SentenceSpan]:
    """Split text into sentences with character offsets. Returns SentenceSpan list.

    Avoids splitting on common abbreviations (U.S., v., et al., etc.).
    Also avoids splitting in the middle of dotted abbreviations like U.S. or e.g.
    """
    if not text.strip():
        return []

    sentences: list[SentenceSpan] = []
    start = 0
    i = 0

    while i < len(text):
        ch = text[i]
        if ch in ".!?":
            # Get the token ending at i (backwards from i)
            j = i - 1
            while j >= start and text[j].isalpha():
                j -= 1
            token = text[j + 1:i].lower()

            is_abbrev = token in _ABBREVS

            # Also check two-part abbrevs like "et al." by looking at the token
            # and its predecessor
            if not is_abbrev and token in ("al",):
                # Check for "et al"
                prev_space = text.rfind(" ", start, j + 1)
                prev_token = text[prev_space + 1:j + 1].lower()
                if prev_token in ("et",):
                    is_abbrev = True

            # Detect dotted multi-letter abbreviations like U.S. or e.g. or i.e.
            # When token is a single letter and the NEXT non-space char is also a
            # single-letter followed immediately by a dot, treat as abbreviation.
            if not is_abbrev and len(token) == 1 and token.isalpha():
                # Check if we're inside a dotted abbreviation like U.S. or e.g.
                k = i + 1
                # Skip over optional whitespace (none expected in U.S. but be safe)
                if k < len(text) and text[k].isalpha():
                    kk = k
                    while kk < len(text) and text[kk].isalpha():
                        kk += 1
                    if kk < len(text) and text[kk] == ".":
                        # Next segment is letters followed by a dot — dotted abbrev
                        is_abbrev = True
                    elif kk - k == 1:
                        # Single letter; check if there is a dot coming after it
                        # e.g. U.S.A — token="u", next="s" then "."
                        pass  # already handled above since kk-k==1 and text[kk]=="."

            if not is_abbrev:
                # Check if next non-space char is uppercase (sentence boundary)
                k = i + 1
                while k < len(text) and text[k] in " \t\n":
                    k += 1

                if k < len(text) and text[k].isupper():
                    sent = text[start:i + 1].strip()
                    if sent:
                        # Find actual start of this sentence in text
                        sent_start = text.index(sent, start)
                        sentences.append(SentenceSpan(
                            text=sent,
                            start=sent_start,
                            end=sent_start + len(sent),
                            index=len(sentences),
                        ))
                    start = k
        i += 1

    # Remaining text
    remaining = text[start:].strip()
    if remaining:
        sent_start = text.index(remaining, start)
        sentences.append(SentenceSpan(
            text=remaining,
            start=sent_start,
            end=sent_start + len(remaining),
            index=len(sentences),
        ))

    return sentences


# ── Build cut from sentences ──────────────────────────────────────────────────

def _build_cut_from_sentence_spans(
    original: str,
    spans: list[SentenceSpan],
    indices: list[int],
) -> EvidenceCutResult:
    """Build EvidenceCutResult from selected SentenceSpan indices."""
    if not indices:
        return EvidenceCutResult(
            original_passage=original,
            selected_spans=[],
            cut_text=original,
            cut_text_with_ellipses=original,
            compression_ratio=1.0,
            cut_style="full",
            validation_passed=False,
            validation_notes="No spans selected",
        )

    selected_spans: list[SelectedSpan] = []
    for idx in sorted(set(indices)):
        if idx < 0 or idx >= len(spans):
            continue
        span = spans[idx]
        selected_spans.append(SelectedSpan(
            start=span.start, end=span.end, text=span.text, sentence_index=idx,
        ))

    if not selected_spans:
        return EvidenceCutResult(
            original_passage=original, selected_spans=[],
            cut_text=original, cut_text_with_ellipses=original,
            compression_ratio=1.0, cut_style="full",
            validation_passed=False, validation_notes="No spans found in original text",
        )

    # Sort by start position
    selected_spans.sort(key=lambda s: s.start)

    # Build cut text and ellipsis text
    parts = [s.text for s in selected_spans]
    cut_text = " ".join(parts)

    # Join with ellipsis where spans are non-adjacent
    ellipsis_parts = [selected_spans[0].text]
    for i in range(1, len(selected_spans)):
        prev_end = selected_spans[i - 1].end
        curr_start = selected_spans[i].start
        gap = original[prev_end:curr_start].strip()
        if gap:  # there's skipped text
            ellipsis_parts.append("[…]")
        ellipsis_parts.append(selected_spans[i].text)
    cut_with_ellipses = " ".join(ellipsis_parts)

    # Compression ratio
    ratio = len(cut_text) / max(len(original), 1)

    # Determine cut_style
    if ratio > 0.9:
        style = "full"
    elif ratio > 0.65:
        style = "light_cut"
    elif ratio > 0.4:
        style = "medium_cut"
    else:
        style = "aggressive_cut"

    # Validate: every span's text must be found exactly in original
    all_valid = all(original.find(s.text) != -1 for s in selected_spans)

    return EvidenceCutResult(
        original_passage=original,
        selected_spans=selected_spans,
        cut_text=cut_text,
        cut_text_with_ellipses=cut_with_ellipses,
        compression_ratio=ratio,
        confidence=0.8 if all_valid else 0.4,
        cut_style=style,  # type: ignore[arg-type]
        validation_passed=all_valid,
        validation_notes="" if all_valid else "Some spans not found in original text",
    )


def _build_cut_from_sentences(
    original: str,
    sentences: list,
    indices: list[int],
) -> EvidenceCutResult:
    """Build EvidenceCutResult from selected sentence indices.

    Accepts either list[SentenceSpan] or list[str] for backward compatibility.
    All selected sentences must be exact text from original. Joined with ' [...] ' when non-adjacent.
    """
    # Normalise to SentenceSpan
    if sentences and isinstance(sentences[0], str):
        span_list: list[SentenceSpan] = []
        search_from = 0
        for idx, sent in enumerate(sentences):
            pos = original.find(sent, search_from)
            if pos == -1:
                stripped = sent.strip()
                pos = original.find(stripped, search_from)
                if pos == -1:
                    pos = 0
                sent = stripped
            span_list.append(SentenceSpan(text=sent, start=pos, end=pos + len(sent), index=idx))
            search_from = max(search_from, pos + 1)
        sentences = span_list

    return _build_cut_from_sentence_spans(original, sentences, indices)


# ── Phrase-level cut validation ───────────────────────────────────────────────

def _validate_and_build_phrase_cut(
    original: str,
    llm_spans: list[_SelectedSpanLLM],
) -> Optional[EvidenceCutResult]:
    """Validate that each LLM-selected span is an exact substring of original.

    Spans are validated, sorted by position, and joined with ' [\\u2026] ' between
    non-adjacent spans. Invalid spans are discarded. If fewer than 1 valid span
    remains, returns None (caller falls back to sentence-level cut).
    """
    validated: list[SelectedSpan] = []
    search_from = 0

    # First pass: find each exact_text in original, preserving order
    for i, span in enumerate(llm_spans):
        et = span.exact_text.strip()
        if not et or len(et) < 10:
            continue
        pos = original.find(et, search_from)
        if pos == -1:
            # Try from the beginning in case of ordering issue
            pos = original.find(et)
        if pos == -1:
            logger.debug("Span not found in original, discarding: %r", et[:60])
            continue
        # Advance search position to preserve order
        search_from = max(search_from, pos)
        validated.append(SelectedSpan(
            start=pos, end=pos + len(et), text=et,
            sentence_index=i, rationale=span.rationale,
        ))

    if not validated:
        return None  # signal to caller to fall back

    # Sort by start position
    validated.sort(key=lambda s: s.start)

    # Build cut text with [...] between non-adjacent spans
    parts = [validated[0].text]
    for j in range(1, len(validated)):
        prev_end = validated[j - 1].end
        curr_start = validated[j].start
        gap = original[prev_end:curr_start].strip()
        if gap:
            parts.append("[…]")
        parts.append(validated[j].text)

    cut_with_ellipses = " ".join(parts)
    cut_text = " ".join(s.text for s in validated)
    ratio = len(cut_text) / max(len(original), 1)

    if ratio > 0.9:
        style = "full"
    elif ratio > 0.65:
        style = "light_cut"
    elif ratio > 0.4:
        style = "medium_cut"
    else:
        style = "aggressive_cut"

    return EvidenceCutResult(
        original_passage=original,
        selected_spans=validated,
        cut_text=cut_text,
        cut_text_with_ellipses=cut_with_ellipses,
        compression_ratio=ratio,
        confidence=0.85,
        cut_style=style,  # type: ignore[arg-type]
        validation_passed=True,
    )


# ── Clause-level candidates for deterministic fallback ───────────────────────

_CLAUSE_SPLITS = re.compile(
    r'(?<=[,;:]) +|(?<= )(?:—|because |which |that |while |although |however )'
)


def _get_clause_candidates(sentences: list[SentenceSpan], original: str) -> list[SelectedSpan]:
    """Split sentences into clause candidates for scoring."""
    candidates = []
    for sent in sentences:
        # Try splitting sentence into clauses
        parts = _CLAUSE_SPLITS.split(sent.text)
        if len(parts) > 1:
            pos = sent.start
            for part in parts:
                if not isinstance(part, str) or not part:
                    continue
                part = part.strip()
                if not part:
                    continue
                if len(part.split()) >= 4:  # minimum 4 words to be useful
                    p = original.find(part, pos)
                    if p != -1:
                        candidates.append(SelectedSpan(
                            start=p, end=p + len(part), text=part, sentence_index=sent.index,
                        ))
                        pos = p
        else:
            # Use whole sentence
            candidates.append(SelectedSpan(
                start=sent.start, end=sent.end, text=sent.text, sentence_index=sent.index,
            ))
    return candidates


def _select_sentences_with_llm(
    passage: str,
    sentences: list[SentenceSpan],
    claim: str,
    evidence_role: str,
    tag: str,
    style_hint: str = "",
) -> Optional[_EvidenceCutLLMOutput]:
    """Ask GPT-4o-mini to select exact phrase spans from the passage.

    style_hint, when provided, nudges the cut length (e.g. cut lightly/aggressively).
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        _style_line = f"\nCUT STYLE: {style_hint}\n" if style_hint else ""
        prompt = f"""You are a debate evidence card cutter. Your job is to select the most impactful exact phrases from a source passage to create a shortened card.

CLAIM: {claim}
EVIDENCE ROLE: {evidence_role}
PROPOSED TAG: {tag or "TBD"}
{_style_line}
PASSAGE:
{passage}

Instructions:
1. Select 2-5 exact phrases or complete clauses/sentences that best support the claim.
2. Each selected span must be EXACT text from the passage — copy it verbatim.
3. Do not paraphrase or modify the evidence text in any way.
4. Prefer complete clauses (around commas, semicolons) that make sense in isolation.
5. Select the minimum text needed — cut boldly but keep coherence.
6. For mechanism_support: select the legal/technical mechanism phrases.
7. For example_support: select the specific case/ruling phrases.
8. For impact_support: select the harm/consequence phrases.
9. Return an improved_tag that states exactly what this card PROVES as a complete sentence.
   - GOOD: "Section 230 grants platforms blanket immunity from civil liability for user content"
   - BAD: "Section 230 — mechanism support" or "Internet law — direct support"
   - The tag must be grounded in what the card body actually says. Do NOT write <topic> — <role> format.

IMPORTANT: exact_text must be word-for-word copy from the passage above.
"""
        resp = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format=_EvidenceCutLLMOutput,
            temperature=0,
        )
        return resp.choices[0].message.parsed
    except Exception as exc:
        logger.debug("Evidence cut LLM failed: %s", exc)
        return None


def _deterministic_cut(
    passage: str,
    sentences: list[SentenceSpan],
    claim: str,
    target_ratio: float = 0.60,
) -> EvidenceCutResult:
    """Deterministic fallback: score clause candidates and take top ones.

    target_ratio controls roughly what fraction of the candidate clauses to keep:
    higher values keep more context (lighter cut), lower values cut harder.
    """
    claim_words = set((claim or "").lower().split())

    try:
        candidates = _get_clause_candidates(sentences, passage)
    except Exception as exc:
        logger.debug("_get_clause_candidates failed (%s) — using full sentences", exc)
        candidates = [
            SelectedSpan(start=s.start, end=s.end, text=s.text, sentence_index=s.index)
            for s in sentences
        ]

    scored = []
    for i, cand in enumerate(candidates):
        sent_words = set(cand.text.lower().split())
        overlap = len(claim_words & sent_words) / max(len(claim_words), 1)
        length_score = min(1.0, len(cand.text.split()) / 20)
        # Prefer sentences with legal/evidentiary terms
        legal_score = sum(
            1 for w in ["court", "held", "ruled", "provides", "states", "found", "evidence"]
            if w in cand.text.lower()
        ) * 0.2
        score = overlap * 3 + length_score + legal_score
        scored.append((score, i))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Take top target_ratio of candidates, minimum 2
    _ratio = max(0.05, min(1.0, target_ratio))
    n_keep = max(2, int(round(len(candidates) * _ratio)))
    top_candidates = sorted(idx for _, idx in scored[:n_keep])

    # Build result from selected candidate spans
    selected: list[SelectedSpan] = [candidates[i] for i in top_candidates]
    if not selected:
        return EvidenceCutResult(
            original_passage=passage, selected_spans=[],
            cut_text=passage, cut_text_with_ellipses=passage,
            compression_ratio=1.0, cut_style="full",
            validation_passed=False, validation_notes="No candidates found",
        )

    selected.sort(key=lambda s: s.start)

    parts = [s.text for s in selected]
    cut_text = " ".join(parts)

    ellipsis_parts = [selected[0].text]
    for i in range(1, len(selected)):
        prev_end = selected[i - 1].end
        curr_start = selected[i].start
        gap = passage[prev_end:curr_start].strip()
        if gap:
            ellipsis_parts.append("[…]")
        ellipsis_parts.append(selected[i].text)
    cut_with_ellipses = " ".join(ellipsis_parts)

    ratio = len(cut_text) / max(len(passage), 1)

    if ratio > 0.9:
        style = "full"
    elif ratio > 0.65:
        style = "light_cut"
    elif ratio > 0.4:
        style = "medium_cut"
    else:
        style = "aggressive_cut"

    all_valid = all(passage.find(s.text) != -1 for s in selected)

    return EvidenceCutResult(
        original_passage=passage,
        selected_spans=selected,
        cut_text=cut_text,
        cut_text_with_ellipses=cut_with_ellipses,
        compression_ratio=ratio,
        confidence=0.8 if all_valid else 0.4,
        cut_style=style,  # type: ignore[arg-type]
        validation_passed=all_valid,
        validation_notes="" if all_valid else "Some spans not found in original text",
    )


# Map user-facing cut-style names → deterministic target ratio + LLM hint.
_CUT_STYLE_TARGET_RATIO: dict[str, float] = {
    "light": 0.85,
    "medium": 0.60,
    "aggressive": 0.35,
}
_CUT_STYLE_LLM_HINT: dict[str, str] = {
    "light": "Cut lightly — keep most context, only remove clearly off-topic parts.",
    "aggressive": "Cut aggressively — aim for 3-5 key phrases only.",
}


def _full_passage_cut(passage: str, sentence_spans: list[SentenceSpan]) -> EvidenceCutResult:
    """Return an EvidenceCutResult that keeps the entire passage as the cut."""
    all_spans: list[SelectedSpan] = [
        SelectedSpan(start=s.start, end=s.end, text=s.text, sentence_index=s.index)
        for s in sentence_spans
    ]
    return EvidenceCutResult(
        original_passage=passage,
        selected_spans=all_spans,
        cut_text=passage,
        cut_text_with_ellipses=passage,
        compression_ratio=1.0,
        cut_style="full",
        validation_passed=True,
    )


# ── Cut body span remapping + deterministic highlights (Part 4b) ─────────────

import uuid as _uuid

# High-value debate terms for deterministic highlighting
_HIGHLIGHT_CAUSAL = frozenset({
    "causes", "cause", "enables", "enable", "creates", "create", "prevents",
    "prevent", "grants", "provides", "shields", "increases", "reduces",
    "permits", "requires", "leads", "demonstrates", "establishes", "proves",
    "shows", "finds", "found", "held", "ruled", "requires", "mandates",
})
_HIGHLIGHT_LEGAL = frozenset({
    "court", "statute", "law", "legal", "ruling", "doctrine", "regulation",
    "section", "immunity", "liability", "jurisdiction", "provision",
    "authorization", "treaty", "convention", "violation", "precedent",
})
_HIGHLIGHT_MORAL = frozenset({
    "moral", "ethical", "obligation", "duty", "rights", "justice",
    "genocide", "atrocity", "suffering", "harm", "dignity", "humanitarian",
})
_HIGHLIGHT_IMPACT = frozenset({
    "million", "billion", "percent", "thousand", "deaths", "killed",
    "displaced", "casualties", "crisis", "threat", "risk",
})


def remap_spans_to_cut_body(
    cut_body: str,
    original_spans: list[SelectedSpan],
) -> list[SelectedSpan]:
    """Remap selected_spans (offsets in original_passage) to offsets in cut_body.

    Uses exact text matching — only valid exact substrings are included.
    Searches monotonically to preserve order and avoid re-matching earlier text.
    """
    if not cut_body or not original_spans:
        return []
    remapped: list[SelectedSpan] = []
    search_from = 0
    for span in sorted(original_spans, key=lambda s: s.start):
        text = span.text
        if not text or not isinstance(text, str):
            continue
        pos = cut_body.find(text, search_from)
        if pos == -1:
            # Try from start in case order is not preserved in cut body
            pos = cut_body.find(text)
        if pos != -1:
            remapped.append(SelectedSpan(
                start=pos, end=pos + len(text), text=text,
                sentence_index=span.sentence_index, rationale=span.rationale,
            ))
            search_from = max(search_from, pos)
    return remapped


def get_deterministic_highlight_spans(
    text: str,
    claim: str = "",
    evidence_role: str = "",
) -> list[SelectedSpan]:
    """Find highlight spans in text using claim terms, role terms, and high-value patterns.

    Only matches whole phrases / substrings that exist exactly in text.
    Returns spans sorted by start position.
    """
    if not text:
        return []

    candidates: list[tuple[int, int, str]] = []  # (start, end, reason)

    # Named entity pattern: capitalized word not at start of sentence
    for m in re.finditer(r'(?<=[.!? ])[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*', text):
        candidates.append((m.start(), m.end(), "named_entity"))

    # Statistics / numbers with units
    for m in re.finditer(
        r'\d+(?:[.,]\d+)?(?:\s*(?:%|percent|million|billion|trillion|thousand|deaths|people|users))',
        text, re.IGNORECASE,
    ):
        candidates.append((m.start(), m.end(), "statistic"))

    # Year (standalone)
    for m in re.finditer(r'\b(19|20)\d{2}\b', text):
        candidates.append((m.start(), m.end(), "year"))

    # High-value debate phrases (multi-word lookups)
    _PHRASES = [
        "use of military force", "extraordinary suffering", "large-scale violation",
        "basic human rights", "armed humanitarian intervention",
        "protect, defend, or rescue", "gross abuse", "without the consent",
        "Rwandan genocide", "nearly one million", "human rights", "civil war",
        "international law", "Security Council", "United Nations",
        "self-defense", "territorial integrity", "state sovereignty",
        "climate change", "economic impact", "public health", "national security",
    ]
    for phrase in _PHRASES:
        pos = text.lower().find(phrase.lower())
        if pos != -1:
            candidates.append((pos, pos + len(phrase), "debate_phrase"))

    # Claim term overlap: words > 4 chars from claim not in stopwords
    _CLAIM_STOPS = frozenset({
        "that", "this", "with", "from", "have", "will", "been", "they",
        "their", "there", "when", "would", "could", "should", "about",
    })
    claim_words = [
        w for w in re.sub(r'[^\w\s]', ' ', (claim or "").lower()).split()
        if len(w) > 4 and w not in _CLAIM_STOPS
    ]
    for word in claim_words[:8]:
        for m in re.finditer(re.escape(word), text, re.IGNORECASE):
            # Expand to whole word boundary
            s, e = m.start(), m.end()
            candidates.append((s, e, "claim_term"))

    # Causal / legal / moral / impact term context (2-word windows)
    _ALL_SIGNAL = _HIGHLIGHT_CAUSAL | _HIGHLIGHT_LEGAL | _HIGHLIGHT_MORAL | _HIGHLIGHT_IMPACT
    words = text.split()
    pos_map: list[int] = []  # char offset of each word
    _c = 0
    for w in words:
        pos_map.append(text.index(w, _c))
        _c = pos_map[-1] + len(w)

    for wi, w in enumerate(words):
        if w.lower().rstrip('.,;:') in _ALL_SIGNAL:
            # Take a window: previous word + this word + next word
            ws = max(0, wi - 1)
            we = min(len(words) - 1, wi + 1)
            start_c = pos_map[ws]
            end_c = pos_map[we] + len(words[we])
            candidates.append((start_c, end_c, "signal_term"))

    if not candidates:
        return []

    # Merge overlapping candidates and build SelectedSpan list
    candidates.sort(key=lambda x: x[0])
    merged: list[tuple[int, int]] = []
    for s, e, _ in candidates:
        if merged and s < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    result: list[SelectedSpan] = []
    for s, e in merged:
        span_text = text[s:e]
        if len(span_text.split()) >= 1 and span_text.strip():
            result.append(SelectedSpan(
                start=s, end=e, text=span_text, sentence_index=0,
                rationale="deterministic_highlight",
            ))

    # Cap at reasonable number of highlights
    return result[:12]


# ── Page-chrome detection and stripping ──────────────────────────────────────

# Patterns that indicate a line is page chrome / navigation / metadata, not evidence.
_CHROME_LINE_RE = re.compile(
    r'^(?:'
    r'Home\s*[>›»|]'                # breadcrumb start
    r'|.*?\s*[>›»]\s*.*?\s*[>›»]'  # multi-level breadcrumb
    r'|Abstract\s*$'                # bare "Abstract" label
    r'|ABSTRACT\s*$'
    r'|Keywords?\s*[:—]'
    r'|Download\s'
    r'|Included in '
    r'|Digital Commons'
    r'|Open Access'
    r'|(?:PDF|DOC|DOCX|Article)\s+(?:Full Text|Download)'
    r'|(?:Follow|Follow this|Share this)\s'
    r'|(?:Search|Browse)\s+(?:this|the)\s'
    r'|Posted\s+(?:at|on|in)\s'
    r'|Repository\s+Citation'
    r'|Recommended Citation'
    r'|(?:Vol|Volume)\.?\s+\d+,?\s+(?:No|Issue)\.?\s+\d+'
    r'|(?:Published|Revised|Accepted|Received):\s+\d'
    r'|DOI:\s+'
    r'|ISSN:\s+'
    r'|Pages?\s+\d+[–-]\d+'
    r'|Copyright\s+©'
    r'|\d+\s+(?:views?|downloads?|citations?)\s*$'
    r'|(?:Subscribe|Sign\s+in|Log\s+in|Create\s+account)'
    r')',
    re.IGNORECASE,
)

# Short lines that are almost always chrome (< 40 chars and match these)
_CHROME_SHORT_RE = re.compile(
    r'^(?:Abstract|Introduction|Contents?|Menu|Navigation|'
    r'Skip to|Back to|Return to|View|Table of Contents|'
    r'Authors?\s*$|Author(?:s?)\s+Note|Corresponding Author|'  # bare "Authors" label
    r'Figure\s+\d|Table\s+\d|Appendix|References|Bibliography|'
    r'Published\s+in|Appears in|In:|Editors?:|Translated)',
    re.IGNORECASE,
)

# Pattern for author-institution metadata lines:
# "Firstname Lastname, University of Something" or "Name <email>"
_AUTHOR_INSTITUTION_RE = re.compile(
    r'^[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+'  # "First Last" or "First M. Last"
    r'(?:\s+(?:Jr\.?|Sr\.?|II|III|IV))?'
    r'[,\s]+(?:University|College|Institute|Department|School|Center|'
    r'Faculty|Professor|Dr\.|PhD|Research)',
    re.IGNORECASE,
)


def _is_chrome_line(line: str) -> bool:
    """Return True if a line looks like page scaffolding, not evidence."""
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) < 60 and _CHROME_SHORT_RE.match(stripped):
        return True
    if _CHROME_LINE_RE.match(stripped):
        return True
    # Very short lines with mostly uppercase tend to be headers/labels
    if len(stripped) <= 30 and stripped.upper() == stripped and stripped.replace(" ", "").isalpha():
        return True
    # Author + institution metadata lines: "Nathaniel R. King, University of Arkansas"
    if len(stripped) < 120 and _AUTHOR_INSTITUTION_RE.match(stripped):
        return True
    return False


def strip_page_chrome(text: str) -> str:
    """Remove repository/navigation/metadata chrome from extracted article text.

    Strips lines that match navigation, breadcrumb, or metadata patterns.
    Preserves all substantive text. Never removes actual sentence content.
    Designed to clean up Digital Commons / law review repository pages and
    similar academic repository front-matter before card cutting.
    """
    if not text:
        return text
    lines = text.splitlines()
    result_lines: list[str] = []
    # Track consecutive chrome lines at the start to skip them
    initial_chrome_done = False
    consecutive_chrome = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Empty lines pass through
        if not stripped:
            result_lines.append(line)
            continue

        is_chrome = _is_chrome_line(stripped)

        if not initial_chrome_done:
            if is_chrome:
                consecutive_chrome += 1
                continue  # Drop early chrome lines
            else:
                # First non-chrome line — chrome zone is over
                initial_chrome_done = True
                consecutive_chrome = 0

        # After initial chrome zone: drop obvious chrome lines, but be more conservative
        # (don't drop lines that might be real evidence mid-article)
        if is_chrome and len(stripped) < 80:
            continue

        result_lines.append(line)

    cleaned = "\n".join(result_lines)
    # Remove leading/trailing blank lines
    cleaned = cleaned.strip()
    return cleaned


def find_evidence_start_index(text: str, claim: str = "", slot_context: str = "") -> int:
    """Return the char index where substantive evidence likely begins.

    Skips leading page-chrome / metadata lines to find the first line that
    reads like a real evidence-bearing sentence. Returns 0 if nothing to skip.

    Strategy:
    1. Skip lines that match chrome patterns.
    2. When we hit a line that:
       - has >= 8 words, AND
       - contains a sentence starter (causal verb, date, named entity, claim overlap), OR
       - ends with a period and is > 80 chars
       → that is likely the evidence start.
    3. Hard cap: if we haven't found evidence in the first 50 lines, start from line 0.
    """
    if not text:
        return 0

    # Build vocabulary for evidence detection
    claim_words = set(re.sub(r'[^\w\s]', ' ', (claim + " " + slot_context).lower()).split())
    claim_words = {w for w in claim_words if len(w) > 4}

    _EVIDENCE_STARTERS = re.compile(
        r'^(?:Since|Because|Although|However|Despite|The|This|These|Those|In|At|By|For|With|'
        r'During|After|Before|Following|According|Research|Studies|Data|Evidence|'
        r'Rwanda|Kosovo|Bosnia|Libya|Iraq|Syria|Sudan|Cambodia|'
        r'[A-Z][a-z]+\s+[A-Z]|'  # Proper noun sequences
        r'\d{4}|\d+\s+(?:percent|million|billion|thousand))',
        re.IGNORECASE,
    )

    lines = text.split('\n')
    char_pos = 0
    best_start = 0
    found = False

    for i, line in enumerate(lines[:60]):  # check up to first 60 lines
        stripped = line.strip()
        if i < 50 and not found:
            is_chrome = _is_chrome_line(stripped)
            words = stripped.split()
            n_words = len(words)

            if not is_chrome and n_words >= 6:
                # Check if this looks like evidence
                line_lower = stripped.lower()
                has_claim_overlap = bool(claim_words & set(re.sub(r'[^\w\s]', ' ', line_lower).split()))
                has_starter = bool(_EVIDENCE_STARTERS.match(stripped))
                is_long_sentence = n_words >= 12 and stripped.endswith('.')
                has_causal = any(w in line_lower for w in (
                    "because", "therefore", "thus", "hence", "enables", "prevents",
                    "causes", "leads", "results", "demonstrates", "shows", "proves",
                    "genocide", "atrocity", "intervention", "violation", "rights",
                    "court", "held", "ruled", "law", "statute", "treaty",
                ))

                if has_claim_overlap or has_starter or is_long_sentence or has_causal:
                    best_start = char_pos
                    found = True
                    break

        char_pos += len(line) + 1  # +1 for '\n'

    return best_start


def clean_card_body_text(text: str) -> tuple[str, list[str]]:
    """Normalize scraped body text for presentation. Returns (cleaned, warnings).

    Safe: only changes whitespace and leading/trailing punctuation artifacts.
    Never removes or paraphrases words. Warnings report if cleanup was aggressive.
    """
    if not text:
        return "", []
    warnings: list[str] = []

    # 1. Join hard line-wraps (single newline within a paragraph)
    cleaned = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    # 2. Normalize multiple spaces/tabs
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

    # 3. Collapse multiple blank lines to double newline
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    # 4. Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    # 5. Remove leading stray punctuation (scraping artifact)
    leading_punct = re.match(r'^[,;:\-–—]\s*', cleaned)
    if leading_punct:
        cleaned = cleaned[leading_punct.end():].lstrip()
        warnings.append("Leading punctuation artifact removed from card start")

    # 6. Check for broken extraction (mostly numbers/symbols)
    word_chars = len(re.findall(r'[a-zA-Z]', cleaned))
    total_chars = len(cleaned)
    if total_chars > 20 and word_chars / total_chars < 0.4:
        warnings.append("Extraction may be broken — unusual character distribution")

    return cleaned, warnings


# ── Cut finalization: annotations, bold spans, confidence/warnings (Part 4) ──

_BOLD_CAUSAL_VERBS = frozenset({
    "causes", "cause", "enables", "enable", "creates", "create", "prevents",
    "prevent", "grants", "provides", "shields", "increases", "reduces",
    "permits", "requires", "leads",
})


def _select_bold_spans(cut: EvidenceCutResult) -> list[SelectedSpan]:
    """Pick the most important phrases within the cut (subset of selected_spans).

    Highlights spans containing named entities (capitalized proper nouns),
    statistics/numbers with units, causal verbs, or claim-aligned concepts.
    """
    bold: list[SelectedSpan] = []
    for span in cut.selected_spans:
        text = span.text
        low = text.lower()
        has_stat = bool(re.search(r"\d+(?:[.,]\d+)?\s*(?:%|percent|million|billion|trillion)", low)) \
            or bool(re.search(r"\b(19|20)\d{2}\b", text)) \
            or bool(re.search(r"\d{3,}", text))
        has_causal = any(v in low.split() for v in _BOLD_CAUSAL_VERBS)
        # Proper noun: a capitalized word that is not the first word of the span
        words = text.split()
        has_proper = any(
            w[:1].isupper() and w[1:2].islower() and len(w) > 2
            for w in words[1:]
        )
        if has_stat or has_causal or has_proper:
            bold.append(span)
    # If nothing matched but we have spans, bold the single longest span.
    if not bold and cut.selected_spans:
        bold = [max(cut.selected_spans, key=lambda s: len(s.text))]
    return bold


def _finalize_cut(
    cut: EvidenceCutResult,
    is_snippet: bool = False,
    claim: str = "",
    evidence_role: str = "",
) -> EvidenceCutResult:
    """Attach annotated spans (prefix/suffix), bold spans, confidence, warnings,
    and cut-body-relative spans for card-body highlighting."""
    original = cut.original_passage
    annotated: list[AnnotatedSpan] = []
    for span in cut.selected_spans:
        prefix = original[max(0, span.start - 20):span.start]
        suffix = original[span.end:span.end + 20]
        annotated.append(AnnotatedSpan(
            id=_uuid.uuid4().hex,
            start=span.start, end=span.end, text=span.text,
            sentence_index=span.sentence_index, rationale=span.rationale,
            selected_by="ai", confidence=cut.confidence,
            prefix=prefix, suffix=suffix,
        ))
    cut.annotated_spans = annotated

    bold = _select_bold_spans(cut)
    cut.bold_spans = bold

    warnings: list[str] = []
    valid_spans = [s for s in cut.selected_spans if original.find(s.text) != -1]
    if len(valid_spans) < 2:
        cut.cut_confidence = 0.3
        warnings.append("Only one span selected — cut may be too thin")
    else:
        cut.cut_confidence = round(min(1.0, 0.5 + 0.1 * len(valid_spans)), 2)

    if cut.compression_ratio < 0.2:
        warnings.append("Very aggressive cut — verify context not lost")
    if not any((s.rationale or "").strip() for s in cut.selected_spans):
        warnings.append("Cut based on heuristic scoring")
    if is_snippet:
        warnings.append("Snippet-only source — cut may be incomplete")
    # Disconnected quotes: any non-adjacent gap between consecutive spans
    spans_sorted = sorted(cut.selected_spans, key=lambda s: s.start)
    disconnected = any(
        original[spans_sorted[i - 1].end:spans_sorted[i].start].strip()
        for i in range(1, len(spans_sorted))
    )
    if disconnected and len(spans_sorted) > 1:
        warnings.append("Disconnected quotes — check coherence")

    cut.cut_warnings = warnings

    # ── Part 4b: Remap spans to cut_body offsets for card-body highlighting ──
    cut_body = cut.cut_text_with_ellipses or cut.cut_text or ""
    if cut_body:
        # Clean the cut body text for presentation
        cleaned_body, cleanup_warnings = clean_card_body_text(cut_body)
        if cleanup_warnings:
            cut.cut_warnings = (cut.cut_warnings or []) + cleanup_warnings
        if cleaned_body != cut_body:
            cut.cut_text_with_ellipses = cleaned_body
            cut.cut_text = cleaned_body
            cut_body = cleaned_body

        # Remap selected_spans to cut_body offsets
        remapped = remap_spans_to_cut_body(cut_body, cut.selected_spans)
        remapped_bold = remap_spans_to_cut_body(cut_body, cut.bold_spans)

        # If remapping failed (cut is same as original, so spans already in range), use as-is
        if not remapped and cut.selected_spans:
            # Try deterministic highlight fallback
            remapped = get_deterministic_highlight_spans(cut_body, claim, evidence_role)
            remapped_bold = []
        elif remapped and not remapped_bold:
            # Compute bold from remapped
            remapped_bold = remap_spans_to_cut_body(cut_body, cut.bold_spans)

        # Final fallback: if still no highlights, generate deterministic ones
        if not remapped and len(cut_body) > 50:
            remapped = get_deterministic_highlight_spans(cut_body, claim, evidence_role)

        cut.cut_body_spans = remapped
        cut.cut_body_bold_spans = remapped_bold

    return cut


def generate_evidence_cut(
    passage: str,
    claim: str,
    evidence_role: str,
    tag: str = "",
    use_llm: bool = True,
    preferred_cut_style: Optional[str] = None,
    is_snippet_source: bool = False,
) -> EvidenceCutResult:
    """Select the strongest sentences/phrases from a passage and build a debate card cut.

    The final body text is always exact source text — selected spans joined with [...]
    where text is omitted. Never paraphrases.

    preferred_cut_style: one of "full" | "light" | "medium" | "aggressive".
      - "full"       returns the entire passage uncut.
      - "light"      keeps most context (target ratio 0.85).
      - "medium"     existing default behavior (target ratio 0.60).
      - "aggressive" prefers short cuts (target ratio 0.35).

    This function never raises — any unexpected error returns a full-passage fallback.
    """
    _safe_passage = (passage or "").strip()
    if not _safe_passage:
        return EvidenceCutResult(
            original_passage=passage or "", cut_text=passage or "",
            cut_text_with_ellipses=passage or "", compression_ratio=1.0,
            cut_style="full", validation_passed=False,
            cut_warnings=["Empty passage — nothing to cut"],
        )
    try:
        return _generate_evidence_cut_inner(
            _safe_passage, claim, evidence_role, tag,
            use_llm, preferred_cut_style, is_snippet_source,
        )
    except Exception as exc:
        logger.warning("generate_evidence_cut unexpected error (%s) — returning full passage", exc)
        return EvidenceCutResult(
            original_passage=_safe_passage, cut_text=_safe_passage,
            cut_text_with_ellipses=_safe_passage, compression_ratio=1.0,
            cut_style="full", validation_passed=False,
            cut_warnings=[f"Cut generation failed: {exc}"],
        )


def _generate_evidence_cut_inner(
    passage: str,
    claim: str,
    evidence_role: str,
    tag: str,
    use_llm: bool,
    preferred_cut_style: Optional[str],
    is_snippet_source: bool,
) -> EvidenceCutResult:
    sentence_spans = _split_sentences(passage)
    if not sentence_spans:
        return _finalize_cut(EvidenceCutResult(
            original_passage=passage, cut_text=passage,
            cut_text_with_ellipses=passage, compression_ratio=1.0, cut_style="full",
        ), is_snippet_source, claim, evidence_role)

    # "full" style: return the entire passage uncut.
    if preferred_cut_style == "full":
        return _finalize_cut(
            _full_passage_cut(passage, sentence_spans), is_snippet_source, claim, evidence_role,
        )

    target_ratio = _CUT_STYLE_TARGET_RATIO.get(preferred_cut_style or "", 0.60)

    # If only 1-3 sentences, return full passage
    if len(sentence_spans) <= 3:
        return _finalize_cut(
            _full_passage_cut(passage, sentence_spans), is_snippet_source, claim, evidence_role,
        )

    # Try LLM phrase-level selection first
    if use_llm:
        _style_hint = _CUT_STYLE_LLM_HINT.get(preferred_cut_style or "", "")
        llm_result = _select_sentences_with_llm(
            passage, sentence_spans, claim, evidence_role, tag, style_hint=_style_hint,
        )
        if llm_result is not None and llm_result.selected_spans:
            phrase_cut = _validate_and_build_phrase_cut(passage, llm_result.selected_spans)
            if phrase_cut is not None:
                return _finalize_cut(phrase_cut, is_snippet_source, claim, evidence_role)

    # Deterministic fallback: score each sentence/clause and take top ones
    return _finalize_cut(
        _deterministic_cut(passage, sentence_spans, claim, target_ratio=target_ratio),
        is_snippet_source, claim, evidence_role,
    )


# ── Citation enrichment ───────────────────────────────────────────────────────

# Law review / repository / known credible domain patterns
# Maps domain substring → publication/container label
_LAW_REVIEW_PATTERNS = {
    # Law reviews + repositories
    "digitalcommons.": "Digital Commons repository",
    "repository.law.": "Law school repository",
    "lawreview.": "Law review",
    "jlp.law.": "Journal of Law & Policy",
    "law.review": "Law review",
    "scholarship.law.": "Law school scholarship",
    "commons.law.": "Law school commons",
    "ssrn.com": "Social Science Research Network",
    "papers.ssrn.com": "SSRN Working Paper",
    "law.yale.edu": "Yale Law",
    "law.harvard.edu": "Harvard Law",
    "law.stanford.edu": "Stanford Law",
    "law.columbia.edu": "Columbia Law",
    "harvardlawreview.org": "Harvard Law Review",
    "yalelawjournal.org": "Yale Law Journal",
    "stanfordlawreview.org": "Stanford Law Review",
    "journals.law.harvard.edu": "Harvard Law journal",
    "repository.jmls.edu": "JMLS Repository",
    "chicagounbound.uchicago.edu": "U Chicago Law repository",
    # Philosophy encyclopedias
    "iep.utm.edu": "Internet Encyclopedia of Philosophy",
    "plato.stanford.edu": "Stanford Encyclopedia of Philosophy",
    # Think tanks + policy
    "carnegieendowment.org": "Carnegie Endowment for International Peace",
    "cfr.org": "Council on Foreign Relations",
    "rand.org": "RAND Corporation",
    "brookings.edu": "Brookings Institution",
    "pewresearch.org": "Pew Research Center",
    # International orgs
    "un.org": "United Nations",
    "ohchr.org": "UN Human Rights Office",
    "icrc.org": "International Committee of the Red Cross",
    "hrw.org": "Human Rights Watch",
    "amnesty.org": "Amnesty International",
    # U.S. Government
    "congress.gov": "U.S. Congress",
    "crsreports.congress.gov": "Congressional Research Service",
    "gao.gov": "U.S. Government Accountability Office",
    "law.cornell.edu": "Cornell Legal Information Institute",
}

# Journal title patterns
_JOURNAL_TITLE_RE = re.compile(
    r'(Journal of [A-Za-z &]+|[A-Za-z]+ Law Review|[A-Za-z]+ Law Journal|'
    r'[A-Za-z]+ Quarterly|[A-Za-z]+ Review)',
    re.IGNORECASE,
)

# Vol/issue from URL path, e.g. /vol23/iss2/
_VOL_ISS_RE = re.compile(r'/vol(\d+)/(?:iss(\d+)/)?', re.IGNORECASE)

# Author extraction from text
_AUTHOR_BY_RE = re.compile(r'^(?:By|Author:?)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*)', re.MULTILINE)

# Year at the beginning of text
_YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')


def _lookup_crossref_doi(doi: str, timeout: float = 5.0) -> Optional[dict]:
    """Query Crossref REST API for DOI metadata.

    Only called when doi is non-empty. Returns raw work dict or None on failure.
    Crossref lookup is best-effort — absence never breaks local dev.
    """
    if not doi.strip():
        return None
    try:
        import httpx
        clean_doi = doi.strip()
        # Strip common prefixes
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if clean_doi.startswith(prefix):
                clean_doi = clean_doi[len(prefix):]
                break
        resp = httpx.get(
            f"https://api.crossref.org/works/{clean_doi}",
            headers={"User-Agent": "RoundLab/1.0 (mailto:support@roundlab.app)"},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("message", {})
    except Exception as exc:
        logger.debug("Crossref lookup failed for DOI %s: %s", doi[:40], exc)
    return None


def _enrich_from_crossref(citation: CitationMetadata, crossref_data: dict) -> CitationMetadata:
    """Update a CitationMetadata with Crossref data."""
    if not crossref_data:
        return citation

    # Author
    if not citation.author_display and crossref_data.get("author"):
        authors = crossref_data["author"]
        if authors:
            first = authors[0]
            surname = first.get("family", "")
            if surname:
                citation.author_display = surname
                if len(authors) > 1:
                    citation.author_display += " et al."
                citation.authors = [
                    f"{a.get('family', '')} {a.get('given', '')}".strip()
                    for a in authors
                ]

    # Year
    if not citation.year:
        issued = crossref_data.get("issued", {}).get("date-parts", [[]])[0]
        if issued:
            citation.year = str(issued[0])

    # Title
    if not citation.title and crossref_data.get("title"):
        t = crossref_data["title"]
        citation.title = t[0] if isinstance(t, list) else t

    # Container title (journal name)
    if not citation.container_title and crossref_data.get("container-title"):
        ct = crossref_data["container-title"]
        citation.container_title = ct[0] if isinstance(ct, list) else ct
        citation.publication_name = citation.publication_name or citation.container_title

    return citation


def enrich_citation_metadata(
    url: str,
    author: Optional[str],
    title: Optional[str],
    publication: Optional[str],
    published_date: Optional[str],
    extracted_text: str = "",
    doi: str = "",
    html_content: Optional[str] = None,
    citation_provenance: Optional[dict] = None,
) -> CitationMetadata:
    """Build structured citation from available metadata. Always returns something safe.

    html_content (optional): raw page HTML — used to mine meta tags / JSON-LD for
    missing fields. citation_provenance (optional): a dict recording where each
    field originated (author_source, date_source, …). Both degrade gracefully.
    """
    from urllib.parse import urlparse as _up
    from datetime import datetime

    provenance: dict = dict(citation_provenance or {})

    # ── Optional metadata cascade from HTML (meta tags → JSON-LD → org heuristic)
    if html_content:
        try:
            from app.services.web_article_extraction import extract_metadata_from_html
            mined = extract_metadata_from_html(url, html_content, {})
            mined_prov = mined.get("provenance", {}) or {}
            if not author and mined.get("author"):
                author = mined["author"]
                provenance.setdefault("author_source", mined_prov.get("author", "meta_tags"))
            if not title and mined.get("title"):
                title = mined["title"]
                provenance.setdefault("title_source", mined_prov.get("title", "meta_tags"))
            if not published_date and mined.get("date"):
                published_date = mined["date"]
                provenance.setdefault("date_source", mined_prov.get("date", "meta_tags"))
            if not publication and mined.get("publication"):
                publication = mined["publication"]
                provenance.setdefault("publication_source", mined_prov.get("publication", "meta_tags"))
        except Exception as exc:
            logger.debug("HTML metadata cascade failed: %s", exc)

    # Extract domain
    try:
        domain = _up(url).netloc.lower().lstrip("www.")
    except Exception:
        domain = ""

    # ── Known domain → publication/container mapping ─────────────────────────
    law_pub_name: str = ""
    for pattern, label in _LAW_REVIEW_PATTERNS.items():
        if pattern in domain or pattern in url.lower():
            law_pub_name = label
            break

    # ── Extract container_title from article title ────────────────────────────
    container_title = law_pub_name  # default to domain-derived label when known
    if title:
        m = _JOURNAL_TITLE_RE.search(title)
        if m:
            container_title = m.group(0)  # specific journal from title wins

    # ── Volume/issue from URL ────────────────────────────────────────────────
    vol_str = ""
    m_vi = _VOL_ISS_RE.search(url)
    if m_vi:
        vol_num = m_vi.group(1)
        iss_num = m_vi.group(2)
        vol_str = f"vol. {vol_num}"
        if iss_num:
            vol_str += f", no. {iss_num}"

    # Author normalization
    author_display = ""
    authors: list[str] = []
    if author:
        raw = author.strip()
        authors = [a.strip() for a in raw.replace(" and ", ";").replace("&", ";").split(";") if a.strip()]
        if authors:
            first_auth = authors[0]
            if "," in first_auth:
                # "Last, First" format — take the part before the comma
                author_display = first_auth.split(",")[0].strip()
            else:
                # "First Last" format — take the last token (surname)
                parts_auth = first_auth.split()
                author_display = parts_auth[-1] if parts_auth else first_auth
            if len(authors) > 1:
                author_display += " et al."

    # ── Try to extract author from beginning of extracted_text ───────────────
    if not author_display and extracted_text:
        text_head = extracted_text[:500]
        m_auth = _AUTHOR_BY_RE.search(text_head)
        if m_auth:
            author_display = m_auth.group(1).split()[-1]  # take surname
            authors = [m_auth.group(1)]

    # ── Organization-as-author heuristic for known credible domains ──────────
    if not author_display:
        try:
            from app.services.web_article_extraction import organization_author_for_url
            org = organization_author_for_url(url)
            if org:
                author_display = org
                authors = [org]
                provenance.setdefault("author_source", "organization_heuristic")
        except Exception:
            pass

    # Year extraction
    year = ""
    if published_date:
        m_yr = re.search(r'(19|20)\d{2}', published_date)
        if m_yr:
            year = m_yr.group(0)

    # ── Fallback year from extracted_text ────────────────────────────────────
    if not year and extracted_text:
        text_head = extracted_text[:300]
        m_yr2 = _YEAR_RE.search(text_head)
        if m_yr2:
            year = m_yr2.group(0)

    # Accessed date
    accessed = datetime.now().strftime("%d %b. %Y")

    # Publication name (prefer explicit publication, then law_pub_name, then domain)
    pub_name = publication or law_pub_name or domain or ""

    # Citation quality
    has_author = bool(author_display)
    has_year = bool(year)
    has_title = bool(title)
    has_pub = bool(pub_name)

    score = sum([has_author, has_year, has_title, has_pub])
    if score >= 3:
        quality: str = "complete"
    elif score >= 2:
        quality = "partial"
    else:
        quality = "weak"

    # MLA citation
    # Format: Author. "Title." Publication, Year, URL.
    mla_parts: list[str] = []
    if author_display:
        mla_parts.append(f"{author_display}.")
    if title:
        mla_parts.append(f'"{title}."')
    if pub_name:
        mla_parts.append(f"{pub_name},")
    if vol_str:
        mla_parts.append(f"{vol_str},")
    if year:
        mla_parts.append(f"{year},")
    if url:
        mla_parts.append(url + ".")
    if not has_author and url:
        # No author: end with "Accessed DATE."
        mla_parts.append(f"Accessed {accessed}.")

    mla = " ".join(mla_parts).replace(",.", ".").replace(",,", ",")
    # Hard fallback: MLA must never be empty when we have a URL or domain
    if not mla.strip():
        _fallback_label = pub_name or domain or "Source"
        _fallback_parts = [f"{_fallback_label}."]
        if url:
            _fallback_parts.append(url + ".")
        _fallback_parts.append(f"Accessed {accessed}.")
        mla = " ".join(_fallback_parts)

    # Short cite
    if author_display and year:
        short_cite = f"{author_display} {year}"
    elif author_display:
        short_cite = author_display
    elif pub_name:
        short_cite = pub_name[:30]
    else:
        short_cite = domain or "Source"

    citation = CitationMetadata(
        author_display=author_display,
        authors=authors,
        year=year,
        title=title or "",
        container_title=container_title,
        publication_name=pub_name,
        url=url,
        doi=doi,
        accessed_date=accessed,
        citation_quality=quality,  # type: ignore[arg-type]
        mla_citation=mla,
        short_cite=short_cite,
        author_source=provenance.get("author_source", "search_provider" if author_display else "missing"),
        date_source=provenance.get("date_source", "search_provider" if year else "missing"),
        title_source=provenance.get("title_source", "search_provider" if title else "missing"),
        publication_source=provenance.get("publication_source", "search_provider" if pub_name else "missing"),
    )

    # ── Optional Crossref DOI enrichment ─────────────────────────────────────
    if doi and quality != "complete":
        crossref_data = _lookup_crossref_doi(doi)
        if crossref_data:
            citation = _enrich_from_crossref(citation, crossref_data)
            # Recompute citation_quality after enrichment
            has_author2 = bool(citation.author_display)
            has_year2 = bool(citation.year)
            has_title2 = bool(citation.title)
            has_pub2 = bool(citation.publication_name)
            score2 = sum([has_author2, has_year2, has_title2, has_pub2])
            if score2 >= 3:
                citation.citation_quality = "complete"
            elif score2 >= 2:
                citation.citation_quality = "partial"
            else:
                citation.citation_quality = "weak"
            # Rebuild short_cite if enrichment provided new info
            if citation.author_display and citation.year:
                citation.short_cite = f"{citation.author_display} {citation.year}"
            elif citation.author_display:
                citation.short_cite = citation.author_display

    return citation


# ── Card intelligence (deterministic, no LLM) ─────────────────────────────────

_ROLE_WHY_TEMPLATES: dict[str, str] = {
    "direct_support": (
        "This passage directly states that {claim}. Use it as your core warrant "
        "in a constructive or extension."
    ),
    "mechanism_support": (
        "This passage explains the mechanism by which {claim}. Pair with an impact "
        "card to complete your argument."
    ),
    "example_support": (
        "This passage provides a real-world case or precedent supporting {claim}. "
        "Use in rebuttal to show practical application."
    ),
    "impact_support": (
        "This passage describes the harm or impact of {claim}. Use in impact "
        "calculus or weighing."
    ),
    "definition_support": (
        "This passage offers a definition that frames how {claim} should be "
        "interpreted. Use to control the debate framework."
    ),
    "authority_support": (
        "This passage provides expert or institutional backing for {claim}. Use to "
        "boost your credibility on this argument."
    ),
    "counter_evidence": (
        "This passage argues against your position. Use it as a pre-empt or to write "
        "a frontline response."
    ),
}

_ROLE_BEST_USE: dict[str, str] = {
    "direct_support": "contention",
    "mechanism_support": "rebuttal",
    "example_support": "crossfire",
    "impact_support": "weighing",
    "definition_support": "definition",
    "authority_support": "frontline",
    "counter_evidence": "frontline",
}

_ROLE_DEBATE_NOTES: dict[str, str] = {
    "mechanism_support": "Pair with an impact card for complete argument",
    "example_support": "Useful in crossfire or rebuttal to show real-world application",
    "impact_support": "Use in final focus impact comparison",
    "definition_support": "Run in first constructive to control interpretive framework",
    "counter_evidence": "Write a frontline or pre-empt block to address this",
    "direct_support": "Extend this in second rebuttal if opponents don't answer it",
}

# Part 9 — likely opponent responses by evidence role
_ROLE_OPPONENT_RESPONSE: dict[str, str] = {
    "direct_support": "Opponents may challenge the source's bias or claim this is isolated evidence.",
    "mechanism_support": "Opponents may argue the mechanism doesn't apply to all cases or is disputed.",
    "example_support": "Opponents may argue the case is unique/irrelevant to the resolution or happened in a different context.",
    "impact_support": "Opponents may weigh this impact differently or argue it's overstated.",
    "definition_support": "Opponents may offer a competing definition or argue yours is self-serving.",
    "authority_support": "Opponents may question the author's credentials or cite a conflicting authority.",
    "counter_evidence": "This already argues against you — expect opponents to read it directly.",
}

# Part 9 — useful crossfire questions by evidence role
_ROLE_CROSSFIRE_QUESTION: dict[str, str] = {
    "example_support": "Can you read the specific text of your case card?",
    "authority_support": "Who wrote this card and what are their credentials?",
    "mechanism_support": "What evidence do you have that this mechanism is still operative?",
    "impact_support": "How do you weigh this impact against your opponent's impact?",
    "direct_support": "What part of the card actually proves your claim?",
    "definition_support": "Why should we prefer your definition over the standard one?",
    "counter_evidence": "Doesn't this card actually cut against your own position?",
}

# Part 9 — slot-function-aware "why this card" lead-ins
_SLOT_FUNCTION_WHY: dict[str, str] = {
    "legal/doctrinal support": "This card provides legal/doctrinal backing for {claim}.",
    "moral/philosophical warrant": "This card supplies the moral/philosophical warrant for {claim}.",
    "historical example": "This historical case supports {claim} with a concrete precedent.",
    "empirical impact/stakes": "This card establishes the empirical stakes behind {claim}.",
    "answer to objection": "This card establishes the conditions or pre-empt needed to defend {claim}.",
    "definition/background": "This card frames the background/definition underpinning {claim}.",
    "mechanism/warrant": "This card explains the mechanism by which {claim} holds.",
    "direct support": "This card directly supports {claim}.",
    "authority/credibility support": "This card lends expert/institutional credibility to {claim}.",
}


def derive_card_intelligence(
    evidence_role: str,
    best_supported_claim: str,
    overclaim_warning: str,
    source_quality: str,
    debate_usefulness_score: float,
    is_snippet_source: bool,
    citation_quality: str,
    compression_ratio: float,
    cut_style: str,
    is_counter_evidence: bool,
    claim: str = "",
    slot_label: str = "",
    slot_target_claim: str = "",
    slot_function: str = "",
) -> CardIntelligence:
    """Derive debate-intelligence annotations from card metadata without an LLM call.

    slot_label/slot_target_claim/slot_function carry evidence-set planner context
    so notes can be tailored to the strategic slot the card fills.
    """
    claim_phrase = (slot_target_claim or best_supported_claim or claim or "")[:80] or "this argument"

    # why_this_card — prefer slot-function-aware lead-in when available
    slot_template = _SLOT_FUNCTION_WHY.get(slot_function) if slot_function else None
    if slot_template:
        why = slot_template.format(claim=claim_phrase)
    else:
        template = _ROLE_WHY_TEMPLATES.get(
            evidence_role,
            "This passage supports the claim: {claim}.",
        )
        if evidence_role == "counter_evidence":
            why = template  # no {claim} placeholder
        else:
            why = template.format(claim=claim_phrase)

    # best_use
    best_use = _ROLE_BEST_USE.get(evidence_role, "contention")

    # supports_claim_because
    supports: list[str] = []
    if debate_usefulness_score >= 7.0:
        supports.append("High debate usefulness score ({:.1f}/10)".format(debate_usefulness_score))
    if evidence_role in ("direct_support", "mechanism_support"):
        supports.append("Directly advances the core argument")
    if source_quality in ("high", "peer_reviewed"):
        supports.append("Credible source ({})".format(source_quality))
    supports = supports[:2]

    # limitations
    limitations: list[str] = []
    if overclaim_warning:
        limitations.append(overclaim_warning)
    if is_snippet_source:
        limitations.append("Partial source text — verify the full original before saving")
    if citation_quality == "weak":
        limitations.append("Citation is incomplete — add author/year before tournament use")
    if compression_ratio < 0.25:
        limitations.append("Very aggressive cut — check that context is not distorted")

    # debate_use_notes
    debate_notes: list[str] = []
    note = _ROLE_DEBATE_NOTES.get(evidence_role)
    if note:
        debate_notes.append(note)

    # suggested_block_label — prefer the slot label as the strategic header
    role_label = (evidence_role or "evidence").replace("_", " ").title()
    label_claim = (best_supported_claim or claim or "")[:50]
    if slot_label:
        suggested_block_label = f"{slot_label} — {label_claim}".rstrip(" —")
    else:
        suggested_block_label = f"Pro {role_label} — {label_claim}".rstrip(" —")

    # save_readiness
    good_citation = citation_quality in ("complete", "partial")
    good_quality = source_quality in ("high", "peer_reviewed", "medium")
    no_overclaim = not overclaim_warning
    if good_citation and not is_snippet_source and no_overclaim and good_quality:
        readiness = "ready"
    elif is_snippet_source and citation_quality == "weak":
        readiness = "weak"
    else:
        readiness = "review_needed"

    # save_readiness_reasons
    reasons: list[str] = []
    if readiness == "ready":
        reasons = ["Citation complete", "Full source extracted", "Tag is debate-appropriate"]
    elif readiness == "weak":
        if is_snippet_source:
            reasons.append("Snippet-only source")
        if citation_quality == "weak":
            reasons.append("Incomplete citation")
    else:  # review_needed
        if not good_citation:
            reasons.append("Incomplete citation")
        if is_snippet_source:
            reasons.append("Snippet-only source")
        if overclaim_warning:
            reasons.append("Overclaim warning")
        if not good_quality:
            reasons.append("Low source quality")
        if not reasons:
            reasons.append("Review before saving")

    opponent_response = _ROLE_OPPONENT_RESPONSE.get(evidence_role, "")
    crossfire_question = _ROLE_CROSSFIRE_QUESTION.get(evidence_role, "")
    if crossfire_question and "[opponent's impact]" in crossfire_question:
        crossfire_question = crossfire_question.replace("[opponent's impact]", "your opponent's impact")

    return CardIntelligence(
        why_this_card=why,
        supports_claim_because=supports,
        best_use=best_use,  # type: ignore[arg-type]
        debate_use_notes=debate_notes,
        limitations=limitations,
        suggested_block_label=suggested_block_label,
        save_readiness=readiness,  # type: ignore[arg-type]
        save_readiness_reasons=reasons,
        opponent_response=opponent_response,
        crossfire_question=crossfire_question,
    )


# ── LLM card drafting ─────────────────────────────────────────────────────────

def _draft_with_llm(
    article: ExtractedArticle,
    topic: str,
    claim_goal: str,
    side: Optional[str],
) -> Optional[_CardCuttingOutput]:
    """Call OpenAI to select a passage and suggest card metadata.
    Returns None on any failure — caller should use fallback."""
    try:
        from openai import OpenAI

        client = OpenAI()
        text_for_llm = article.extracted_text[:_MAX_ARTICLE_CHARS]
        side_str = f"Side: {side}" if side else "Side: not specified"

        system_msg = (
            "You are a Public Forum debate evidence card cutter helping a student find "
            "a card-worthy passage.\n\n"
            "CRITICAL RULES:\n"
            "- body_start_idx and body_end_idx MUST be exact character positions in the article text.\n"
            "- Do NOT modify, rephrase, or add anything to the source passage.\n"
            "- Span start/end values are character offsets WITHIN the body text "
            "(i.e., body_text = article[body_start_idx:body_end_idx]; "
            "span 0 maps to body_text[0]).\n"
            "- If no strong passage exists, set body_start_idx = -1 and body_end_idx = -1.\n"
            "- The tag must be debater-written active-voice, 10-20 words. "
            "Write it as a COMPLETE SPECIFIC CLAIM grounded in what this passage actually says. "
            "NEVER write the tag in the format '<concept> — <role>' or '<topic> — support'. "
            "GOOD tag examples: "
            "'Section 230 grants platforms blanket immunity from civil liability for user content' "
            "or 'Backpage court ruling shows Section 230 shields platforms from trafficking lawsuits'. "
            "BAD tag examples: 'Section 230 — direct support' or 'Internet law — mechanism support'.\n"
        )
        user_msg = (
            f"Topic: {topic}\n"
            f"Claim goal: {claim_goal}\n"
            f"{side_str}\n\n"
            f"Article text:\n{text_for_llm}"
        )

        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            response_format=_CardCuttingOutput,
            max_tokens=800,
        )
        return response.choices[0].message.parsed
    except Exception as exc:
        logger.warning("LLM card cutting failed: %s", exc)
        return None


# ── Fallback passage selection ────────────────────────────────────────────────

def _fallback_passage(article: ExtractedArticle, topic: str, claim_goal: str) -> str:
    """Select best passage without LLM using heuristic scoring.

    Applies chrome stripping and preamble skipping before paragraph selection.
    """
    # Skip leading preamble to find where real evidence starts
    ev_start = find_evidence_start_index(article.extracted_text, claim_goal, topic)
    stripped_at_ev_start = article.extracted_text[ev_start:] if ev_start > 0 else article.extracted_text

    # Strip page chrome before splitting into paragraphs
    clean_text = strip_page_chrome(stripped_at_ev_start)
    paragraphs = _split_paragraphs(clean_text)
    if not paragraphs:
        # Fallback to chrome-stripped first 600 chars
        return clean_text[:600] if clean_text else article.extracted_text[:600]

    scored = [
        (p, _score_paragraph(p, claim_goal, topic))
        for p in paragraphs
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    # Drop paragraphs with very negative scores (pure chrome)
    positive = [(p, s) for p, s in scored if s > -1.0]
    if not positive:
        positive = scored  # fallback if all scored poorly

    best = positive[0][0]
    # Extend to roughly 400 chars if very short
    if len(best) < 120 and len(positive) > 1:
        best = best + "\n\n" + positive[1][0]
    return best[:1500]


def _build_cite(
    author: Optional[str],
    publication: Optional[str],
    published_date: Optional[str],
    url: str,
    title: Optional[str],
) -> str:
    """Build a compact citation line from available metadata."""
    parts: list[str] = []
    if author:
        parts.append(author)
    if publication:
        parts.append(publication)
    if published_date:
        year_match = re.search(r"(19|20)\d{2}", published_date)
        if year_match:
            parts.append(year_match.group())
    if title and len(title) <= 80:
        parts.append(f'"{title}"')
    if not parts:
        # Only URL available
        return url
    cite = " · ".join(parts)
    return cite


# ── Debate tag generation (Part 5) ────────────────────────────────────────────

_MECHANISM_VERBS = (
    "grants", "provides", "shields", "allows", "enables", "prevents", "requires",
    "permits", "protects", "immunizes", "authorizes", "guarantees", "creates",
)
_CASE_VERBS = (
    "ruled", "held", "found", "dismissed", "decided", "affirmed", "struck",
    "upheld", "convicted", "acquitted", "ordered",
)
_IMPACT_TERMS = (
    "deaths", "killed", "harm", "cost", "billion", "million", "percent", "%",
    "casualties", "displaced", "victims", "crisis",
)

_GENERIC_TAG_RE = re.compile(r"^\s*\S.*\s+[—-]\s+(direct|mechanism|example|impact|"
                             r"definition|authority|counter)\s+support\s*$", re.IGNORECASE)


def _first_sentence_with(passage: str, terms: tuple) -> str:
    """Return the first sentence containing any of `terms`, or ''."""
    for sent in _split_sentences(passage):
        low = sent.text.lower()
        if any(t in low for t in terms):
            return sent.text.strip()
    return ""


def _truncate_words(text: str, max_words: int = 20) -> str:
    """Truncate to max_words on a word boundary (never mid-word)."""
    words = text.split()
    if len(words) <= max_words:
        return text.strip().rstrip(".")
    return " ".join(words[:max_words]).rstrip(",;:").rstrip()


def _deterministic_tag(passage: str, claim: str, evidence_role: str) -> str:
    """Build a grounded debate tag from the passage without an LLM."""
    candidate = ""
    if evidence_role == "mechanism_support":
        candidate = _first_sentence_with(passage, _MECHANISM_VERBS)
    elif evidence_role == "example_support":
        candidate = _first_sentence_with(passage, _CASE_VERBS)
    elif evidence_role == "impact_support":
        candidate = _first_sentence_with(passage, _IMPACT_TERMS)

    if not candidate:
        # Fall back to the first substantial sentence of the passage.
        sents = _split_sentences(passage)
        candidate = next((s.text for s in sents if len(s.text.split()) >= 5), "")
    if not candidate:
        candidate = (claim or passage)[:120]

    tag = _truncate_words(candidate, 20)
    # Never start with "Evidence:"
    if tag.lower().startswith("evidence:"):
        tag = tag.split(":", 1)[1].strip()
    return tag or (claim or "")[:120]


def generate_debate_tag(
    passage: str,
    claim: str,
    evidence_role: str,
    slot_label: str = "",
    slot_target_claim: str = "",
    use_llm: bool = True,
) -> tuple[str, Optional[str]]:
    """Generate a specific, debate-ready tag grounded in the passage.

    Returns (tag, overclaim_warning_or_None). The tag never uses the
    '<topic> — <role>' format and never starts with 'Evidence:'.
    Degrades gracefully to a deterministic tag.
    """
    overclaim: Optional[str] = None

    if use_llm:
        try:
            from openai import OpenAI
            from pydantic import BaseModel as _BM

            class _TagOut(_BM):
                tag: str
                overclaim_warning: str = ""

            target = slot_target_claim or claim
            slot_ctx = f"\nThis card fills the slot: {slot_label}." if slot_label else ""
            client = OpenAI()
            resp = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Generate a specific, debate-ready 12-20 word tag that states "
                            f"exactly what this passage proves about: {target}. "
                            "NEVER use the format '<topic> — <role>'. NEVER start with 'Evidence:'. "
                            "The tag must be grounded only in what the passage actually says. "
                            "If the passage proves less than the target claim, note it in overclaim_warning."
                        ),
                    },
                    {"role": "user", "content": f"{slot_ctx}\nPassage:\n{passage[:1500]}"},
                ],
                response_format=_TagOut,
                temperature=0,
                max_tokens=160,
            )
            parsed = resp.choices[0].message.parsed
            if parsed and parsed.tag.strip():
                tag = parsed.tag.strip()
                if not tag.lower().startswith("evidence:") and not _GENERIC_TAG_RE.match(tag):
                    return tag, (parsed.overclaim_warning.strip() or None)
        except Exception as exc:
            logger.debug("generate_debate_tag LLM failed: %s", exc)

    return _deterministic_tag(passage, claim, evidence_role), overclaim


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_card_draft(
    article: ExtractedArticle,
    topic: str,
    claim_goal: str,
    side: Optional[str] = None,
    user_id: str = "",
    source_quality: Optional[SourceQuality] = None,
    credibility_notes: Optional[str] = None,
    slot_id: str = "",
    slot_label: str = "",
    slot_target_claim: str = "",
) -> dict:
    """Generate a card draft dict from an ExtractedArticle.

    The body_text field contains ONLY extracted source text. It is never
    modified, rephrased, or extended by the LLM.

    slot_id/slot_label/slot_target_claim carry evidence-set planner context so
    tags and notes can be slot-aware.

    Returns a dict ready for insertion into card_drafts table.
    """
    llm_out = _draft_with_llm(article, topic, claim_goal, side)

    # ── Extract body_text from source ─────────────────────────────────────
    body_text: str = ""
    highlight_spans: list[dict] = []
    underline_spans: list[dict] = []
    tag: str = ""
    warrant_summary: str = ""
    impact_summary: str = ""
    extraction_confidence = article.extraction_confidence

    if llm_out and llm_out.body_start_idx >= 0 and llm_out.body_end_idx > llm_out.body_start_idx:
        # Strip page chrome before using LLM-selected offsets, since the LLM
        # may have selected into chrome zones if the text had lots of preamble.
        full_text = strip_page_chrome(article.extracted_text)
        # Adjust indices — they were relative to original, so use original if chrome
        # stripping changed length, fall back to original text.
        if len(full_text) < len(article.extracted_text) * 0.5:
            full_text = article.extracted_text  # too much stripped; use original
        start = max(0, min(llm_out.body_start_idx, len(full_text)))
        end   = max(start, min(llm_out.body_end_idx, len(full_text)))
        candidate = full_text[start:end].strip()

        if len(candidate) >= _MIN_BODY_CHARS:
            body_text = candidate
            tag = llm_out.tag or ""
            warrant_summary = llm_out.warrant_summary or ""
            impact_summary  = llm_out.impact_summary or ""
            extraction_confidence = min(1.0, article.extraction_confidence * (1.0 + llm_out.confidence * 0.2))

            # Verify spans — drop any that don't map to valid offsets within body_text
            raw_highlights = [h.model_dump() for h in llm_out.highlight_spans]
            raw_underlines = [u.model_dump() for u in llm_out.underline_spans]
            highlight_spans = verify_spans(body_text, raw_highlights)
            underline_spans = verify_spans(body_text, raw_underlines)

    if not body_text:
        body_text = _fallback_passage(article, topic, claim_goal)

    # ── Build cite ────────────────────────────────────────────────────────
    meta = article.metadata
    cite = _build_cite(
        author=meta.author,
        publication=meta.publication,
        published_date=meta.published_date,
        url=article.url,
        title=meta.title,
    )

    # ── Track missing metadata ────────────────────────────────────────────
    missing: dict = {}
    if not meta.author:
        missing["author"] = "Author not found"
    if not meta.published_date:
        missing["date"] = "Publication date not found"
    if not meta.publication:
        missing["publication"] = "Publication name not found"
    if not tag:
        tag, _ = generate_debate_tag(
            body_text, claim_goal, "direct_support",
            slot_label, slot_target_claim, use_llm=False,
        )

    return {
        "user_id": user_id,
        "url": article.url or None,
        "topic": topic,
        "claim_goal": claim_goal,
        "side": side,
        "tag": tag,
        "cite": cite,
        "body_text": body_text,
        "highlighted_spans_json": highlight_spans,
        "underline_spans_json": underline_spans,
        "author": meta.author,
        "publication": meta.publication,
        "title": meta.title,
        "published_date": meta.published_date,
        "warrant_summary": warrant_summary or None,
        "impact_summary": impact_summary or None,
        "source_quality": source_quality,
        "credibility_notes": credibility_notes,
        "extraction_confidence": round(extraction_confidence, 3),
        "generated_tag": True,
        "missing_metadata_json": missing,
        "card_source_type": "url" if article.url else "manual_paste",
        "status": "draft",
        "slot_id": slot_id,
        "slot_label": slot_label,
    }
