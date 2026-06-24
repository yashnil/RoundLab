"""Pass 14 — Gap-Driven Workout Generator.

Derives targeted practice workouts from prep gaps and real saved cards.
All workout content is derived deterministically from library data.

Design invariants:
- Source card body text is copied at generation time — never mutated.
- Completing a speaking drill does NOT resolve a missing-evidence gap.
- Workout body never contains AI-generated text in this pass.
- Each workout type has specific success criteria.

Public interface:
    generate_workout_for_gap(gap, card) -> PrepWorkoutCreate
    generate_workouts_for_report(report, cards) -> list[PrepWorkoutCreate]
"""

from __future__ import annotations

import textwrap
from typing import Optional

from app.models.tournament_prep import (
    GapCategory,
    PrepGap,
    PrepWorkoutCreate,
    WorkoutType,
)

# ── Workout templates by gap category ─────────────────────────────────────────

def _evidence_explanation_workout(gap: PrepGap, card: dict) -> PrepWorkoutCreate:
    tag = card.get("tag", "this card")
    body = card.get("body_text", "")
    body_excerpt = textwrap.shorten(body, width=300, placeholder="…")
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",  # filled by caller
        user_id="",                            # filled by caller
        gap_id=gap.id,
        workout_type="evidence_explanation",
        title=f"Explain the warrant: {tag[:60]}",
        description=(
            "Practice explaining how this card proves the warrant without reading the tag."
        ),
        prompt=(
            f"Read the following evidence card carefully:\n\n"
            f"TAG: {tag}\n\n"
            f"CARD: {body_excerpt}\n\n"
            "Now explain in 30-45 seconds — out loud — how this card proves the warrant. "
            "Do NOT read the tag. Use your own words to explain what the card shows, "
            "how it links to your argument, and why a judge should vote for you."
        ),
        instructions=textwrap.dedent("""\
            1. Read the card once, then set it aside.
            2. Say the claim the card supports (one sentence).
            3. Explain the mechanism or evidence in the card (two to three sentences).
            4. State the impact and why it matters to the resolution.
            5. Time yourself — complete in under 45 seconds.
        """),
        success_criteria=[
            "Claim stated without reading the tag verbatim.",
            "Mechanism or key data point from the card explained accurately.",
            "Connection to resolution impact made explicitly.",
            "Completed in under 45 seconds.",
        ],
        time_limit_seconds=45,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body=body,
    )


def _card_comparison_workout(gap: PrepGap, card_a: dict, card_b: Optional[dict] = None) -> PrepWorkoutCreate:
    tag_a = card_a.get("tag", "Card A")
    body_a = textwrap.shorten(card_a.get("body_text", ""), width=250, placeholder="…")
    if card_b:
        tag_b = card_b.get("tag", "Card B")
        body_b = textwrap.shorten(card_b.get("body_text", ""), width=250, placeholder="…")
        prompt = (
            f"Compare these two conflicting sources:\n\n"
            f"CARD A: {tag_a}\n{body_a}\n\n"
            f"CARD B: {tag_b}\n{body_b}\n\n"
            "In 60 seconds, explain which card a flow judge should prefer and why. "
            "Consider recency, methodology, specificity, and source credibility."
        )
    else:
        prompt = (
            f"You have one card:\n\n"
            f"CARD: {tag_a}\n{body_a}\n\n"
            "Your opponent claims their evidence is more recent. In 60 seconds, explain "
            "why your card should still be preferred — or when you would concede the evidence point."
        )
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",
        user_id="",
        gap_id=gap.id,
        workout_type="card_comparison",
        title=f"Compare and defend: {tag_a[:50]}",
        description="Practice defending your evidence against a competing source.",
        prompt=prompt,
        success_criteria=[
            "Named at least one specific difference between the sources.",
            "Identified which source is more recent (or conceded if theirs is).",
            "Made a comparison argument the judge can flow.",
            "Completed in under 60 seconds.",
        ],
        time_limit_seconds=60,
        source_card_id=card_a.get("id"),
        source_card_tag=tag_a,
        source_card_body=card_a.get("body_text"),
    )


def _frontline_speed_workout(gap: PrepGap, frontline: Optional[dict] = None) -> PrepWorkoutCreate:
    claim = (frontline or {}).get("opponent_claim", "this argument") if frontline else gap.title
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",
        user_id="",
        gap_id=gap.id,
        workout_type="frontline_speed",
        title=f"30-second answer: {claim[:60]}",
        description="Practice answering an opponent argument in under 30 seconds.",
        prompt=(
            f"Your opponent is running: '{claim}'\n\n"
            "You have 30 seconds. Give your best response. Lead with your strongest argument. "
            "State the response type, your claim, and why it outweighs."
        ),
        success_criteria=[
            "Response started within 3 seconds.",
            "Named the response type (no-link, turn, uniqueness takeout, etc.).",
            "Made a complete claim with a reason.",
            "Completed in under 30 seconds.",
        ],
        time_limit_seconds=30,
        source_card_id=None,
        source_card_tag=None,
        source_card_body=None,
    )


def _summary_extension_workout(gap: PrepGap, card: dict) -> PrepWorkoutCreate:
    tag = card.get("tag", "this card")
    body = textwrap.shorten(card.get("body_text", ""), width=250, placeholder="…")
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",
        user_id="",
        gap_id=gap.id,
        workout_type="summary_extension",
        title=f"Summary extension: {tag[:50]}",
        description="Practice extending this card through the summary speech.",
        prompt=(
            f"Extend the following card through the summary speech:\n\n"
            f"TAG: {tag}\nCARD: {body}\n\n"
            "In 60-90 seconds, extend this argument: state the claim, warrant, evidence, "
            "impact, and why it outweighs. Then explain why it's a voting issue."
        ),
        success_criteria=[
            "Claim, warrant, and evidence all stated.",
            "Impact quantified or qualified.",
            "Weighing comparison made.",
            "Voting issue framed for the judge.",
        ],
        time_limit_seconds=90,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body=card.get("body_text"),
    )


def _evidence_indictment_workout(gap: PrepGap, card: dict) -> PrepWorkoutCreate:
    tag = card.get("tag", "the opponent's card")
    body = textwrap.shorten(card.get("body_text", ""), width=300, placeholder="…")
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",
        user_id="",
        gap_id=gap.id,
        workout_type="evidence_indictment",
        title=f"Indict the source: {tag[:50]}",
        description="Practice identifying and explaining the weakness in an evidence card.",
        prompt=(
            f"Analyze this evidence card for weaknesses:\n\n"
            f"TAG: {tag}\nCARD: {body}\n\n"
            "Identify at least one weakness: check the source type, recency, methodology, "
            "scope, causal claims, or whether the conclusion matches the tag. "
            "Explain the weakness in 45 seconds."
        ),
        success_criteria=[
            "Named a specific weakness (not just 'bad source').",
            "Explained why the weakness undermines the argument.",
            "Suggested what a stronger card would look like.",
            "Completed in under 60 seconds.",
        ],
        time_limit_seconds=60,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body=card.get("body_text"),
    )


def _stale_evidence_workout(gap: PrepGap, card: dict) -> PrepWorkoutCreate:
    tag = card.get("tag", "this older card")
    body = textwrap.shorten(card.get("body_text", ""), width=250, placeholder="…")
    pub_date = card.get("published_date", "unknown date")
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",
        user_id="",
        gap_id=gap.id,
        workout_type="stale_evidence",
        title=f"Defend older evidence: {tag[:50]}",
        description="Practice explaining why an older card remains strategically usable.",
        prompt=(
            f"This card is from {pub_date}:\n\n"
            f"TAG: {tag}\nCARD: {body}\n\n"
            "Your opponent says the evidence is outdated. In 45 seconds, explain: "
            "1) whether the claim is time-sensitive; 2) if not, why age doesn't matter; "
            "3) if it is, what you would need to find to replace it."
        ),
        success_criteria=[
            "Identified whether the claim is time-sensitive.",
            "Argued why the evidence remains valid OR conceded it needs updating.",
            "Did not claim old evidence is false solely because of age.",
            "Completed in under 60 seconds.",
        ],
        time_limit_seconds=60,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body=card.get("body_text"),
    )


def _lay_judge_workout(gap: PrepGap, card: dict) -> PrepWorkoutCreate:
    tag = card.get("tag", "this evidence")
    body = textwrap.shorten(card.get("body_text", ""), width=300, placeholder="…")
    author = card.get("author") or card.get("publication") or "the authors"
    return PrepWorkoutCreate(
        workspace_id=gap.blockfile_id or "",
        user_id="",
        gap_id=gap.id,
        workout_type="lay_judge_evidence",
        title=f"Explain for a lay judge: {tag[:50]}",
        description="Practice presenting evidence to a non-flow judge without citation jargon.",
        prompt=(
            f"Read this card to a lay judge:\n\n"
            f"TAG: {tag}\nSOURCE: {author}\nCARD: {body}\n\n"
            "Explain the source and conclusion in plain language. "
            "Do not say 'according to' or cite the author formally. "
            "Instead, explain what the research shows and why it matters — "
            "as if talking to a curious adult who has never seen a debate round."
        ),
        success_criteria=[
            "No jargon a non-debater wouldn't understand.",
            "Source credibility explained in plain terms.",
            "Main conclusion stated clearly.",
            "Connection to the round outcome explained.",
        ],
        time_limit_seconds=60,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body=card.get("body_text"),
    )


# ── Gap → workout type mapping ────────────────────────────────────────────────

def _select_workout_type(gap: PrepGap) -> WorkoutType:
    category_map: dict[str, WorkoutType] = {
        "stale_evidence": "stale_evidence",
        "freshness_unknown": "stale_evidence",
        "missing_warrant": "evidence_explanation",
        "missing_impact": "summary_extension",
        "missing_weighing": "summary_extension",
        "missing_summary_extension": "summary_extension",
        "missing_final_focus_extension": "summary_extension",
        "weak_source": "evidence_indictment",
        "unsupported_card": "evidence_indictment",
        "partial_support": "evidence_indictment",
        "abstract_only": "evidence_indictment",
        "missing_response": "frontline_speed",
        "frontline_underdeveloped": "frontline_speed",
        "insufficient_source_diversity": "card_comparison",
        "duplicate_evidence": "card_comparison",
    }
    return category_map.get(gap.gap_category, "evidence_explanation")


def generate_workout_for_gap(
    gap: PrepGap,
    card: Optional[dict] = None,
    secondary_card: Optional[dict] = None,
    frontline: Optional[dict] = None,
    workspace_id: str = "",
    user_id: str = "",
) -> PrepWorkoutCreate:
    """Generate a workout for a single gap."""
    workout_type = _select_workout_type(gap)
    _card = card or {}

    workout: PrepWorkoutCreate
    if workout_type == "stale_evidence":
        workout = _stale_evidence_workout(gap, _card)
    elif workout_type == "evidence_explanation":
        workout = _evidence_explanation_workout(gap, _card)
    elif workout_type == "summary_extension":
        workout = _summary_extension_workout(gap, _card)
    elif workout_type == "evidence_indictment":
        workout = _evidence_indictment_workout(gap, _card)
    elif workout_type == "frontline_speed":
        workout = _frontline_speed_workout(gap, frontline)
    elif workout_type == "card_comparison":
        workout = _card_comparison_workout(gap, _card, secondary_card)
    else:
        workout = _evidence_explanation_workout(gap, _card)

    workout.workspace_id = workspace_id
    workout.user_id = user_id
    return workout


def generate_workouts_for_report(
    report,  # PrepReadinessReport
    cards: dict[str, dict],
    workspace_id: str,
    user_id: str,
    max_workouts: int = 10,
) -> list[PrepWorkoutCreate]:
    """Generate a bounded set of targeted workouts from a readiness report."""
    workouts: list[PrepWorkoutCreate] = []
    # Prioritize critical and high gaps
    ordered_gaps = sorted(
        report.gaps,
        key=lambda g: (0 if g.severity in ("critical", "high") else 1),
    )

    seen_types: set[str] = set()
    for gap in ordered_gaps:
        if len(workouts) >= max_workouts:
            break
        workout_type = _select_workout_type(gap)
        # Don't generate same workout type more than 3 times
        count = sum(1 for w in workouts if w.workout_type == workout_type)
        if count >= 3:
            continue

        # Pick a card for the workout
        card = cards.get(gap.card_id or "") or (list(cards.values())[0] if cards else {})

        wo = generate_workout_for_gap(
            gap, card, workspace_id=workspace_id, user_id=user_id
        )
        workouts.append(wo)

    return workouts
