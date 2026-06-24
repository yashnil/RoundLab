"""Pass 15 — Adaptation Risk Detection.

Deterministic checks for risks that arise when adapting material for a judge.
Reuses Pass 11 support verdicts and Pass 14 freshness assessments.

No LLM calls. All checks are pattern-based or structural.
"""

from __future__ import annotations

import re
from typing import Optional

from app.models.judge_adaptation import AdaptationRisk, AdaptationRiskLevel, JudgeType

# ── Causal overstatement patterns ─────────────────────────────────────────────

_CAUSAL_STRONG_PATTERNS = re.compile(
    r"\b(causes?|leads? to|results? in|proves?|demonstrates?|shows? that)\b",
    re.IGNORECASE,
)
_CORRELATION_INDICATORS = re.compile(
    r"\b(associated with|correlated with|linked to|related to|may|might|could|suggests?)\b",
    re.IGNORECASE,
)
_QUALIFIER_WORDS = re.compile(
    r"\b(limited|in some cases?|under certain conditions?|in developed countries?|"
    r"when controlling for|only if|with caveats?|may not|does not always|"
    r"preliminary|not conclusive)\b",
    re.IGNORECASE,
)


def _risk(
    category: str,
    level: str,
    description: str,
    source_ref: Optional[str] = None,
    how_to_mitigate: str = "",
) -> AdaptationRisk:
    return AdaptationRisk(
        category=category,  # type: ignore[arg-type]
        level=level,  # type: ignore[arg-type]
        description=description,
        source_ref=source_ref,
        how_to_mitigate=how_to_mitigate or "Review the original source and ensure the adaptation preserves the original causal strength.",
    )


# ── Individual risk checks ─────────────────────────────────────────────────────

def check_causal_overstatement(
    original_body: Optional[str],
    tag: Optional[str],
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if the original body uses correlation language but the tag or simplification might overstate causality."""
    risks: list[AdaptationRisk] = []
    if not original_body:
        return risks
    has_correlation = bool(_CORRELATION_INDICATORS.search(original_body))
    has_causal_claim = bool(_CAUSAL_STRONG_PATTERNS.search(tag or ""))
    if has_correlation and has_causal_claim:
        risks.append(_risk(
            category="causal_overstatement",
            level="high",
            description=(
                "The evidence uses correlation language but the tag states a causal claim. "
                f"Adapting for a {judge_type} judge who values narrative may amplify this overstatement."
            ),
            source_ref=source_ref,
            how_to_mitigate="Ensure the tag accurately reflects the evidence's causal strength. Do not upgrade correlation to causation.",
        ))
    return risks


def check_qualifier_removal(
    original_body: Optional[str],
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if the body has qualifiers that might be omitted when simplifying."""
    risks: list[AdaptationRisk] = []
    if not original_body:
        return risks
    qualifiers = _QUALIFIER_WORDS.findall(original_body)
    if qualifiers and judge_type in ("lay", "parent"):
        risks.append(_risk(
            category="qualifier_removal",
            level="medium",
            description=(
                f"The evidence contains {len(qualifiers)} qualifier(s) "
                f"(e.g., '{qualifiers[0]}'). Lay/parent adaptation may inadvertently omit them, "
                "making the claim appear stronger than it is."
            ),
            source_ref=source_ref,
            how_to_mitigate="Keep at least one qualifier phrase when simplifying. Do not present a limited claim as universal.",
        ))
    return risks


def check_unsafe_card(
    support_verdict: Optional[str],
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if the card has an unsupported verdict (Pass 11 integration)."""
    risks: list[AdaptationRisk] = []
    if support_verdict in ("unsupported", "contradicts"):
        risks.append(_risk(
            category="unsafe_card_used",
            level="critical",
            description=(
                f"This card has an '{support_verdict}' support verdict. "
                f"Adapting for a {judge_type} judge does not make the card safe to use in round."
            ),
            source_ref=source_ref,
            how_to_mitigate="Do not use this card until the claim is verified against the source. Adaptation cannot fix a bad card.",
        ))
    elif support_verdict == "partial":
        risks.append(_risk(
            category="unsafe_card_used",
            level="medium",
            description="Card has partial support — some claims are unverified. Exercise caution when simplifying.",
            source_ref=source_ref,
            how_to_mitigate="Ensure you only claim what the evidence fully supports when presenting to a lay or parent judge.",
        ))
    return risks


def check_stale_card(
    freshness_state: Optional[str],
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if the card is stale (Pass 14 integration)."""
    risks: list[AdaptationRisk] = []
    if freshness_state in ("stale", "superseded"):
        risks.append(_risk(
            category="stale_card_used",
            level="medium" if freshness_state == "superseded" else "high",
            description=(
                f"The evidence has freshness state '{freshness_state}'. "
                f"A {judge_type} judge may be persuaded by the argument today but the claim may be outdated."
            ),
            source_ref=source_ref,
            how_to_mitigate="Find updated evidence or explicitly acknowledge the date in round. Adaptation cannot refresh the evidence.",
        ))
    return risks


def check_jargon_overflow(
    tag: Optional[str],
    body_excerpt: Optional[str],
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if the planned delivery uses jargon a lay/parent judge won't understand."""
    risks: list[AdaptationRisk] = []
    if judge_type not in ("lay", "parent"):
        return risks
    from app.services.adaptation_rules import _JARGON_TERMS
    text = f"{tag or ''} {body_excerpt or ''}".lower()
    found = [t for t in _JARGON_TERMS if t in text]
    if len(found) > 2:
        risks.append(_risk(
            category="jargon_overflow",
            level="medium",
            description=f"Text contains {len(found)} jargon terms ({', '.join(found[:3])}...) likely unfamiliar to a {judge_type} judge.",
            source_ref=source_ref,
            how_to_mitigate="Replace jargon with plain-language alternatives before presenting.",
        ))
    return risks


def check_under_explanation(
    has_warrant: bool,
    has_real_world_link: bool,
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if the argument is missing explanations needed for a parent/lay judge."""
    risks: list[AdaptationRisk] = []
    if judge_type not in ("lay", "parent"):
        return risks
    if not has_warrant:
        risks.append(_risk(
            category="under_explanation",
            level="high",
            description=f"No warrant explanation found. A {judge_type} judge needs the 'why' explicitly stated.",
            source_ref=source_ref,
            how_to_mitigate="Add one sentence explaining the causal mechanism before the impact.",
        ))
    if not has_real_world_link:
        risks.append(_risk(
            category="under_explanation",
            level="medium",
            description=f"No real-world connection found. {judge_type.capitalize()} judges need concrete examples.",
            source_ref=source_ref,
            how_to_mitigate="Add a real-world example or analogy to connect the evidence to lived experience.",
        ))
    return risks


def check_missing_extension(
    is_summary_or_ff: bool,
    has_extension_signal: bool,
    judge_type: JudgeType,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag missing extensions in summary/final focus."""
    risks: list[AdaptationRisk] = []
    if not is_summary_or_ff:
        return risks
    if not has_extension_signal and judge_type in ("flow", "technical", "coach"):
        risks.append(_risk(
            category="missing_extension",
            level="high",
            description=f"Argument is not explicitly extended in this speech. A {judge_type} judge will drop it.",
            source_ref=source_ref,
            how_to_mitigate="Add explicit extension: 'Extend [claim] — [evidence tag] — [impact]'.",
        ))
    return risks


def check_new_argument_late_speech(
    is_final_focus: bool,
    introduces_new_content: bool,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag new arguments in final focus."""
    risks: list[AdaptationRisk] = []
    if is_final_focus and introduces_new_content:
        risks.append(_risk(
            category="new_argument_late_speech",
            level="critical",
            description="New argument or evidence introduced in final focus. This violates PF rules.",
            source_ref=source_ref,
            how_to_mitigate="Remove new content. Final focus may only extend arguments already on the flow.",
        ))
    return risks


def check_narrative_over_flow(
    judge_type: JudgeType,
    is_heavy_narrative: bool,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag excessive narrative when presenting to a flow/technical judge."""
    risks: list[AdaptationRisk] = []
    if judge_type in ("flow", "technical") and is_heavy_narrative:
        risks.append(_risk(
            category="narrative_over_flow",
            level="medium",
            description=f"Heavy narrative framing detected. A {judge_type} judge wants analysis, not story.",
            source_ref=source_ref,
            how_to_mitigate="Lead with the argument label and evidence, then add brief analysis. Save narrative for lay rounds.",
        ))
    return risks


def check_evidence_without_analysis(
    judge_type: JudgeType,
    evidence_count: int,
    has_analysis: bool,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag card-dumping without analytical connectors."""
    risks: list[AdaptationRisk] = []
    if evidence_count >= 3 and not has_analysis:
        risks.append(_risk(
            category="evidence_without_analysis",
            level="medium",
            description=f"{evidence_count} cards without connecting analysis. {judge_type.capitalize()} judges need you to explain how cards interact.",
            source_ref=source_ref,
            how_to_mitigate="Add brief explanation between cards: 'This card establishes X. The next card shows that X leads to Y.'",
        ))
    return risks


def check_warrant_collapse(
    simplified_text: Optional[str],
    original_has_warrant: bool,
    source_ref: Optional[str] = None,
) -> list[AdaptationRisk]:
    """Flag if simplification may have removed the warrant entirely."""
    risks: list[AdaptationRisk] = []
    if not original_has_warrant:
        return risks
    if simplified_text:
        has_mechanism = bool(re.search(r"\b(because|since|this works by|mechanism|causes?|through)\b", simplified_text, re.I))
        if not has_mechanism:
            risks.append(_risk(
                category="warrant_collapsed",
                level="high",
                description="Simplified version appears to omit the causal mechanism (warrant).",
                source_ref=source_ref,
                how_to_mitigate="Add back one sentence explaining why the evidence leads to the impact.",
            ))
    return risks


# ── Aggregate checker ─────────────────────────────────────────────────────────

def check_all_risks(
    judge_type: JudgeType,
    *,
    card_id: Optional[str] = None,
    tag: Optional[str] = None,
    original_body: Optional[str] = None,
    support_verdict: Optional[str] = None,
    freshness_state: Optional[str] = None,
    has_warrant: bool = True,
    has_real_world_link: bool = False,
    has_extension_signal: bool = True,
    is_summary_or_ff: bool = False,
    is_final_focus: bool = False,
    introduces_new_content: bool = False,
    is_heavy_narrative: bool = False,
    evidence_count: int = 1,
    has_analysis: bool = True,
) -> list[AdaptationRisk]:
    """Run all risk checks for a given context. Returns deduplicated risk list."""
    risks: list[AdaptationRisk] = []
    ref = card_id

    risks.extend(check_causal_overstatement(original_body, tag, judge_type, ref))
    risks.extend(check_qualifier_removal(original_body, judge_type, ref))
    risks.extend(check_unsafe_card(support_verdict, judge_type, ref))
    risks.extend(check_stale_card(freshness_state, judge_type, ref))
    risks.extend(check_jargon_overflow(tag, original_body, judge_type, ref))
    risks.extend(check_under_explanation(has_warrant, has_real_world_link, judge_type, ref))
    risks.extend(check_missing_extension(is_summary_or_ff, has_extension_signal, judge_type, ref))
    risks.extend(check_new_argument_late_speech(is_final_focus, introduces_new_content, ref))
    risks.extend(check_narrative_over_flow(judge_type, is_heavy_narrative, ref))
    risks.extend(check_evidence_without_analysis(judge_type, evidence_count, has_analysis, ref))

    # Sort by severity
    _sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda r: _sev_order.get(r.level, 9))
    return risks


def critical_risks(risks: list[AdaptationRisk]) -> list[AdaptationRisk]:
    return [r for r in risks if r.level == "critical"]
