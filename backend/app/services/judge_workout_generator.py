"""Pass 15 — Judge-Specific Workout Generator.

Generates drills from actual prepared material.
Evidence body text is NOT included (only a bounded snapshot ≤500 chars).
Source card IDs are referenced. Drill-attempt infrastructure from existing workouts.
"""

from __future__ import annotations

from typing import Optional

from app.models.judge_adaptation import JudgeType, JudgeWorkoutCreate, WorkoutJudgeType


_WORKOUT_TIME_SECONDS: dict[str, int] = {
    "lay_explanation": 90,
    "parent_context": 90,
    "flow_extension": 45,
    "technical_concession": 60,
    "judge_switch": 120,
    "evidence_adaptation": 90,
    "final_focus_voter": 90,
}


def _snap_body(body: Optional[str], max_chars: int = 500) -> Optional[str]:
    """Return a bounded snapshot of the card body. NEVER the full text in workouts."""
    if not body:
        return None
    return body[:max_chars]


# ── Workout builders ──────────────────────────────────────────────────────────

def build_lay_explanation(
    card: dict,
    user_id: str,
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    tag = card.get("tag", "")
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="lay_explanation",
        judge_type="lay",
        title=f"Lay Explanation: {tag[:60]}" if tag else "Lay Explanation Drill",
        description="Explain your argument without debate jargon in 30 seconds.",
        prompt=(
            "Your judge is a community member with no debate experience. "
            "In 30 seconds, explain:\n"
            "1. What does this evidence say?\n"
            "2. Why should anyone care?\n"
            "3. What does it mean for this debate?\n\n"
            "Do NOT use the words: contention, extend, flow, non-unique, turn, frontline, or impact."
        ),
        instructions="Speak out loud. Time yourself. Pretend you're explaining to a neighbor.",
        success_criteria=[
            "No debate jargon used",
            "Explained in terms a non-debater would understand",
            "Connected to a real-world consequence",
            "Completed within 30 seconds",
        ],
        time_limit_seconds=30,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body_snapshot=_snap_body(card.get("body_text")),
        workspace_id=workspace_id,
    )


def build_parent_context(
    card: dict,
    user_id: str,
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    tag = card.get("tag", "")
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="parent_context",
        judge_type="parent",
        title=f"Parent Context Drill: {tag[:60]}" if tag else "Parent Context Drill",
        description="Provide full context for a parent judge unfamiliar with the topic.",
        prompt=(
            "Imagine your judge is a parent who attended all your practices but has never debated. "
            "In 45 seconds:\n"
            "1. Set up the topic in plain terms.\n"
            "2. Explain what your argument claims.\n"
            "3. Explain why it's fair to accept.\n"
            "4. Give a real-world example.\n"
            "Define any debate terms the first time you use them."
        ),
        instructions="Include a term definition (e.g., 'when I say impact, I mean...') and a concrete example.",
        success_criteria=[
            "Defined at least one debate term",
            "Provided real-world context",
            "Explained why the claim is fair/reasonable",
            "Did not assume policy knowledge",
            "Completed within 45 seconds",
        ],
        time_limit_seconds=45,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body_snapshot=_snap_body(card.get("body_text")),
        workspace_id=workspace_id,
    )


def build_flow_extension(
    argument_title: Optional[str],
    user_id: str,
    argument_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    title_str = argument_title or "your argument"
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="flow_extension",
        judge_type="flow",
        title=f"Flow Extension Drill: {title_str[:60]}",
        description="Extend your argument in 20 seconds for a flow judge.",
        prompt=(
            f"Extend '{title_str}' in under 20 seconds.\n"
            "Format: 'Extend [claim label] — [evidence tag] — still true because [one sentence] — impacts [impact label]'\n\n"
            "The judge flows every word. A single dropped component = dropped argument."
        ),
        instructions="Say it out loud. Start with the label. Hit all four components. Stay under 20 seconds.",
        success_criteria=[
            "Named the argument label explicitly",
            "Referenced the evidence by tag",
            "Explained why it's still true",
            "Named the impact",
            "Completed in under 20 seconds",
        ],
        time_limit_seconds=20,
        source_argument_id=argument_id,
        workspace_id=workspace_id,
    )


def build_technical_concession(
    frontline: dict,
    responses: list[dict],
    user_id: str,
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    fl_title = frontline.get("title", "this argument")
    # Find concede_and_turn or turn responses
    offensive = [r for r in responses if r.get("response_type") in ("turn", "straight_turn", "concede_and_turn")]
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="technical_concession",
        judge_type="technical",
        title=f"Technical Concession Drill: {fl_title[:60]}",
        description="Identify and exploit opponent concessions precisely.",
        prompt=(
            f"Your opponent is running '{fl_title}'. "
            "In 60 seconds, identify:\n"
            "1. What has your opponent conceded (not answered) in their last speech?\n"
            "2. How does that concession create offense for you?\n"
            "3. What is the precise logical chain from their concession to your impact?\n\n"
            f"{'Known offensive answers: ' + ', '.join(r.get('response_type','') for r in offensive[:2]) if offensive else ''}"
        ),
        instructions="Be precise. Say 'They conceded X in their [speech]. That means [Y]. Which means [Z].'",
        success_criteria=[
            "Identified a specific concession by name",
            "Traced a logical chain from concession to impact",
            "Distinguished offense from defense",
            "Did not overstate the concession",
            "Completed within 60 seconds",
        ],
        time_limit_seconds=60,
        workspace_id=workspace_id,
    )


def build_judge_switch(
    tag: Optional[str],
    user_id: str,
    source_card_id: Optional[str] = None,
    body: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    tag_str = tag or "your argument"
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="judge_switch",
        judge_type="lay",  # primary judge
        comparison_judge_type="technical",
        title=f"Judge Switch Drill: {tag_str[:50]} (Lay → Technical)",
        description="Deliver the same argument differently for a lay judge, then a technical judge.",
        prompt=(
            f"Argument: '{tag_str}'\n\n"
            "ROUND 1 — Lay Judge (30 seconds):\n"
            "Explain this argument to someone with no debate experience. Use plain language and a real-world example.\n\n"
            "ROUND 2 — Technical Judge (30 seconds):\n"
            "Present the same argument with precise labels, explicit claim/warrant/impact, and concession tracking.\n\n"
            "The facts and evidence do NOT change between rounds."
        ),
        instructions="Complete both rounds. Note what you changed and what stayed the same.",
        success_criteria=[
            "Lay version: no jargon, real-world example",
            "Technical version: explicit labels, exact argument structure",
            "Facts and source not changed between versions",
            "Both completed within time",
            "Can articulate what changed and why",
        ],
        time_limit_seconds=120,
        source_card_id=source_card_id,
        source_card_tag=tag,
        source_card_body_snapshot=_snap_body(body),
        workspace_id=workspace_id,
    )


def build_evidence_adaptation(
    card: dict,
    user_id: str,
    comparison_judge: JudgeType = "flow",
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    tag = card.get("tag", "")
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="evidence_adaptation",
        judge_type="parent",
        comparison_judge_type=comparison_judge,
        title=f"Evidence Adaptation: {tag[:50]}" if tag else "Evidence Adaptation Drill",
        description="Introduce the same card differently for a parent judge and a flow judge.",
        prompt=(
            f"Card tag: '{tag}'\n\n"
            "PARENT INTRODUCTION (30 seconds):\n"
            "'According to [who/what org], [what they found in simple terms]. "
            "This matters because [one sentence real-world impact].'\n\n"
            f"{comparison_judge.upper()} INTRODUCTION (20 seconds):\n"
            "'[Short citation] — [claim] — [warrant] — [impact label].'\n\n"
            "Do NOT change what the evidence says. Only change how you introduce it."
        ),
        instructions="Practice both out loud. The card's factual content stays identical.",
        success_criteria=[
            "Parent version: source name, plain finding, real-world impact",
            "Flow version: short citation, claim, warrant, impact in one breath",
            "Both accurate to the original card",
            "Completed in time",
        ],
        time_limit_seconds=90,
        source_card_id=card.get("id"),
        source_card_tag=tag,
        source_card_body_snapshot=_snap_body(card.get("body_text")),
        workspace_id=workspace_id,
    )


def build_final_focus_voter(
    argument_title: Optional[str],
    user_id: str,
    judge_type: JudgeType = "flow",
    comparison_judge: Optional[JudgeType] = None,
    argument_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> JudgeWorkoutCreate:
    title_str = argument_title or "your main argument"
    comp_j = comparison_judge or ("lay" if judge_type == "flow" else "flow")
    return JudgeWorkoutCreate(
        user_id=user_id,
        workout_type="final_focus_voter",
        judge_type=judge_type,
        comparison_judge_type=comp_j,
        title=f"Final Focus Voter Drill: {title_str[:50]}",
        description=f"Frame the same voter for {judge_type} and {comp_j} judges in final focus.",
        prompt=(
            f"Argument: '{title_str}'\n\n"
            f"{judge_type.upper()} VERSION (30 seconds):\n"
            f"{'Extend and weigh in precise flow format.' if judge_type in ('flow','technical') else 'Tell the story of why this argument wins the round.'}\n\n"
            f"{comp_j.upper()} VERSION (30 seconds):\n"
            f"{'Tell the story of why this argument wins the round.' if comp_j in ('lay','parent') else 'Extend and weigh in precise flow format.'}\n\n"
            "No new content in final focus. Only extend what is already on the flow."
        ),
        instructions="Deliver both versions. Compare how you framed the voter differently.",
        success_criteria=[
            "No new arguments introduced",
            "Both versions accurate to what was in summary",
            "Judge-appropriate framing in each version",
            f"{judge_type} version completed in 30s",
            f"{comp_j} version completed in 30s",
        ],
        time_limit_seconds=90,
        source_argument_id=argument_id,
        workspace_id=workspace_id,
    )


# ── Dispatch ──────────────────────────────────────────────────────────────────

def generate_judge_workout(
    judge_type: JudgeType,
    source_type: str,
    *,
    card: Optional[dict] = None,
    frontline: Optional[dict] = None,
    responses: Optional[list[dict]] = None,
    argument_title: Optional[str] = None,
    argument_id: Optional[str] = None,
    user_id: str,
    workspace_id: Optional[str] = None,
) -> Optional[JudgeWorkoutCreate]:
    """Generate the most appropriate workout for the source type and judge type."""
    card = card or {}
    responses = responses or []

    if source_type == "evidence":
        if judge_type in ("lay",):
            return build_lay_explanation(card, user_id, workspace_id)
        if judge_type in ("parent",):
            return build_parent_context(card, user_id, workspace_id)
        if judge_type in ("flow", "technical", "coach"):
            return build_evidence_adaptation(card, user_id, judge_type, workspace_id)

    if source_type in ("argument", "section"):
        if judge_type in ("flow", "coach"):
            return build_flow_extension(argument_title, user_id, argument_id, workspace_id)
        if judge_type == "technical" and frontline:
            return build_technical_concession(frontline, responses, user_id, workspace_id)
        return build_judge_switch(
            card.get("tag") or argument_title,
            user_id,
            source_card_id=card.get("id"),
            body=card.get("body_text"),
            workspace_id=workspace_id,
        )

    if source_type == "frontline":
        if judge_type == "technical":
            return build_technical_concession(frontline or {}, responses, user_id, workspace_id)
        return build_judge_switch(
            card.get("tag") or argument_title,
            user_id,
            source_card_id=card.get("id"),
            body=card.get("body_text"),
            workspace_id=workspace_id,
        )

    if source_type in ("summary", "final_focus"):
        return build_final_focus_voter(
            argument_title,
            user_id,
            judge_type=judge_type,
            comparison_judge=None,
            argument_id=argument_id,
            workspace_id=workspace_id,
        )

    # Default
    return build_judge_switch(
        card.get("tag") or argument_title,
        user_id,
        source_card_id=card.get("id"),
        body=card.get("body_text"),
        workspace_id=workspace_id,
    )
