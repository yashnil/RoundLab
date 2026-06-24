"""Pass 17 — Concession and contradiction detection.

Replaces simple keyword matching with a combined deterministic approach.
Supports: explicit, partial, qualified concessions; evasions; contradictions.

Key principle: not every polite agreement is a full concession.
Low-confidence findings are suggestions, not definitive flow events.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ConcessionFinding:
    type: str  # "explicit", "partial", "qualified", "evasion", "contradiction",
               # "agreement_on_fact", "non_concession_agreement"
    speaker_side: str
    target_argument_label: Optional[str]
    transcript_span: str        # exact text excerpt from the answer
    confidence: str             # "high", "medium", "low"
    strategic_effect: str       # human-readable explanation for the coach
    requires_confirmation: bool # True for low-confidence / ambiguous findings
    detected_at_index: int      # char index in the answer where the trigger was found


# ---------------------------------------------------------------------------
# Internal patterns
# ---------------------------------------------------------------------------

# --- Explicit concession ---
_EXPLICIT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bI(?:'ll)?\s+concede\b", re.IGNORECASE),
    re.compile(r"\bI\s+admit\b", re.IGNORECASE),
    re.compile(r"\bI\s+grant\b", re.IGNORECASE),
    re.compile(r"\byou(?:'re| are)\s+(?:completely\s+)?right\b", re.IGNORECASE),
    re.compile(r"\bI(?:'ll)?\s+concede\s+that\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:concede|admit|grant)\b", re.IGNORECASE),
    re.compile(r"\bthat\s+(?:point\s+)?(?:is|was)\s+correct\b", re.IGNORECASE),
]

# --- Partial concession ---
_PARTIAL_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bto\s+some\s+extent\b", re.IGNORECASE),
    re.compile(r"\bthat(?:'s| is)\s+partially\s+true\b", re.IGNORECASE),
    re.compile(r"\bin\s+some\s+cases\b", re.IGNORECASE),
    re.compile(r"\bthere(?:'s| is)\s+some\s+truth\s+to\b", re.IGNORECASE),
    re.compile(r"\bpartially\s+(?:correct|right|agree)\b", re.IGNORECASE),
    re.compile(r"\bto\s+a\s+(?:certain|limited)\s+degree\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:partially|somewhat)\s+agree\b", re.IGNORECASE),
    re.compile(r"\bsomewhat\s+(?:true|correct|accurate)\b", re.IGNORECASE),
]

# --- Qualified concession: polite phrase + rebuttal pivot ---
# These look like concessions but then pivot with "but", "however", "though", etc.
_QUALIFIED_PIVOTS = re.compile(
    r"(?P<phrase>"
    r"(?:that(?:'s| is)\s+fair"
    r"|true\s+in\s+theory"
    r"|I\s+acknowledge"
    r"|I\s+understand"
    r"|I\s+see\s+your\s+point"
    r"|I\s+recognize"
    r"|I\s+(?:agree|concede)\s+that)"
    r")"
    r".{0,80}"
    r"(?P<pivot>\bbut\b|\bhowever\b|\bthough\b|\byet\b|\bstill\b|\bnevertheless\b|\bnonetheless\b)",
    re.IGNORECASE | re.DOTALL,
)

# --- Non-concession agreement (polite phrases with NO rebuttal) ---
# These are common phrases that are NOT concessions.
_NON_CONCESSION_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\s*that(?:'s| is)\s+(?:a\s+)?(?:fair|good|great|interesting)\s+(?:question|point|observation)\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*I\s+see\s+your\s+point\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:good|great|interesting)\s+(?:question|point)\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*sure\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*of\s+course\.?\s*$", re.IGNORECASE),
]

# Non-concession anchors (any match anywhere in short responses)
_NON_CONCESSION_ANCHORS: List[re.Pattern] = [
    re.compile(r"\bthat(?:'s| is)\s+(?:a\s+good|an?\s+interesting)\s+(?:question|point)\b", re.IGNORECASE),
    re.compile(r"\bI\s+see\s+your\s+point\b", re.IGNORECASE),
]

# --- Agreement on fact (yes/right + factual X, no impact) ---
_FACT_AGREEMENT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:right|yes|correct),?\s+(?:\w+\s+){1,6}(?:happened|occurred|is|was|are|were)\b", re.IGNORECASE),
    re.compile(r"\b(?:yes|right),?\s+(?:that(?:'s| is))\s+(?:accurate|correct|true)\b", re.IGNORECASE),
    re.compile(r"\byes,?\s+X\s+is\s+true\b", re.IGNORECASE),
]

# --- Evasion ---
_EVASION_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bI(?:'ll)?\s+(?:get|come\s+back)\s+to\s+that\b", re.IGNORECASE),
    re.compile(r"\bthat(?:'s| is)\s+not\s+(?:what\s+I\s+said|the\s+question)\b", re.IGNORECASE),
    re.compile(r"\byou(?:'re| are)\s+misrepresenting\b", re.IGNORECASE),
    re.compile(r"\bI(?:'ll)?\s+have\s+to\s+(?:check|look\s+into)\b", re.IGNORECASE),
    re.compile(r"\bnext\s+question\b", re.IGNORECASE),
    re.compile(r"\bmaybe\b.{0,30}\bmaybe\s+not\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bthat(?:'s| is)\s+(?:a\s+)?different\s+(?:topic|argument|issue|point)\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:already|just)\s+(?:addressed|answered|covered)\s+that\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:can\s+)?(?:discuss|talk\s+about)\s+that\s+later\b", re.IGNORECASE),
]

# --- Contradiction markers ---
_NEGATION_REVERSAL_PATTERNS: List[re.Pattern] = [
    # "X is not Y" when they previously said "X is Y"
    re.compile(r"\b(?:is|are|was|were)\s+not\b", re.IGNORECASE),
    re.compile(r"\bno\s+(?:longer|more)\b", re.IGNORECASE),
    re.compile(r"\bactually\b.{0,40}\b(?:isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:never|nowhere)\s+(?:said|claimed|argued|stated)\b", re.IGNORECASE),
    re.compile(r"\bopposite\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:never|didn't)\s+(?:say|claim|argue)\b", re.IGNORECASE),
]

# Stopwords for snippet extraction
_WINDOW = 80  # characters of context around a match


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_span(text: str, match: re.Match, window: int = _WINDOW) -> str:
    """Return a readable excerpt around the match position."""
    start = max(0, match.start() - 10)
    end = min(len(text), match.end() + window)
    span = text[start:end].strip()
    return span


def _word_count(text: str) -> int:
    return len(text.split())


def _has_direct_answer(text: str) -> bool:
    """Check if text contains words that indicate a direct yes/no stance."""
    direct = re.compile(
        r"\b(?:yes|no|I\s+agree|I\s+disagree|correct|incorrect|that(?:'s| is)\s+(?:right|wrong))\b",
        re.IGNORECASE,
    )
    return bool(direct.search(text))


def _is_plain_non_concession(text: str) -> bool:
    """Return True if the entire answer is a stock polite phrase with no substance."""
    stripped = text.strip()
    for pat in _NON_CONCESSION_PATTERNS:
        if pat.match(stripped):
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_concessions(
    answer_text: str,
    speaker_side: str,
    target_argument_label: Optional[str],
    prior_positions: List[str],
) -> List[ConcessionFinding]:
    """Detect concessions, evasions, and agreement types in a crossfire answer.

    Parameters
    ----------
    answer_text:
        The raw answer given by the speaker.
    speaker_side:
        "pro" or "con" (which side is answering).
    target_argument_label:
        The label of the argument the question targeted (may be None).
    prior_positions:
        A list of prior claim strings from this speaker, used for contradiction
        checks (passed through to detect_contradiction separately).

    Returns
    -------
    A list of ConcessionFinding. May be empty. Multiple findings are possible
    (e.g. a qualified statement that is also partially evasive).
    """
    findings: List[ConcessionFinding] = []
    text = answer_text.strip()

    # Guard: completely empty answer
    if not text:
        findings.append(
            ConcessionFinding(
                type="evasion",
                speaker_side=speaker_side,
                target_argument_label=target_argument_label,
                transcript_span="[no answer provided]",
                confidence="high",
                strategic_effect="Speaker provided no response — counts as a full evasion on flow.",
                requires_confirmation=False,
                detected_at_index=0,
            )
        )
        return findings

    # -----------------------------------------------------------------------
    # 1. Check for plain non-concession polite phrases FIRST (before anything
    #    else so they don't get misclassified as concessions).
    # -----------------------------------------------------------------------
    if _is_plain_non_concession(text):
        # Find the triggering anchor
        idx = 0
        for pat in _NON_CONCESSION_ANCHORS:
            m = pat.search(text)
            if m:
                idx = m.start()
                break
        findings.append(
            ConcessionFinding(
                type="non_concession_agreement",
                speaker_side=speaker_side,
                target_argument_label=target_argument_label,
                transcript_span=text[:120],
                confidence="low",
                strategic_effect=(
                    "Polite acknowledgment only — not a concession. "
                    "No flow credit; argument still live."
                ),
                requires_confirmation=True,
                detected_at_index=idx,
            )
        )
        return findings

    # -----------------------------------------------------------------------
    # 2. Explicit concessions — HIGHEST priority, checked before word-count
    # -----------------------------------------------------------------------
    for pat in _EXPLICIT_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(
                ConcessionFinding(
                    type="explicit",
                    speaker_side=speaker_side,
                    target_argument_label=target_argument_label,
                    transcript_span=_extract_span(text, m),
                    confidence="high",
                    strategic_effect=(
                        f"Speaker explicitly conceded{'on ' + target_argument_label if target_argument_label else ''}. "
                        "This is a full concession — record on the flow."
                    ),
                    requires_confirmation=False,
                    detected_at_index=m.start(),
                )
            )
            # One explicit match is enough — return early (highest signal)
            return findings

    # -----------------------------------------------------------------------
    # 3. Short answer without a direct stance → evasion (< 15 words)
    # -----------------------------------------------------------------------
    wc = _word_count(text)
    if wc < 15 and not _has_direct_answer(text):
        findings.append(
            ConcessionFinding(
                type="evasion",
                speaker_side=speaker_side,
                target_argument_label=target_argument_label,
                transcript_span=text[:120],
                confidence="medium",
                strategic_effect=(
                    f"Answer is only {wc} words and does not directly address "
                    "the question. Likely evasion — judge may notice."
                ),
                requires_confirmation=True,
                detected_at_index=0,
            )
        )
        # For very short answers, don't continue to partial/qualified checks
        if wc < 8:
            return findings

    # -----------------------------------------------------------------------
    # 4. Qualified concession (polite phrase + pivot)
    # -----------------------------------------------------------------------
    m = _QUALIFIED_PIVOTS.search(text)
    if m:
        findings.append(
            ConcessionFinding(
                type="qualified",
                speaker_side=speaker_side,
                target_argument_label=target_argument_label,
                transcript_span=_extract_span(text, m, window=120),
                confidence="medium",
                strategic_effect=(
                    "Speaker acknowledged the point but then pivoted with a rebuttal. "
                    "This is a qualified concession — the argument is still partially live."
                ),
                requires_confirmation=True,
                detected_at_index=m.start(),
            )
        )
        return findings

    # -----------------------------------------------------------------------
    # 5. Partial concession
    # -----------------------------------------------------------------------
    for pat in _PARTIAL_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(
                ConcessionFinding(
                    type="partial",
                    speaker_side=speaker_side,
                    target_argument_label=target_argument_label,
                    transcript_span=_extract_span(text, m),
                    confidence="medium",
                    strategic_effect=(
                        "Speaker acknowledged part of the argument. "
                        "Partial concession — record the conceded portion but the full impact is still contested."
                    ),
                    requires_confirmation=False,
                    detected_at_index=m.start(),
                )
            )
            return findings

    # -----------------------------------------------------------------------
    # 6. Agreement on a fact (not on the argument impact)
    # -----------------------------------------------------------------------
    for pat in _FACT_AGREEMENT_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(
                ConcessionFinding(
                    type="agreement_on_fact",
                    speaker_side=speaker_side,
                    target_argument_label=target_argument_label,
                    transcript_span=_extract_span(text, m),
                    confidence="medium",
                    strategic_effect=(
                        "Speaker agreed on a factual premise but has NOT conceded the argument's "
                        "impact or the causal link. Impact is still contested."
                    ),
                    requires_confirmation=True,
                    detected_at_index=m.start(),
                )
            )
            return findings

    # -----------------------------------------------------------------------
    # 7. Non-concession polite anchors anywhere in a longer response
    # -----------------------------------------------------------------------
    for pat in _NON_CONCESSION_ANCHORS:
        m = pat.search(text)
        if m:
            findings.append(
                ConcessionFinding(
                    type="non_concession_agreement",
                    speaker_side=speaker_side,
                    target_argument_label=target_argument_label,
                    transcript_span=_extract_span(text, m),
                    confidence="low",
                    strategic_effect=(
                        "Polite acknowledgment detected within a longer answer. "
                        "Not a concession — verify that speaker followed with a substantive rebuttal."
                    ),
                    requires_confirmation=True,
                    detected_at_index=m.start(),
                )
            )
            return findings

    # -----------------------------------------------------------------------
    # 8. Evasion patterns
    # -----------------------------------------------------------------------
    for pat in _EVASION_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(
                ConcessionFinding(
                    type="evasion",
                    speaker_side=speaker_side,
                    target_argument_label=target_argument_label,
                    transcript_span=_extract_span(text, m),
                    confidence="medium",
                    strategic_effect=(
                        "Speaker avoided directly answering the question. "
                        "Evasion recorded — the questioner may press in a follow-up."
                    ),
                    requires_confirmation=True,
                    detected_at_index=m.start(),
                )
            )
            return findings

    # -----------------------------------------------------------------------
    # No finding — return empty list (normal, substantive rebuttal)
    # -----------------------------------------------------------------------
    return findings


def detect_contradiction(
    new_statement: str,
    prior_statements: List[str],
    argument_label: Optional[str] = None,
) -> Optional[ConcessionFinding]:
    """Detect if new_statement contradicts any prior statement.

    Uses simple heuristics:
    - Negation patterns applied to prior claim content
    - "never said / didn't say" reversals
    - Factual reversal markers

    Confidence is always "medium" — deterministic detection is imperfect.

    Returns a ConcessionFinding of type "contradiction" or None.
    """
    if not new_statement or not prior_statements:
        return None

    new_lower = new_statement.lower()

    # Build a compact version of the new statement for comparison
    new_words = set(re.findall(r"\b\w{4,}\b", new_lower))

    for prior in prior_statements:
        if not prior:
            continue
        prior_lower = prior.lower()
        prior_words = set(re.findall(r"\b\w{4,}\b", prior_lower))

        # Overlap: at least 2 content words in common (same topic)
        overlap = new_words & prior_words
        if len(overlap) < 2:
            continue

        # Check whether any negation/reversal pattern fires on the new statement
        # in context of a prior claim
        for pat in _NEGATION_REVERSAL_PATTERNS:
            m = pat.search(new_statement)
            if m:
                span_start = max(0, m.start() - 10)
                span_end = min(len(new_statement), m.end() + 80)
                span = new_statement[span_start:span_end].strip()
                label_note = f" on {argument_label}" if argument_label else ""
                return ConcessionFinding(
                    type="contradiction",
                    speaker_side="unknown",  # caller should set appropriately
                    target_argument_label=argument_label,
                    transcript_span=span,
                    confidence="medium",
                    strategic_effect=(
                        f"Possible contradiction detected{label_note}: "
                        f"new statement appears to reverse a prior position. "
                        f"Prior: «{prior[:120]}». "
                        "Verify before recording on flow — deterministic detection may produce false positives."
                    ),
                    requires_confirmation=True,
                    detected_at_index=m.start(),
                )

    return None
