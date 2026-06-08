"""Deterministic PF debate signal detection.

Pure functions — no LLM calls, no network, no I/O.
Detects debate-rule violations and quality indicators from raw transcript text.

Used by feedback_generation.py:
  1. Before LLM call — inject detected signals into the user message.
  2. After LLM call — drives IssueCalibrator to fix missed signals and suppress FPs.
"""

from __future__ import annotations

import re
from pydantic import BaseModel


# ── Data models ────────────────────────────────────────────────────────────────

class DebateSignal(BaseModel):
    """A single detected debate signal from transcript analysis."""

    issue_type: str
    """Canonical issue_type (matches VALID_ISSUE_TYPES in evals/models.py)."""

    confidence: str
    """'high' | 'medium' | 'low'"""

    evidence: str
    """Short excerpt or description from the transcript that triggered detection."""

    reason: str
    """Human-readable explanation of why this signal was detected."""


class QualityGateReport(BaseModel):
    """Quality indicators derived from transcript structure."""

    has_named_evidence: bool
    """True if transcript contains a named org/author plus year (e.g., 'RAND 2023')."""

    has_clear_warrant_language: bool
    """True if transcript contains explicit causal mechanism language."""

    has_impact_language: bool
    """True if transcript contains clear impact/consequence framing."""

    recommended_issue_budget: int
    """0–4: how many structured issues the LLM should be allowed to generate.
    0 = strong speech, do not invent issues.
    4 = weak speech, full budget."""


class DebateSignalReport(BaseModel):
    """Output of detect_debate_signals — feeds into prompt injection and calibration."""

    speech_type: str
    signals: list[DebateSignal]
    quality_gate: QualityGateReport


# ── Pattern constants ──────────────────────────────────────────────────────────

# Late-speech signals: new evidence/arguments introduced in final_focus or summary
_NEW_ARGUMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bnew evidence from\b", re.IGNORECASE),
    re.compile(r"\bnew card from\b", re.IGNORECASE),
    re.compile(r"\bnew source\b", re.IGNORECASE),
    re.compile(r"\bnew study\b", re.IGNORECASE),
    re.compile(r"\bnew analysis from\b", re.IGNORECASE),
    re.compile(r"\bfor the first time\b", re.IGNORECASE),
    re.compile(r"\bnewly released\b", re.IGNORECASE),
    re.compile(r"\bbrand.new evidence\b", re.IGNORECASE),
    re.compile(r"\bnew impact\b", re.IGNORECASE),
]

# Terms indicating opponent engagement in rebuttal/summary
# Note: avoid generic " rebut" since "our rebuttal" matches but is NOT opponent engagement
_OPPONENT_ENGAGEMENT_TERMS: list[str] = [
    "opponent", "their case", "they say", "they argue", "they claim",
    "con says", "pro says", "aff says", "neg says", "affirmative says",
    "negative says", " response to", " turn their", "frontline",
    "rebut their", "rebutting their", "answer their",
    "on their contention", "on their c1", "on their c2",
    "cross-apply", "their evidence", "their card",
    "they drop", "their warrant", "their impact", "my opponents",
    "affirmative's", "negative's", "their argument", "they never",
]

# Terms indicating own-case restatement (high = restating own case, not engaging opponent)
_OWN_CASE_TERMS: list[str] = [
    "our first contention", "our second contention", "our c1", "our c2",
    "we show", "our argument", "our case", "our evidence",
    "our impact", "extend our", "our warrant", "our contention",
    "we stand on", "we stand firmly",
]

# Vague attribution patterns (signal weak evidence quality)
_VAGUE_EVIDENCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bstudies show\b", re.IGNORECASE),
    re.compile(r"\bexperts say\b", re.IGNORECASE),
    re.compile(r"\bexperts agree\b", re.IGNORECASE),
    re.compile(r"\bresearch shows\b", re.IGNORECASE),
    re.compile(r"\bresearch proves\b", re.IGNORECASE),
    re.compile(r"\bdata shows\b", re.IGNORECASE),
    re.compile(r"\bmany reports\b", re.IGNORECASE),
    re.compile(r"\bsome reports\b", re.IGNORECASE),
    re.compile(r"\beconomists agree\b", re.IGNORECASE),
    re.compile(r"\bscholars believe\b", re.IGNORECASE),
    re.compile(r"\bscientists believe\b", re.IGNORECASE),
    re.compile(r"\bit is widely (?:known|accepted|believed)\b", re.IGNORECASE),
    re.compile(r"\baccording to experts\b", re.IGNORECASE),
    re.compile(r"\baccording to (?:some|many|various) (?:analysts|experts|scholars)\b", re.IGNORECASE),
    re.compile(r"\bunnamed source", re.IGNORECASE),
    re.compile(r"\bsome analysts\b", re.IGNORECASE),
    re.compile(r"\bmany believe\b", re.IGNORECASE),
    re.compile(r"\bit is generally (?:accepted|known|believed)\b", re.IGNORECASE),
    re.compile(r"\bvarious (?:think tank|reports?|studies?|scholars?)\b", re.IGNORECASE),
]

# Named institution patterns — nearby institution names mean evidence is NOT vague
_NAMED_INSTITUTION_RE = re.compile(
    r"\b(?:"
    r"RAND|Carnegie|Harvard|MIT|Stanford|Oxford|Yale|Princeton|Columbia|Georgetown|"
    r"Heritage Foundation|Brookings|Peterson Institute|Cato Institute|Urban Institute|"
    r"Belfer Center|CSIS|Atlantic Council|Council on Foreign Relations|CFR|"
    r"IMF|World Bank|NATO|WHO|WTO|UN(?:\b)|CBO|OMB|BLS|CDC|NIH|NSF|"
    r"Reuters|AP|Associated Press|BBC|Financial Times|Wall Street Journal|"
    r"Asan Institute|RAND Corporation|Carnegie Endowment"
    r")\b",
    re.IGNORECASE,
)

# Named institution WITH a year — the gold standard for verifiable evidence
_NAMED_WITH_YEAR_RE = re.compile(
    r"(?:"
    r"RAND|Carnegie|Harvard|Belfer|CSIS|Peterson|Heritage|"
    r"IMF|World Bank|Brookings|CBO|CDC|NIH|NSF|Asan"
    r")[\w\s,]*?\b(20\d{2}|19\d{2})\b",
    re.IGNORECASE,
)

# Explicit causal / warrant language
_WARRANT_LANGUAGE_RE = re.compile(
    r"\b(?:the warrant is|the mechanism is|because\b|this means that|"
    r"leads to|causes\b|therefore\b|as a result\b|consequently\b|"
    r"the reason is|creating\b|triggers?\b|produces?\b)\b",
    re.IGNORECASE,
)

# Impact / consequence framing
_IMPACT_LANGUAGE_RE = re.compile(
    r"\b(?:the impact is|impact\b|harm\b|consequence\b|this means\b|"
    r"ultimately\b|at risk\b|breaks down\b|will suffer\b|"
    r"voting issue\b|decisive\b|escalation\b|deterrence\b)\b",
    re.IGNORECASE,
)

# Extension language — indicates debater is forwarding an argument rather than re-explaining it
_EXTENSION_TERMS: list[str] = [
    "extend our", "extend this", "extend the", "extend it",
    "bring through", "carry through", "bring this", "still stands",
    "still access", "vote off", "this argument still", "our contention still",
    "this still applies", "extend and", "extend c1", "extend c2",
    "extend their", "extend both", "cross-apply our",
]

# Warrant re-establishment phrases — debater explains WHY the argument is true
# Stricter than _WARRANT_LANGUAGE_RE: requires explicit mechanism labeling or
# a causal chain explanation clearly tied to the extended argument.
_WARRANT_REESTABLISHMENT_RE = re.compile(
    r"\b(?:"
    r"the warrant is\b|the mechanism (?:is|shows|explains|here)\b|the internal link\b|"
    r"explains why\b|because (?:this|the|of|when|if)\b|"
    r"the reason (?:is|why)\b|therefore\b|consequently\b|"
    r"which means\b|as a result\b|this means that\b|this is because\b|"
    r"establish(?:es|ing)? that\b|demonstrat(?:es|ing)? that\b|show(?:s|ing)? that\b|"
    r"this (?:proves?|confirms?)\b|in other words\b|"
    r"the (?:link|connection) (?:is|between)\b"
    r")",
    re.IGNORECASE,
)

# Explicit mechanism phrases for missing_warrant detection — much stricter than quality gate
# Only matches when the debater explicitly labels a warrant/mechanism or explains a causal chain
_EXPLICIT_MECHANISM_RE = re.compile(
    r"\b(?:"
    r"the warrant is\b|the mechanism is\b|the internal link\b|"
    r"this (?:happens?|works?) because\b|the reason (?:is|why)\b|"
    r"this means that\b|as a direct result\b|which causes\b|"
    r"therefore (?:the|this)\b|because of (?:this|these)\b|"
    r"the causal chain\b|mechanism (?:here|of)\b|"
    r"establish(?:es|ing)? that\b|demonstrat(?:es|ing)? that\b"
    r")",
    re.IGNORECASE,
)


# ── Public utility ────────────────────────────────────────────────────────────

def has_named_evidence(text: str) -> bool:
    """Return True if the transcript contains a named org/author plus year combo."""
    return bool(_NAMED_WITH_YEAR_RE.search(text))


# ── Individual detectors ───────────────────────────────────────────────────────

def _detect_new_argument(text: str, speech_type: str) -> DebateSignal | None:
    """Detect new evidence/arguments introduced in final_focus or summary."""
    if speech_type not in ("final_focus", "summary"):
        return None
    for pat in _NEW_ARGUMENT_PATTERNS:
        m = pat.search(text)
        if m:
            start = max(0, m.start() - 15)
            end = min(len(text), m.end() + 80)
            snippet = text[start:end].strip().replace("\n", " ")
            return DebateSignal(
                issue_type="new_argument",
                confidence="high",
                evidence=snippet,
                reason=(
                    f"'{m.group(0)}' detected in {speech_type} — "
                    "PF rules prohibit introducing new evidence/arguments in late speeches."
                ),
            )
    return None


def _detect_no_clash(text: str, speech_type: str) -> DebateSignal | None:
    """Detect failure to engage opponent — only in rebuttal speeches.

    Summaries and final focus legitimately extend own case; no_clash
    is a rebuttal-specific strategic failure.
    """
    if speech_type != "rebuttal":
        return None
    text_lower = text.lower()
    engagement = sum(1 for t in _OPPONENT_ENGAGEMENT_TERMS if t in text_lower)
    own_case = sum(1 for t in _OWN_CASE_TERMS if t in text_lower)

    if engagement == 0 and own_case >= 2:
        return DebateSignal(
            issue_type="no_clash",
            confidence="high",
            evidence=f"(opponent engagement terms: {engagement}, own-case restatement terms: {own_case})",
            reason=(
                f"This {speech_type} restates the team's own case "
                "without directly engaging any opponent arguments."
            ),
        )
    if engagement <= 1 and own_case >= 3:
        return DebateSignal(
            issue_type="no_clash",
            confidence="medium",
            evidence=f"(opponent engagement: {engagement}, own-case: {own_case})",
            reason="Very low opponent engagement relative to own-case restatement.",
        )
    return None


def _detect_weak_extension(text: str, speech_type: str) -> DebateSignal | None:
    """Detect extension-only summaries/final-focus that don't re-establish the warrant.

    Only fires for summary, final_focus (and common spacing/casing variants).
    Never fires for constructive — a constructive should never have extension language.
    """
    late_speech = {"summary", "final_focus", "final focus", "finalfocus"}
    if speech_type.lower().replace("-", "_") not in late_speech and speech_type not in late_speech:
        return None

    text_lower = text.lower()
    extension_hits = [t for t in _EXTENSION_TERMS if t in text_lower]
    if not extension_hits:
        return None

    has_reestablishment = bool(_WARRANT_REESTABLISHMENT_RE.search(text))

    if not has_reestablishment:
        snippet = extension_hits[0][:80]
        return DebateSignal(
            issue_type="weak_extension",
            confidence="high",
            evidence=f"Extension language detected ('{snippet}') with no warrant re-establishment.",
            reason=(
                "The speech extends offense but does not clearly re-establish the "
                "warrant/internal link needed for the judge to evaluate the argument."
            ),
        )

    # Extension language present but warrant re-establishment is very thin
    # (only one warrant phrase vs multiple extension terms)
    reest_count = len(_WARRANT_REESTABLISHMENT_RE.findall(text))
    if reest_count <= 1 and len(extension_hits) >= 2:
        snippet = extension_hits[0][:80]
        return DebateSignal(
            issue_type="weak_extension",
            confidence="medium",
            evidence=f"Extension language detected ('{snippet}') with minimal warrant re-establishment.",
            reason=(
                "The speech extends multiple arguments but re-establishes warrants/internal links "
                "only briefly. The judge may lack enough warrant depth to evaluate the extension."
            ),
        )

    return None


def _detect_missing_warrant(text: str, speech_type: str) -> DebateSignal | None:
    """Detect constructive speeches that assert claims/impacts without a causal mechanism.

    Only fires for constructive speeches. Does not fire when the speech has
    strong named evidence + causal language + impact language (budget-0 quality gate).
    """
    if speech_type != "constructive":
        return None

    # Don't flag strong constructives (named evidence + warrant + impact all present)
    if (has_named_evidence(text)
            and bool(_WARRANT_LANGUAGE_RE.search(text))
            and bool(_IMPACT_LANGUAGE_RE.search(text))):
        return None

    # Require impact/claim language to be present before flagging
    if not _IMPACT_LANGUAGE_RE.search(text):
        return None

    mechanism_count = len(_EXPLICIT_MECHANISM_RE.findall(text))
    impact_hits = len(_IMPACT_LANGUAGE_RE.findall(text))

    if mechanism_count == 0 and impact_hits >= 1:
        return DebateSignal(
            issue_type="missing_warrant",
            confidence="high",
            evidence=(
                f"(impact language hits: {impact_hits}, "
                f"explicit mechanism phrases: {mechanism_count})"
            ),
            reason=(
                "The speech asserts a claim/impact relationship but does not explain "
                "the causal mechanism connecting them."
            ),
        )

    if mechanism_count <= 1 and impact_hits >= 2:
        return DebateSignal(
            issue_type="missing_warrant",
            confidence="medium",
            evidence=(
                f"(impact language hits: {impact_hits}, "
                f"explicit mechanism phrases: {mechanism_count})"
            ),
            reason=(
                "The speech has limited causal mechanism explanation relative to "
                "the number of asserted claims."
            ),
        )

    return None


def _detect_weak_evidence(text: str, speech_type: str) -> DebateSignal | None:
    """Detect vague attribution or complete absence of named sources.

    Returns high confidence for explicit vague phrases ('studies show').
    Returns medium confidence for constructive speeches with zero named institutions.
    """
    # Check for explicit vague attribution phrases
    for pat in _VAGUE_EVIDENCE_PATTERNS:
        m = pat.search(text)
        if m:
            # Check if a named institution appears nearby (within ±120 chars)
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 120)
            window = text[start:end]
            if _NAMED_INSTITUTION_RE.search(window):
                continue  # Named institution nearby — not truly vague
            snippet = window.strip().replace("\n", " ")[:120]
            return DebateSignal(
                issue_type="weak_evidence",
                confidence="high",
                evidence=snippet,
                reason=f"Vague attribution detected ('{m.group(0)}') without a named source.",
            )

    # For constructives: check for complete absence of named evidence
    if speech_type == "constructive" and not has_named_evidence(text):
        return DebateSignal(
            issue_type="weak_evidence",
            confidence="medium",
            evidence="(no named institution + year found in constructive)",
            reason=(
                "Constructive speech cites no verifiable named source with a year. "
                "PF contentions need named authors/organizations to be credible."
            ),
        )
    return None


def _assess_quality_gate(text: str, speech_type: str) -> QualityGateReport:
    """Assess speech structure quality and compute recommended issue budget."""
    has_named = has_named_evidence(text)
    has_warrant = bool(_WARRANT_LANGUAGE_RE.search(text))
    has_impact = bool(_IMPACT_LANGUAGE_RE.search(text))

    # Budget: lower = fewer invented issues allowed
    if speech_type == "constructive":
        if has_named and has_warrant and has_impact:
            budget = 0  # Strong constructive — do not invent quality issues
        elif has_named and (has_warrant or has_impact):
            budget = 1
        elif has_named or has_warrant:
            budget = 2
        else:
            budget = 4  # Weak constructive — full issue budget
    else:
        # Non-constructive speeches
        if has_named and has_warrant:
            budget = 2
        elif has_named or has_warrant:
            budget = 3
        else:
            budget = 4

    return QualityGateReport(
        has_named_evidence=has_named,
        has_clear_warrant_language=has_warrant,
        has_impact_language=has_impact,
        recommended_issue_budget=budget,
    )


# ── Main entry point ───────────────────────────────────────────────────────────

def detect_debate_signals(
    transcript: str,
    speech_type: str,
    side: str | None = None,
    judge_type: str | None = None,
) -> DebateSignalReport:
    """Run all deterministic signal detectors on a transcript.

    Pure function — no LLM calls, no network.

    Returns a DebateSignalReport containing:
      - signals: detected rule violations / quality issues
      - quality_gate: quality indicators and recommended issue budget
    """
    signals: list[DebateSignal] = []

    sig = _detect_new_argument(transcript, speech_type)
    if sig:
        signals.append(sig)

    sig = _detect_no_clash(transcript, speech_type)
    if sig:
        signals.append(sig)

    sig = _detect_weak_evidence(transcript, speech_type)
    if sig:
        signals.append(sig)

    sig = _detect_weak_extension(transcript, speech_type)
    if sig:
        signals.append(sig)

    sig = _detect_missing_warrant(transcript, speech_type)
    if sig:
        signals.append(sig)

    quality_gate = _assess_quality_gate(transcript, speech_type)

    return DebateSignalReport(
        speech_type=speech_type,
        signals=signals,
        quality_gate=quality_gate,
    )


# ── Prompt injection helper ────────────────────────────────────────────────────

def format_signal_injection(report: DebateSignalReport) -> str:
    """Build the DETECTED DEBATE SIGNALS block for injection into the user message.

    Returns an empty string if no signals and no quality gate guidance to add.
    """
    lines: list[str] = []

    if report.signals:
        lines.append("DETECTED DEBATE SIGNALS (pre-analysis — act on these):")
        for s in report.signals:
            lines.append(f"  [{s.confidence.upper()}] {s.issue_type}")
            lines.append(f"    Evidence: \"{s.evidence[:100]}\"")
            lines.append(f"    Reason: {s.reason}")
            if s.confidence == "high":
                lines.append(
                    f"    → MANDATORY: include issue_type={s.issue_type} in structured_issues."
                )
            else:
                lines.append(
                    f"    → RECOMMENDED: include issue_type={s.issue_type} if confirmed by transcript."
                )
        lines.append("")

    qg = report.quality_gate
    if qg.recommended_issue_budget == 0:
        lines.append("QUALITY GATE: Strong speech detected (named evidence + warrant + impact).")
        lines.append("  → Do NOT invent structured issues. Only include issues from DETECTED SIGNALS above.")
        lines.append("  → If no signals above: structured_issues should be empty [].")
    elif qg.recommended_issue_budget == 1:
        lines.append("QUALITY GATE: Well-structured speech (budget = 1).")
        lines.append("  → Limit structured_issues to 1 item. Prioritize signal-backed issues.")
    elif not report.signals:
        pass  # No guidance needed for average speeches with no signals

    return "\n".join(lines) if lines else ""
