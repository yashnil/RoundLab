"""Pass 15 — Deterministic Adaptation Rules per Judge Type.

Each rule function returns a list of AdaptationChange objects.
No LLM is called here. Suggested phrasing uses deterministic templates.

Immutability contract (enforced by never including these in output):
    - Evidence body text
    - Source meaning
    - Support verdicts
    - Citation metadata
    - Factual magnitude, causal strength, population scope
    - Source qualifications
    - Argument status on the flow
"""

from __future__ import annotations

from typing import Optional

from app.models.judge_adaptation import AdaptationChange, JudgeProfile, JudgeType


# ── Dimension constants ───────────────────────────────────────────────────────

_JARGON_TERMS = frozenset({
    "non-unique", "no-link", "turn", "terminal defense", "concede",
    "extend", "frontline", "flow", "impact calculus", "timeframe",
    "magnitude", "probability", "internal link", "contention",
    "weighing", "burden", "offense", "straight turn", "concede and turn",
    "PF", "LD", "CX", "rebuttal", "final focus",
})

_LAY_JARGON_REPLACEMENTS = {
    "non-unique": "this problem already exists",
    "no-link": "their claim doesn't connect to the conclusion",
    "turn": "actually their argument helps our side",
    "terminal defense": "this completely eliminates the risk",
    "extend": "carry this argument forward",
    "frontline": "answer to their argument",
    "weighing": "comparing which side's impact matters more",
    "internal link": "the middle step connecting evidence to the impact",
    "contention": "main argument",
}


def _jargon_change(term: str, replacement: str) -> AdaptationChange:
    return AdaptationChange(
        dimension="jargon_level",
        original=f'"{term}"',
        adapted=f'"{replacement}"',
        reason=f'Lay/parent judge unfamiliar with debate jargon "{term}"',
        may_be_omitted=False,
    )


# ── Lay judge rules ────────────────────────────────────────────────────────────

def lay_judge_changes(
    tag: Optional[str] = None,
    body_excerpt: Optional[str] = None,
    has_evidence: bool = True,
    response_count: int = 0,
) -> list[AdaptationChange]:
    """Deterministic adaptation changes for a lay judge."""
    changes: list[AdaptationChange] = []

    # Jargon simplification
    if body_excerpt or tag:
        text = f"{tag or ''} {body_excerpt or ''}".lower()
        for term, replacement in _LAY_JARGON_REPLACEMENTS.items():
            if term in text:
                changes.append(_jargon_change(term, replacement))

    # Evidence introduction
    if has_evidence:
        changes.append(AdaptationChange(
            dimension="evidence_introduction",
            adapted="Introduce the source before reading: 'According to [Author/Org], [what they found].'",
            reason="Lay judges need context about who is speaking before they can evaluate the card.",
        ))

    # Real-world framing
    changes.append(AdaptationChange(
        dimension="impact_framing",
        adapted="End with an explicit real-world consequence: 'This means [concrete outcome] for [relatable group].'",
        reason="Lay judges are persuaded by tangible consequences, not abstract impact labels.",
    ))

    # Response overload warning
    if response_count > 3:
        changes.append(AdaptationChange(
            dimension="response_count",
            original=f"{response_count} responses",
            adapted="2-3 best responses",
            reason="Lay judges lose track of many shallow responses. Lead with the clearest intuitive answer.",
        ))

    # Warrant explanation
    changes.append(AdaptationChange(
        dimension="warrant_explanation",
        adapted="Explain the causal mechanism in one sentence: 'This works because...'",
        reason="Lay judges need explicit cause-and-effect, not just evidence citation.",
    ))

    return changes


# ── Parent judge rules ────────────────────────────────────────────────────────

def parent_judge_changes(
    tag: Optional[str] = None,
    body_excerpt: Optional[str] = None,
    has_evidence: bool = True,
) -> list[AdaptationChange]:
    """Deterministic adaptation changes for a parent judge."""
    changes = lay_judge_changes(tag=tag, body_excerpt=body_excerpt, has_evidence=has_evidence)

    # Additional: define debate terms
    changes.append(AdaptationChange(
        dimension="term_definition",
        adapted="Define any debate-specific terms the first time you use them.",
        reason="Parent judges know the topic (from supporting their child) but not debate conventions.",
    ))

    # Fairness framing
    changes.append(AdaptationChange(
        dimension="fairness_framing",
        adapted="Frame weighing around practical consequences and fairness: 'The more realistic concern is...'",
        reason="Parent judges respond to fairness and practical reasoning, not technical flows.",
    ))

    # Policy knowledge assumption
    changes.append(AdaptationChange(
        dimension="policy_context",
        adapted="Do not assume knowledge of current policy specifics. Briefly orient the judge.",
        reason="Parent judges may be familiar with the topic but not policy details.",
    ))

    return changes


# ── Flow judge rules ──────────────────────────────────────────────────────────

def flow_judge_changes(
    has_explicit_labels: bool = False,
    has_extension: bool = True,
    response_count: int = 0,
    has_weighing: bool = True,
) -> list[AdaptationChange]:
    """Deterministic adaptation changes for a flow judge."""
    changes: list[AdaptationChange] = []

    if not has_explicit_labels:
        changes.append(AdaptationChange(
            dimension="argument_labels",
            adapted="Use clear numbered/labeled responses: 'First, non-unique. Second, no internal link.'",
            reason="Flow judges track arguments by label; unlabeled responses get dropped on the flow.",
        ))

    if not has_extension:
        changes.append(AdaptationChange(
            dimension="extension",
            adapted="Extend claim, warrant, evidence, and impact explicitly: 'Extend [claim] — [evidence] — [impact]'",
            reason="Flow judges require explicit extensions or arguments are considered dropped.",
        ))

    changes.append(AdaptationChange(
        dimension="organization",
        adapted="Announce each response before delivering it. Use consistent structure: claim → evidence → impact.",
        reason="Flow judges expect line-by-line organization and will flow what they can track.",
    ))

    if not has_weighing:
        changes.append(AdaptationChange(
            dimension="weighing",
            adapted="Provide explicit comparative weighing: timeframe, magnitude, and probability.",
            reason="Flow judges expect comparative analysis in summary and final focus.",
        ))

    return changes


# ── Technical judge rules ─────────────────────────────────────────────────────

def technical_judge_changes(
    has_concession_exploitation: bool = False,
    response_count: int = 0,
    has_burden_framing: bool = False,
) -> list[AdaptationChange]:
    """Deterministic adaptation changes for a technical judge."""
    changes: list[AdaptationChange] = []

    if not has_concession_exploitation:
        changes.append(AdaptationChange(
            dimension="concession_interaction",
            adapted="Identify and exploit explicit concessions: 'They conceded [X] in their [speech]. That means...'",
            reason="Technical judges track concessions precisely and reward explicit exploitation.",
        ))

    changes.append(AdaptationChange(
        dimension="argument_precision",
        adapted="Use precise argument wording. Avoid rhetorical substitution for actual analysis.",
        reason="Technical judges distinguish analysis from rhetoric and will not fill in gaps.",
    ))

    changes.append(AdaptationChange(
        dimension="offense_defense_separation",
        adapted="Clearly separate offensive arguments from defensive responses.",
        reason="Technical judges distinguish terminal defense from mitigation and track each separately.",
    ))

    if not has_burden_framing:
        changes.append(AdaptationChange(
            dimension="burden_framing",
            adapted="Identify where the burden lies and how you are meeting it.",
            reason="Technical judges care about framework and burden implications.",
        ))

    return changes


# ── Coach judge rules ─────────────────────────────────────────────────────────

def coach_judge_changes(
    has_complete_structure: bool = True,
    has_source_qualification: bool = False,
) -> list[AdaptationChange]:
    """Deterministic adaptation changes for a coach judge."""
    changes: list[AdaptationChange] = []

    changes.append(AdaptationChange(
        dimension="argument_structure",
        adapted="Use complete argument structure: claim → warrant → evidence → impact. Do not shortcut.",
        reason="Coach judges value educational habits and penalize structural shortcuts even when they technically work.",
    ))

    if not has_source_qualification:
        changes.append(AdaptationChange(
            dimension="source_qualification",
            adapted="Briefly introduce source credentials where they strengthen the card.",
            reason="Coach judges reward explaining why a source is credible, not just citing it.",
        ))

    changes.append(AdaptationChange(
        dimension="delivery_balance",
        adapted="Balance delivery and technical execution. Neither pure rhetoric nor pure flow.",
        reason="Coach judges evaluate habits, not just outcomes.",
    ))

    changes.append(AdaptationChange(
        dimension="strategic_soundness",
        adapted="Prioritize strategically sound choices over technically faster shortcuts.",
        reason="Coach judges reward strategic thinking that would generalize to harder rounds.",
    ))

    return changes


# ── Dispatch ──────────────────────────────────────────────────────────────────

def get_adaptation_changes(
    judge_type: JudgeType,
    *,
    tag: Optional[str] = None,
    body_excerpt: Optional[str] = None,
    has_evidence: bool = True,
    response_count: int = 0,
    has_explicit_labels: bool = False,
    has_extension: bool = True,
    has_weighing: bool = True,
    has_concession_exploitation: bool = False,
    has_burden_framing: bool = False,
    has_complete_structure: bool = True,
    has_source_qualification: bool = False,
) -> list[AdaptationChange]:
    """Dispatch to the correct rule set for the given judge type."""
    if judge_type == "lay":
        return lay_judge_changes(
            tag=tag, body_excerpt=body_excerpt,
            has_evidence=has_evidence, response_count=response_count,
        )
    if judge_type == "parent":
        return parent_judge_changes(
            tag=tag, body_excerpt=body_excerpt, has_evidence=has_evidence,
        )
    if judge_type == "flow":
        return flow_judge_changes(
            has_explicit_labels=has_explicit_labels,
            has_extension=has_extension,
            response_count=response_count,
            has_weighing=has_weighing,
        )
    if judge_type == "technical":
        return technical_judge_changes(
            has_concession_exploitation=has_concession_exploitation,
            response_count=response_count,
            has_burden_framing=has_burden_framing,
        )
    if judge_type == "coach":
        return coach_judge_changes(
            has_complete_structure=has_complete_structure,
            has_source_qualification=has_source_qualification,
        )
    # custom — return base changes
    return lay_judge_changes(tag=tag, body_excerpt=body_excerpt, has_evidence=has_evidence)
