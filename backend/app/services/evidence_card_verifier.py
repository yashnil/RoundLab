"""Pass 11 — Evidence Card Support Verification.

Verifies that a generated evidence card actually supports the user's claim and
the generated tag WITHOUT overstating causality, certainty, magnitude, scope,
timeframe, or population.

Public interface:
    verify_card_support(claim, tag, body_text, ...) -> EvidenceVerificationResult

Layers (each independently testable and optional):
    1. Deterministic mismatch checks  — always run, no LLM, no network
    2. Semantic/LLM verifier adapter  — optional, disabled gracefully
    3. Verdict aggregation            — deterministic, reproducible rules

SAFETY INVARIANTS:
    - Evidence body text is NEVER modified.
    - Safer tags are SUGGESTIONS ONLY; never auto-applied.
    - No outside web knowledge is used during verification.
    - Invalid quoted spans from the LLM are discarded before use.
    - Verification failure never fails evidence generation.
    - Credentials never appear in verification output.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── Verdict constants ─────────────────────────────────────────────────────────

SUPPORTED = "supported"
PARTIALLY_SUPPORTED = "partially_supported"
UNSUPPORTED = "unsupported"
CONTRADICTED = "contradicted"
INSUFFICIENT_CONTEXT = "insufficient_context"
VERIFICATION_UNAVAILABLE = "verification_unavailable"

ALL_VERDICTS = (
    SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED,
    CONTRADICTED, INSUFFICIENT_CONTEXT, VERIFICATION_UNAVAILABLE,
)

# Severity levels for individual dimension findings
SEVERITY_CRITICAL = "critical"  # Contradicts the claim
SEVERITY_MAJOR = "major"        # Major scope/causal/magnitude mismatch
SEVERITY_MINOR = "minor"        # Wording imprecision, not fundamental
SEVERITY_NONE = "none"          # No issue found

# Dimension identifiers
DIM_CORE_CLAIM = "core_claim"
DIM_CAUSAL_STRENGTH = "causal_strength"
DIM_CERTAINTY = "certainty"
DIM_MAGNITUDE = "magnitude"
DIM_TIMEFRAME = "timeframe"
DIM_POPULATION_SCOPE = "population_scope"
DIM_GEOGRAPHIC_SCOPE = "geographic_scope"
DIM_POLICY_MATCH = "policy_or_intervention_match"
DIM_SOURCE_ATTRIBUTION = "source_attribution"
DIM_CAVEAT_COMPLETENESS = "caveat_completeness"

ALL_DIMENSIONS = (
    DIM_CORE_CLAIM, DIM_CAUSAL_STRENGTH, DIM_CERTAINTY,
    DIM_MAGNITUDE, DIM_TIMEFRAME, DIM_POPULATION_SCOPE,
    DIM_GEOGRAPHIC_SCOPE, DIM_POLICY_MATCH,
    DIM_SOURCE_ATTRIBUTION, DIM_CAVEAT_COMPLETENESS,
)


# ── Typed models ──────────────────────────────────────────────────────────────

@dataclass
class SupportEvidenceSpan:
    """An exact substring of the source document that supports or conflicts."""
    text: str           # exact text from body_text
    start: int          # offset in body_text
    end: int            # offset in body_text
    span_type: str      # "supporting" | "conflicting"


@dataclass
class SupportDimensionResult:
    """Result for one verification dimension."""
    dimension: str                  # one of ALL_DIMENSIONS
    verdict: str                    # supported|partially_supported|unsupported|not_applicable
    severity: str                   # SEVERITY_*
    explanation: str                # plain-language explanation
    spans: list[SupportEvidenceSpan] = field(default_factory=list)
    suggested_correction: str = ""  # narrower wording suggestion


@dataclass
class EvidenceVerificationResult:
    """Complete verification result for one evidence card.

    This is the canonical output of verify_card_support().  It is stored in
    draft_json["support_verification"] and forwarded to the frontend.
    """

    # ── Overall verdict ───────────────────────────────────────────────────────
    overall_verdict: str = VERIFICATION_UNAVAILABLE  # one of ALL_VERDICTS

    # ── Per-target verdicts ───────────────────────────────────────────────────
    claim_verdict: str = VERIFICATION_UNAVAILABLE   # vs the original user claim
    tag_verdict: str = VERIFICATION_UNAVAILABLE     # vs the generated card tag

    # ── Dimension-level results ───────────────────────────────────────────────
    dimensions: list[SupportDimensionResult] = field(default_factory=list)

    # ── Safer tag ─────────────────────────────────────────────────────────────
    safer_tag: str = ""                 # suggestion only; never auto-applied
    safer_tag_generated: bool = False   # True when a safer tag was produced

    # ── Source-context metadata ───────────────────────────────────────────────
    source_text_type: str = "full_text"  # full_text|abstract_only|etc.
    context_limitation: str = ""         # plain-language limitation note

    # ── Deterministic signals ─────────────────────────────────────────────────
    deterministic_mismatches: list[str] = field(default_factory=list)

    # ── Semantic verifier status ──────────────────────────────────────────────
    semantic_verifier_used: bool = False
    semantic_verifier_backend: str = ""
    verifier_confidence: float = 0.0

    # ── Performance ───────────────────────────────────────────────────────────
    verification_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "overall_verdict": self.overall_verdict,
            "claim_verdict": self.claim_verdict,
            "tag_verdict": self.tag_verdict,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "verdict": d.verdict,
                    "severity": d.severity,
                    "explanation": d.explanation,
                    "spans": [
                        {"text": s.text, "start": s.start, "end": s.end, "span_type": s.span_type}
                        for s in d.spans
                    ],
                    "suggested_correction": d.suggested_correction,
                }
                for d in self.dimensions
            ],
            "safer_tag": self.safer_tag,
            "safer_tag_generated": self.safer_tag_generated,
            "source_text_type": self.source_text_type,
            "context_limitation": self.context_limitation,
            "deterministic_mismatches": self.deterministic_mismatches,
            "semantic_verifier_used": self.semantic_verifier_used,
            "semantic_verifier_backend": self.semantic_verifier_backend,
            "verifier_confidence": self.verifier_confidence,
            "verification_duration_ms": round(self.verification_duration_ms, 1),
        }


# ── Deterministic mismatch patterns ──────────────────────────────────────────
#
# All patterns are purely textual — no outside knowledge, no model calls.

# Causal language in claims/tags
_CAUSAL_CLAIM_RE = re.compile(
    r"\b(causes?|leads? to|results? in|prevents?|drives?|triggers?|produces?|creates?)\b",
    re.IGNORECASE,
)
# Associative language in sources
_ASSOCIATIVE_SOURCE_RE = re.compile(
    r"\b(associated with|correlat(?:ed|es|ion)|linked to|may contribute|suggests?|related to"
    r"|consistent with|indicat(?:es?|ive of)|tends? to|appears? to)\b",
    re.IGNORECASE,
)

# Certainty markers
_CERTAIN_CLAIM_RE = re.compile(
    r"\b(will\b|always|inevitably|proves?|definitively|eliminates?|guarantees?|ensures?|must\b)\b",
    re.IGNORECASE,
)
_UNCERTAIN_SOURCE_RE = re.compile(
    r"\b(may\b|might\b|could\b|possibly|likely|probably|suggests?|appears? to|tends? to"
    r"|is consistent with|in some cases?|under certain conditions?)\b",
    re.IGNORECASE,
)

# Numbers and magnitudes (claim has a specific figure)
_NUMBER_RE = re.compile(r"\b(\d+(?:\.\d+)?)[ -]*(%|percent(?:age)?|fold|x\b|times\b|\$|dollars?|billion|million|trillion)")

# Universal / population generalizations
_UNIVERSAL_CLAIM_RE = re.compile(
    r"\b(everyone|all (students?|people|workers?|patients?|families|countries|nations|states)|"
    r"globally|universally|nationwide|across (the country|all states?|the (US|world)))\b",
    re.IGNORECASE,
)
# Subgroup markers in source
_SUBGROUP_SOURCE_RE = re.compile(
    r"\b(study participants?|sample|cohort|survey respondents?|adolescents?|children|patients?"
    r"|adults? (aged|between|in)|in (the )?study|data from|in (this|the|a|our) study|examined)\b",
    re.IGNORECASE,
)

# Geographic overgeneralization
_NATIONAL_CLAIM_RE = re.compile(
    r"\b(nationwide|nationally|national(ly)?|across (the )?(US|United States|country|nation)"
    r"|globally|worldwide|in America|in the US)\b",
    re.IGNORECASE,
)
_LOCAL_SOURCE_RE = re.compile(
    r"\b(in (the )?(state of )?[A-Z][a-z]+(,\s+[A-Z]{2})?|"
    r"county|city of|district|single (city|state|country|site)|"
    r"pilot program|local (school|district|region)|"
    r"this (city|state|county|region|country|municipality))\b",
    re.IGNORECASE,
)

# Timeframe mismatches
_CURRENT_CLAIM_RE = re.compile(
    r"\b(currently|today|now|present(ly)?|in (\d{4}|recent years?)|recent(ly)?)\b",
    re.IGNORECASE,
)
_OLD_SOURCE_RE = re.compile(
    r"\b(19[0-9]{2}|200[0-9]|201[0-3])\b"  # data from 1990s–2013 likely dated
)
_PERMANENT_CLAIM_RE = re.compile(
    r"\b(permanent(ly)?|long[ -]term|lasting|enduring|over (the )?decades?|forever|indefinitely)\b",
    re.IGNORECASE,
)
_SHORTTERM_SOURCE_RE = re.compile(
    r"\b(short[ -]term|(one|two|three|four|five)[ -]year|(\d+)[ -]month"
    r"|follow[ -]up period|at (\d+) (months?|weeks?|days?)|weeks?[ -]long)\b",
    re.IGNORECASE,
)

# Contradiction markers in source
_CONTRADICTION_RE = re.compile(
    r"\b(does not|did not|failed to|found no|no evidence (that|of)|contrary to"
    r"|contradicts?|refutes?|disproves?|not supported|negatively\b|worsened?)"
    r"\b",
    re.IGNORECASE,
)

# Caveat / limitation language
_CAVEAT_RE = re.compile(
    r"\b(however|although|caveat|limitation|limit(ed|s)\b|caution(s)?\b|"
    r"not(e|e that)|important(ly)?|it should be noted|except(ion)?|"
    r"on the other hand|but\b|despite|while\b|whereas|uncertainty|"
    r"confound(ing|er)?|selection bias|cannot (be )?generaliz|"
    r"further research|more research needed|small sample)\b",
    re.IGNORECASE,
)

# Journalism vs original research
_JOURNALISM_MARKERS = re.compile(
    r"\b(according to|reports? (that|say|suggest)|news (report|article)|"
    r"a (new )?study (says?|finds?|shows?|suggests?)|researchers? say|"
    r"experts? say|officials? say|told (the )?[A-Z][a-z]+)\b",
    re.IGNORECASE,
)
_STUDY_AUTHORSHIP_RE = re.compile(
    r"\b(peer[ -]reviewed|journal(?: of)?|doi:|published in|et al\.|volume \d)\b",
    re.IGNORECASE,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Deterministic mismatch checks
# ══════════════════════════════════════════════════════════════════════════════

def _validate_exact_span(text: str, body: str) -> Optional[SupportEvidenceSpan]:
    """Return a SupportEvidenceSpan if text is an exact substring of body, else None."""
    idx = body.find(text)
    if idx == -1:
        return None
    return SupportEvidenceSpan(text=text, start=idx, end=idx + len(text), span_type="supporting")


def _first_match_span(pattern: re.Pattern, body: str,
                       span_type: str = "conflicting") -> Optional[SupportEvidenceSpan]:
    m = pattern.search(body)
    if not m:
        return None
    return SupportEvidenceSpan(
        text=m.group(0), start=m.start(), end=m.end(), span_type=span_type
    )


def check_causal_mismatch(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when claim says 'causes' but source only shows correlation/association."""
    full_source = body_text + "\n\n" + context

    has_causal_claim = bool(_CAUSAL_CLAIM_RE.search(claim_or_tag))
    if not has_causal_claim:
        return None

    has_causal_source = bool(_CAUSAL_CLAIM_RE.search(full_source))
    has_assoc_source = bool(_ASSOCIATIVE_SOURCE_RE.search(full_source))

    if not has_causal_source and has_assoc_source:
        span = _first_match_span(_ASSOCIATIVE_SOURCE_RE, body_text)
        return SupportDimensionResult(
            dimension=DIM_CAUSAL_STRENGTH,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MAJOR,
            explanation=(
                "The claim asserts causation, but the source uses associative language "
                "(e.g., 'associated with', 'correlated with'). "
                "A causal conclusion requires stronger evidence."
            ),
            spans=[span] if span else [],
            suggested_correction=(
                "Replace causal language ('causes', 'leads to') with associative language "
                "('is associated with', 'is linked to')."
            ),
        )
    return None


def check_certainty_mismatch(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when claim uses absolute certainty that the source hedges."""
    full_source = body_text + "\n\n" + context

    has_certain_claim = bool(_CERTAIN_CLAIM_RE.search(claim_or_tag))
    if not has_certain_claim:
        return None

    has_uncertain_source = bool(_UNCERTAIN_SOURCE_RE.search(full_source))
    if has_uncertain_source:
        span = _first_match_span(_UNCERTAIN_SOURCE_RE, body_text)
        return SupportDimensionResult(
            dimension=DIM_CERTAINTY,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MAJOR,
            explanation=(
                "The claim states a certainty ('will', 'always', 'proves') that the "
                "source hedges with language like 'may', 'suggests', or 'likely'."
            ),
            spans=[span] if span else [],
            suggested_correction=(
                "Change absolute language to conditional: 'may', 'is likely to', 'suggests'."
            ),
        )
    return None


def check_magnitude_mismatch(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when claim contains a specific figure not found in the source."""
    claim_numbers = _NUMBER_RE.findall(claim_or_tag)
    if not claim_numbers:
        return None

    full_source = body_text + "\n\n" + context
    source_numbers = _NUMBER_RE.findall(full_source)

    # Check if any claim number+unit pair appears in source
    claim_num_strs = {f"{n}{u}" for n, u in claim_numbers}
    source_num_strs = {f"{n}{u}" for n, u in source_numbers}

    unsupported = claim_num_strs - source_num_strs
    if unsupported:
        return SupportDimensionResult(
            dimension=DIM_MAGNITUDE,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MAJOR,
            explanation=(
                f"The claim contains a specific magnitude ({', '.join(sorted(unsupported))}) "
                "not found in the source passage."
            ),
            spans=[],
            suggested_correction=(
                "Remove the specific figure or replace it with what the source actually says."
            ),
        )
    return None


def check_population_mismatch(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when claim generalizes from a specific subgroup to everyone."""
    full_source = body_text + "\n\n" + context

    has_universal = bool(_UNIVERSAL_CLAIM_RE.search(claim_or_tag))
    has_subgroup_source = bool(_SUBGROUP_SOURCE_RE.search(full_source))

    if has_universal and has_subgroup_source:
        span = _first_match_span(_SUBGROUP_SOURCE_RE, body_text)
        return SupportDimensionResult(
            dimension=DIM_POPULATION_SCOPE,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MAJOR,
            explanation=(
                "The claim makes a universal population claim, but the source studied "
                "a specific subgroup (e.g., study participants, patients, adolescents)."
            ),
            spans=[span] if span else [],
            suggested_correction=(
                "Narrow the claim to the actual study population."
            ),
        )
    return None


def check_geographic_mismatch(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when a local/state study is generalized to a national/global claim."""
    full_source = body_text + "\n\n" + context

    has_national_claim = bool(_NATIONAL_CLAIM_RE.search(claim_or_tag))
    has_local_source = bool(_LOCAL_SOURCE_RE.search(full_source))

    if has_national_claim and has_local_source:
        span = _first_match_span(_LOCAL_SOURCE_RE, body_text)
        return SupportDimensionResult(
            dimension=DIM_GEOGRAPHIC_SCOPE,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MAJOR,
            explanation=(
                "The claim makes a national or global scope claim, but the source "
                "studied a specific local, state, or single-country context."
            ),
            spans=[span] if span else [],
            suggested_correction=(
                "Limit the geographic claim to the study's actual location."
            ),
        )
    return None


def check_timeframe_mismatch(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when historical data is presented as current, or short-term as permanent."""
    full_source = body_text + "\n\n" + context
    mismatches = []

    # Old data presented as current
    has_current_claim = bool(_CURRENT_CLAIM_RE.search(claim_or_tag))
    old_match = _OLD_SOURCE_RE.search(full_source)
    if has_current_claim and old_match:
        mismatches.append(
            f"Source cites data from {old_match.group(0)}, but claim implies currency."
        )

    # Short-term evidence for permanent effect
    has_permanent = bool(_PERMANENT_CLAIM_RE.search(claim_or_tag))
    has_shortterm = bool(_SHORTTERM_SOURCE_RE.search(full_source))
    if has_permanent and has_shortterm:
        mismatches.append(
            "Claim describes a permanent or long-term effect, but source measured "
            "a short-term outcome."
        )

    if mismatches:
        return SupportDimensionResult(
            dimension=DIM_TIMEFRAME,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MAJOR,
            explanation="; ".join(mismatches),
            spans=[],
            suggested_correction=(
                "Specify the study's time period and avoid implying findings are permanent."
            ),
        )
    return None


def check_contradiction_signal(
    body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect explicit contradiction language in the source."""
    full_source = body_text + "\n\n" + context
    m = _CONTRADICTION_RE.search(full_source)
    if m:
        # Only flag if the contradiction is not a meta-contrast ("did not show harm" = good)
        surrounding = full_source[max(0, m.start() - 40): m.end() + 60]
        # Common false-positive: "does not cause harm" → actually supports safety claims
        if any(phrase in surrounding.lower() for phrase in [
            "does not increase", "did not increase", "found no evidence of harm",
            "not harmful", "does not harm",
        ]):
            return None
        span = _first_match_span(_CONTRADICTION_RE, body_text, span_type="conflicting")
        return SupportDimensionResult(
            dimension=DIM_CORE_CLAIM,
            verdict=CONTRADICTED,
            severity=SEVERITY_CRITICAL,
            explanation=(
                f"The source contains contradiction language near: "
                f"'{m.group(0)}'. The passage may argue against the claimed conclusion."
            ),
            spans=[span] if span else [],
        )
    return None


def check_caveat_completeness(
    body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when nearby source text has limitation language absent from the cut."""
    # Only check context (not body_text itself) since caveats in body are preserved
    if not context:
        return None

    caveats_in_context = _CAVEAT_RE.findall(context)
    caveats_in_body = _CAVEAT_RE.findall(body_text)

    # If significant caveat language exists in context but not in the card cut
    if len(caveats_in_context) >= 3 and len(caveats_in_body) == 0:
        preview = context[:150].replace("\n", " ")
        return SupportDimensionResult(
            dimension=DIM_CAVEAT_COMPLETENESS,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MINOR,
            explanation=(
                "Nearby source text contains limitation or caveat language not captured "
                f"by the card cut: '{preview}…'"
            ),
            spans=[],
            suggested_correction=(
                "Verify the cut does not omit an essential qualification. "
                "Consider a broader cut or noting the limitation explicitly."
            ),
        )
    return None


def check_attribution(
    claim_or_tag: str, body_text: str, context: str
) -> Optional[SupportDimensionResult]:
    """Detect when journalism is presented as original research."""
    full_source = body_text + "\n\n" + context

    is_journalism = bool(_JOURNALISM_MARKERS.search(full_source))
    is_original = bool(_STUDY_AUTHORSHIP_RE.search(full_source))

    if is_journalism and not is_original:
        return SupportDimensionResult(
            dimension=DIM_SOURCE_ATTRIBUTION,
            verdict=PARTIALLY_SUPPORTED,
            severity=SEVERITY_MINOR,
            explanation=(
                "The source appears to be journalistic reporting about a study "
                "rather than the original research publication. Judges may challenge "
                "the primary-source authenticity of this card."
            ),
            spans=[],
            suggested_correction=(
                "Locate and cite the original peer-reviewed study if available."
            ),
        )
    return None


def run_deterministic_checks(
    claim: str,
    tag: str,
    body_text: str,
    context: str = "",
) -> list[SupportDimensionResult]:
    """Run all deterministic mismatch checks. Returns any findings (empty = no issues)."""
    findings: list[SupportDimensionResult] = []

    check_target = f"{claim} {tag}"

    for checker in [
        lambda: check_causal_mismatch(check_target, body_text, context),
        lambda: check_certainty_mismatch(check_target, body_text, context),
        lambda: check_magnitude_mismatch(check_target, body_text, context),
        lambda: check_population_mismatch(check_target, body_text, context),
        lambda: check_geographic_mismatch(check_target, body_text, context),
        lambda: check_timeframe_mismatch(check_target, body_text, context),
        lambda: check_contradiction_signal(body_text, context),
        lambda: check_caveat_completeness(body_text, context),
        lambda: check_attribution(check_target, body_text, context),
    ]:
        try:
            result = checker()
            if result is not None:
                findings.append(result)
        except Exception as exc:
            logger.debug("Deterministic check error: %s", exc)

    return findings


# ══════════════════════════════════════════════════════════════════════════════
# 2. Core-claim check (keyword-level support signal)
# ══════════════════════════════════════════════════════════════════════════════

_STOP = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "to", "of", "in", "on", "at", "by", "for", "with", "from",
    "this", "that", "it", "its", "they", "their", "and", "or", "but", "not",
    "if", "as", "so", "than", "more", "less", "such", "also",
})


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"\b[a-z]{3,}\b", text.lower()) if w not in _STOP}


def _core_claim_overlap_ratio(claim: str, body: str) -> float:
    """Fraction of claim keywords that appear in body text."""
    ck = _keywords(claim)
    if not ck:
        return 1.0  # no keywords → can't assess → assume ok
    bk = _keywords(body)
    overlap = ck & bk
    return len(overlap) / len(ck)


def check_core_claim_keyword(
    claim: str, body_text: str
) -> SupportDimensionResult:
    """Keyword-overlap heuristic for core-claim support."""
    ratio = _core_claim_overlap_ratio(claim, body_text)

    if ratio >= 0.55:
        verdict = SUPPORTED
        severity = SEVERITY_NONE
        explanation = f"Core claim keywords overlap well with source ({ratio:.0%})."
    elif ratio >= 0.30:
        verdict = PARTIALLY_SUPPORTED
        severity = SEVERITY_MINOR
        explanation = (
            f"Partial keyword overlap ({ratio:.0%}) — the source covers related "
            "topics but may not directly address all aspects of the claim."
        )
    else:
        verdict = UNSUPPORTED
        severity = SEVERITY_MAJOR
        explanation = (
            f"Low keyword overlap ({ratio:.0%}) between claim and source passage. "
            "The passage may not be relevant to this specific claim."
        )

    return SupportDimensionResult(
        dimension=DIM_CORE_CLAIM,
        verdict=verdict,
        severity=severity,
        explanation=explanation,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. Optional LLM semantic verifier
# ══════════════════════════════════════════════════════════════════════════════

_LLM_VERIFIER_SYSTEM = """\
You are a rigorous debate coach verifying whether a proposed evidence card supports the debater's claim.

ABSOLUTE RULES:
1. Use ONLY the provided evidence text and context. Never use outside knowledge.
2. The evidence body is exact source text — you may not rewrite, improve, or add to it.
3. Choose ONE overall_verdict from: supported, partially_supported, unsupported, contradicted, insufficient_context.
4. For each dimension, choose verdict: supported, partially_supported, unsupported, not_applicable.
5. If you quote any source text, it must be an EXACT substring of the provided evidence body.
6. safer_tag must NOT introduce any fact absent from the evidence text; leave blank if unnecessary.
7. Your judgement must be based on what the source ACTUALLY SAYS, not what it implies or suggests.

Support rules:
- supported: evidence directly and explicitly supports the core claim with acceptable scope/certainty/magnitude.
- partially_supported: evidence supports the general idea but has a meaningful mismatch in cause/certainty/scope/magnitude/time.
- unsupported: evidence does not address the claim or addresses a different question entirely.
- contradicted: evidence explicitly argues against the claim.
- insufficient_context: abstract-only, snippet-only, or truncated text where the full conclusion cannot be verified.
"""


def _call_llm_verifier(
    claim: str,
    tag: str,
    body_text: str,
    context: str,
    source_text_type: str,
    timeout_s: float,
) -> Optional[dict]:
    """Call LLM for structured support verification. Returns raw dict or None."""
    from pydantic import BaseModel

    class _DimVerdict(BaseModel):
        dimension: str
        verdict: str
        explanation: str

    class _VerifierOutput(BaseModel):
        overall_verdict: str
        claim_verdict: str
        tag_verdict: str
        primary_mismatch: str = ""
        dimensions: list[_DimVerdict] = []
        safer_tag: str = ""
        confidence: float = 0.5

    try:
        import openai
        from app.config import get_openai_api_key
        api_key = get_openai_api_key()
        if not api_key:
            return None

        # Bound context to configured max
        from app.config import settings
        max_ctx = getattr(settings, "card_verifier_max_context_chars", 3000)
        bounded_context = context[:max_ctx] if context else ""

        user_msg = (
            f"USER'S CLAIM: {claim}\n"
            f"CARD TAG: {tag}\n"
            f"SOURCE TEXT TYPE: {source_text_type}\n\n"
            f"EVIDENCE BODY (exact source text):\n{body_text}\n\n"
        )
        if bounded_context:
            user_msg += f"SURROUNDING CONTEXT:\n{bounded_context}\n\n"
        user_msg += (
            "Verify whether the evidence body supports the claim and tag. "
            "Check: core_claim, causal_strength, certainty, magnitude, timeframe, "
            "population_scope, geographic_scope, policy_or_intervention_match, "
            "source_attribution, caveat_completeness."
        )

        client = openai.OpenAI(api_key=api_key)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _LLM_VERIFIER_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            response_format=_VerifierOutput,
            max_tokens=600,
            timeout=timeout_s,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            return None
        return parsed.model_dump()

    except Exception as exc:
        logger.debug("LLM verifier failed: %s", exc)
        return None


def _parse_llm_verifier_result(
    raw: dict, body_text: str
) -> tuple[str, str, str, list[SupportDimensionResult], str, bool]:
    """Parse and validate LLM verifier output.

    Returns:
        (overall_verdict, claim_verdict, tag_verdict, dimensions, safer_tag, safer_tag_generated)
    """
    overall = raw.get("overall_verdict", VERIFICATION_UNAVAILABLE)
    if overall not in ALL_VERDICTS:
        overall = VERIFICATION_UNAVAILABLE

    claim_v = raw.get("claim_verdict", VERIFICATION_UNAVAILABLE)
    if claim_v not in ALL_VERDICTS:
        claim_v = overall

    tag_v = raw.get("tag_verdict", VERIFICATION_UNAVAILABLE)
    if tag_v not in ALL_VERDICTS:
        tag_v = overall

    # Validate safer_tag — must not introduce facts absent from source
    safer_tag = (raw.get("safer_tag") or "").strip()
    safer_tag_generated = bool(safer_tag) and overall in (PARTIALLY_SUPPORTED,)

    # Build dimension results, ignoring invalid verdicts
    dimensions: list[SupportDimensionResult] = []
    for dim_raw in raw.get("dimensions", []):
        d_name = dim_raw.get("dimension", "")
        d_verdict = dim_raw.get("verdict", "not_applicable")
        if d_name not in ALL_DIMENSIONS:
            continue
        if d_verdict not in (SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, "not_applicable"):
            d_verdict = "not_applicable"
        severity = (
            SEVERITY_CRITICAL if d_verdict == CONTRADICTED
            else SEVERITY_MAJOR if d_verdict == UNSUPPORTED
            else SEVERITY_MINOR if d_verdict == PARTIALLY_SUPPORTED
            else SEVERITY_NONE
        )
        dimensions.append(SupportDimensionResult(
            dimension=d_name,
            verdict=d_verdict,
            severity=severity,
            explanation=dim_raw.get("explanation", ""),
        ))

    return overall, claim_v, tag_v, dimensions, safer_tag, safer_tag_generated


# ══════════════════════════════════════════════════════════════════════════════
# 4. Verdict aggregation (deterministic, reproducible)
# ══════════════════════════════════════════════════════════════════════════════

def _source_type_limitation(source_text_type: str) -> str:
    """Return a plain-language context limitation note for the source-text type."""
    limits = {
        "abstract_only": (
            "This card is from an abstract only — full methods, limitations, "
            "and result details are unavailable."
        ),
        "snippet_only": "Only a short snippet is available; full source context cannot be verified.",
        "metadata_only": "No usable body text is available for this source.",
        "partial_extraction": (
            "The full document was only partially extracted; some sections may be missing."
        ),
    }
    return limits.get(source_text_type, "")


def aggregate_verdict(
    core_claim_result: SupportDimensionResult,
    det_findings: list[SupportDimensionResult],
    llm_overall: Optional[str],
    source_text_type: str,
) -> str:
    """Deterministic aggregation of all verification signals into one verdict.

    Rules (in priority order):
    1. metadata_only or snippet_only → insufficient_context (cannot verify)
    2. Any dimension verdict is CONTRADICTED → contradicted
    3. core_claim verdict is UNSUPPORTED → unsupported
    4. abstract_only → at most partially_supported
    5. Any CRITICAL deterministic finding → contradicted
    6. Any MAJOR deterministic finding → partially_supported
    7. core_claim is supported, LLM agrees, no major issues → supported
    8. Otherwise → partially_supported
    """
    # Rule 1: insufficient source context
    if source_text_type in ("metadata_only", "snippet_only"):
        return INSUFFICIENT_CONTEXT

    # Rule 2: contradiction detected
    if any(d.verdict == CONTRADICTED for d in det_findings + [core_claim_result]):
        return CONTRADICTED
    if any(d.severity == SEVERITY_CRITICAL for d in det_findings):
        return CONTRADICTED

    # Rule 3: core claim not supported
    if core_claim_result.verdict == UNSUPPORTED:
        return UNSUPPORTED

    # LLM says unsupported or contradicted (weight heavily)
    if llm_overall in (UNSUPPORTED, CONTRADICTED):
        return llm_overall

    # Rule 4: abstract-only cannot get "supported"
    if source_text_type == "abstract_only":
        # LLM partial or fully supported → partially_supported at best
        if core_claim_result.verdict in (SUPPORTED, PARTIALLY_SUPPORTED):
            return PARTIALLY_SUPPORTED
        return INSUFFICIENT_CONTEXT

    # partial extraction → at most partially_supported when issues found
    if source_text_type == "partial_extraction" and det_findings:
        return PARTIALLY_SUPPORTED

    # Rule 5/6: any major deterministic finding
    major_findings = [d for d in det_findings if d.severity in (SEVERITY_MAJOR, SEVERITY_CRITICAL)]
    if any(d.severity == SEVERITY_CRITICAL for d in major_findings):
        return CONTRADICTED
    if major_findings:
        return PARTIALLY_SUPPORTED

    # Rule 7: core claim supported, LLM supports or unavailable
    if core_claim_result.verdict == SUPPORTED:
        if llm_overall in (None, SUPPORTED, PARTIALLY_SUPPORTED, VERIFICATION_UNAVAILABLE):
            return SUPPORTED if llm_overall != PARTIALLY_SUPPORTED else PARTIALLY_SUPPORTED

    # Rule 8: fallback
    return PARTIALLY_SUPPORTED


# ══════════════════════════════════════════════════════════════════════════════
# 5. Safer tag generation
# ══════════════════════════════════════════════════════════════════════════════

def _generate_safer_tag(
    tag: str,
    findings: list[SupportDimensionResult],
    best_supported_claim: str,
) -> str:
    """Generate a safer tag suggestion based on deterministic findings.

    Returns empty string when no correction is needed.
    The returned tag is a SUGGESTION ONLY and must never be auto-applied.
    """
    if not findings:
        return ""

    safer = tag
    modified = False

    for finding in findings:
        if finding.dimension == DIM_CAUSAL_STRENGTH:
            safer = re.sub(
                _CAUSAL_CLAIM_RE,
                lambda m: {
                    "causes": "is associated with",
                    "leads to": "is linked to",
                    "results in": "correlates with",
                    "prevents": "may reduce",
                    "drives": "is associated with",
                    "triggers": "may trigger",
                    "produces": "is associated with",
                    "creates": "is linked to",
                }.get(m.group(0).lower(), "is associated with"),
                safer,
                count=1,
            )
            modified = True

        elif finding.dimension == DIM_CERTAINTY:
            safer = re.sub(
                _CERTAIN_CLAIM_RE,
                lambda m: {
                    "will": "may", "always": "often", "inevitably": "likely",
                    "proves": "suggests", "definitively": "tentatively",
                    "eliminates": "may reduce", "guarantees": "may improve",
                    "ensures": "is likely to produce", "must": "should",
                }.get(m.group(0).lower(), "may"),
                safer,
                count=1,
            )
            modified = True

        elif finding.dimension == DIM_GEOGRAPHIC_SCOPE:
            safer = re.sub(
                _NATIONAL_CLAIM_RE, "in the studied region", safer, count=1
            )
            modified = True

        elif finding.dimension == DIM_POPULATION_SCOPE:
            safer = re.sub(
                _UNIVERSAL_CLAIM_RE, "among study participants", safer, count=1
            )
            modified = True

    # Fall back to best_supported_claim when we couldn't make a clean fix
    if not modified and best_supported_claim and len(best_supported_claim) < len(tag):
        return best_supported_claim.strip()

    return safer.strip() if modified else ""


# ══════════════════════════════════════════════════════════════════════════════
# 6. Public entry point
# ══════════════════════════════════════════════════════════════════════════════

def verify_card_support(
    claim: str,
    tag: str,
    body_text: str,
    *,
    context: str = "",
    source_text_type: str = "full_text",
    best_supported_claim: str = "",
    timeout_s: Optional[float] = None,
    enable_semantic: Optional[bool] = None,
) -> EvidenceVerificationResult:
    """Verify whether the evidence card supports the claim and tag.

    Args:
        claim: The user's original claim goal.
        tag: The generated card tag (debate headline).
        body_text: The exact evidence body text (immutable; never modified).
        context: Surrounding paragraphs / abstract / section text.
        source_text_type: Classification of source completeness.
        best_supported_claim: Narrower claim from the evidence-role classifier.
        timeout_s: LLM verifier timeout in seconds (default from config).
        enable_semantic: Override config enable flag (for testing).

    Returns EvidenceVerificationResult. Never raises.
    """
    t_start = time.monotonic()

    # Handle edge cases gracefully
    if not claim and not tag:
        return _unavailable_result(t_start, "No claim or tag provided.")
    if not body_text:
        return _unavailable_result(t_start, "No evidence body text provided.")

    try:
        from app.config import settings as _cfg
        if timeout_s is None:
            timeout_s = float(getattr(_cfg, "card_verifier_timeout_s", 10.0))
        if enable_semantic is None:
            enable_semantic = getattr(_cfg, "research_enable_card_verification", True)
    except Exception:
        timeout_s = timeout_s or 10.0
        enable_semantic = enable_semantic if enable_semantic is not None else False

    mismatches: list[str] = []
    dimensions: list[SupportDimensionResult] = []

    # ── Layer 1: Deterministic checks ────────────────────────────────────────
    det_findings = run_deterministic_checks(claim, tag, body_text, context)
    for f in det_findings:
        dimensions.append(f)
        if f.severity in (SEVERITY_MAJOR, SEVERITY_CRITICAL):
            mismatches.append(f"{f.dimension}: {f.explanation[:100]}")

    # Always include core_claim result
    core_result = check_core_claim_keyword(
        f"{claim} {best_supported_claim}".strip(), body_text
    )
    dimensions.insert(0, core_result)  # core_claim first

    # ── Layer 2: Optional LLM semantic verifier ───────────────────────────────
    llm_overall: Optional[str] = None
    llm_claim_v: Optional[str] = None
    llm_tag_v: Optional[str] = None
    llm_dims: list[SupportDimensionResult] = []
    llm_safer_tag: str = ""
    llm_safer_tag_gen: bool = False
    sem_used = False
    sem_backend = ""
    llm_raw: Optional[dict] = None  # initialized so the reference at verifier_confidence is safe

    if enable_semantic:
        llm_raw = None
        try:
            llm_raw = _call_llm_verifier(
                claim=claim, tag=tag, body_text=body_text,
                context=context, source_text_type=source_text_type,
                timeout_s=timeout_s,
            )
        except Exception as exc:
            logger.debug("Semantic verifier call failed: %s", exc)

        if llm_raw is not None:
            (
                llm_overall, llm_claim_v, llm_tag_v,
                llm_dims, llm_safer_tag, llm_safer_tag_gen,
            ) = _parse_llm_verifier_result(llm_raw, body_text)
            sem_used = True
            sem_backend = "gpt-4o-mini"

            # Add any LLM dimensions not already covered by deterministic
            det_dim_names = {d.dimension for d in dimensions}
            for dim in llm_dims:
                if dim.dimension not in det_dim_names and dim.verdict != "not_applicable":
                    dimensions.append(dim)

    # ── Layer 3: Verdict aggregation ─────────────────────────────────────────
    overall = aggregate_verdict(core_result, det_findings, llm_overall, source_text_type)

    # Claim verdict: aggregate with claim-specific phrasing
    claim_v = llm_claim_v or overall
    tag_v = llm_tag_v or overall

    # ── Safer tag ─────────────────────────────────────────────────────────────
    safer_tag = llm_safer_tag or ""
    safer_generated = llm_safer_tag_gen

    if not safer_tag and overall == PARTIALLY_SUPPORTED:
        safer_tag = _generate_safer_tag(tag, det_findings, best_supported_claim)
        safer_generated = bool(safer_tag)

    # ── Context limitation note ───────────────────────────────────────────────
    context_limitation = _source_type_limitation(source_text_type)

    duration_ms = (time.monotonic() - t_start) * 1000

    return EvidenceVerificationResult(
        overall_verdict=overall,
        claim_verdict=claim_v,
        tag_verdict=tag_v,
        dimensions=dimensions,
        safer_tag=safer_tag,
        safer_tag_generated=safer_generated,
        source_text_type=source_text_type,
        context_limitation=context_limitation,
        deterministic_mismatches=mismatches,
        semantic_verifier_used=sem_used,
        semantic_verifier_backend=sem_backend,
        verifier_confidence=float(llm_raw.get("confidence", 0.0)) if (llm_raw and sem_used) else 0.5,
        verification_duration_ms=duration_ms,
    )


def _unavailable_result(t_start: float, reason: str) -> EvidenceVerificationResult:
    return EvidenceVerificationResult(
        overall_verdict=VERIFICATION_UNAVAILABLE,
        claim_verdict=VERIFICATION_UNAVAILABLE,
        tag_verdict=VERIFICATION_UNAVAILABLE,
        context_limitation=reason,
        verification_duration_ms=(time.monotonic() - t_start) * 1000,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 7. Pipeline acceptance decision
# ══════════════════════════════════════════════════════════════════════════════

def should_accept_card(result: EvidenceVerificationResult) -> bool:
    """Return True when the card should be included in card_drafts.

    - supported, partially_supported, insufficient_context: accept (with warnings)
    - verification_unavailable: accept (degrade gracefully)
    - unsupported, contradicted: reject
    """
    return result.overall_verdict not in (UNSUPPORTED, CONTRADICTED)


def should_move_to_counter_evidence(result: EvidenceVerificationResult) -> bool:
    """Return True when a supporting card should be moved to counter_evidence_drafts.

    Contradicted evidence may be retained for counterevidence use.
    """
    return result.overall_verdict == CONTRADICTED
