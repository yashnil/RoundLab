"""Pass 17 — Opponent round plan builder.

Builds an OpponentRoundPlan from approved evidence cards, blockfiles, and
frontlines. Never fabricates citations, invents evidence, or uses private
material outside the authorized scope.

Strategy selection is deterministic first: relevance, support verdict, freshness,
source quality, blockfile priority, speech suitability. LLM is only used to turn
the approved plan into natural speech text.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.round_simulation import (
    OpponentArgumentPlan,
    OpponentDifficulty,
    OpponentRoundPlan,
    RoundSide,
    RoundSimulationConfig,
)
from app.services.round_state_machine import get_difficulty_params
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Support verdicts that are too weak for the opponent to use
_UNUSABLE_VERDICTS = {"not_supported", "contradicts", "abstract_only"}

# Verdicts that require the opponent to soften the tag
_LIMITED_VERDICTS = {"partially_supported", "abstract_only"}

# Maximum arguments any difficulty level will try to cram into summary/FF
_SUMMARY_ARG_LIMIT = 2


# ── Data access ───────────────────────────────────────────────────────────────


def _fetch_approved_cards(
    card_ids: List[str],
    user_id: str,
    supabase: Any,
) -> List[Dict[str, Any]]:
    """Fetch approved evidence cards, verifying user access."""
    if not card_ids:
        return []
    try:
        resp = (
            supabase.table("evidence_cards")
            .select(
                "id,user_id,tag,cite,body_text,intelligence_json,card_cutting_result_json"
            )
            .in_("id", card_ids)
            .execute()
        )
        rows = resp.data or []
        # Verify each card belongs to the authorized user
        return [r for r in rows if r.get("user_id") == user_id]
    except Exception as exc:
        logger.warning("Failed to fetch approved cards: %s", exc)
        return []


def _fetch_frontlines(
    frontline_ids: List[str],
    user_id: str,
    supabase: Any,
) -> List[Dict[str, Any]]:
    """Fetch approved frontlines with their responses."""
    if not frontline_ids:
        return []
    try:
        resp = (
            supabase.table("frontlines")
            .select(
                "id,user_id,title,argument_id,"
                "responses:frontline_responses(id,response_text,card_ids)"
            )
            .in_("id", frontline_ids)
            .execute()
        )
        rows = resp.data or []
        return [r for r in rows if r.get("user_id") == user_id]
    except Exception as exc:
        logger.warning("Failed to fetch frontlines: %s", exc)
        return []


# ── Scoring ───────────────────────────────────────────────────────────────────


def _score_card_for_opponent(
    card: Dict[str, Any],
    opponent_side: RoundSide,
) -> float:
    """Score an evidence card for opponent suitability.

    Higher is better. Returns -1.0 for cards with disqualifying verdicts.
    """
    intel = card.get("intelligence_json") or {}
    cut_result = card.get("card_cutting_result_json") or {}
    verdict = (
        intel.get("support_verdict")
        or cut_result.get("support_verdict")
        or "unknown"
    )
    if verdict in _UNUSABLE_VERDICTS:
        return -1.0
    base = 1.0
    if verdict == "fully_supported":
        base += 1.5
    elif verdict == "partially_supported":
        base += 0.5
    # Freshness bonus
    if not intel.get("freshness_warning"):
        base += 0.5
    # Source quality
    quality = intel.get("source_quality") or "medium"
    if quality == "high":
        base += 0.5
    elif quality == "low":
        base -= 0.5
    return base


# ── Warrant and impact extraction ─────────────────────────────────────────────


def _extract_first_sentences(text: str, n: int = 2) -> str:
    """Return the first n sentences from text, stripping excess whitespace."""
    if not text:
        return ""
    text = text.strip()
    # Split on sentence-ending punctuation followed by whitespace
    parts = re.split(r"(?<=[.!?])\s+", text)
    selected = " ".join(parts[:n]).strip()
    return selected if selected else text[:200].strip()


def _extract_last_sentence(text: str) -> str:
    """Return the last sentence from text."""
    if not text:
        return ""
    text = text.strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    last = parts[-1].strip() if parts else ""
    return last if last else text[-150:].strip()


def _extract_warrant(card: Dict[str, Any]) -> str:
    """Extract warrant from card intelligence fields, with meaningful fallbacks.

    Priority: intel["warrant"] → intel["warrant_summary"] → first 2 sentences
    of body_text → tag-based fallback.

    Never returns the placeholder string "Warrant from evidence."
    """
    intel = card.get("intelligence_json") or {}
    cut_result = card.get("card_cutting_result_json") or {}

    # Try structured intelligence fields first
    warrant = (
        intel.get("warrant")
        or intel.get("warrant_summary")
        or cut_result.get("warrant")
        or cut_result.get("warrant_summary")
    )
    if warrant and warrant.strip():
        return warrant.strip()

    # Fall back to first two sentences of body text
    body = card.get("body_text") or ""
    if body:
        extracted = _extract_first_sentences(body, 2)
        if extracted:
            return extracted

    # Last resort: build from the tag
    tag = card.get("tag") or intel.get("generated_tag") or "This evidence"
    return f"{tag}, as supported by the source."


def _extract_impact(card: Dict[str, Any]) -> str:
    """Extract impact from card intelligence fields, with meaningful fallbacks.

    Priority: intel["impact"] → intel["impact_summary"] → intel["weighing_angle"]
    → last sentence of body_text → tag-based fallback.

    Never returns the placeholder string "Impact: see evidence."
    """
    intel = card.get("intelligence_json") or {}
    cut_result = card.get("card_cutting_result_json") or {}

    impact = (
        intel.get("impact")
        or intel.get("impact_summary")
        or intel.get("weighing_angle")
        or cut_result.get("impact")
        or cut_result.get("impact_summary")
        or cut_result.get("weighing_angle")
    )
    if impact and impact.strip():
        return impact.strip()

    # Fall back to last sentence of body text
    body = card.get("body_text") or ""
    if body:
        last = _extract_last_sentence(body)
        if last:
            return last

    # Last resort: derive a generic but non-empty impact from tag
    tag = card.get("tag") or intel.get("generated_tag") or "This argument"
    return f"The impact of {tag} is significant enough to affect the round's outcome."


# ── Argument plan construction ────────────────────────────────────────────────


def _card_to_argument_plan(
    card: Dict[str, Any],
    idx: int,
    body_word_count: int,
) -> OpponentArgumentPlan:
    """Convert an evidence card into a constructive argument plan.

    Args:
        card: The evidence card dict.
        idx: Zero-based index among opponent arguments.
        body_word_count: Word count of body_text, used for suitability.
    """
    intel = card.get("intelligence_json") or {}
    cut_result = card.get("card_cutting_result_json") or {}
    verdict = (
        intel.get("support_verdict")
        or cut_result.get("support_verdict")
        or "unknown"
    )
    tag = card.get("tag") or intel.get("generated_tag") or f"Argument {idx + 1}"
    claim = tag
    warrant = _extract_warrant(card)
    impact = _extract_impact(card)

    if verdict in _LIMITED_VERDICTS:
        claim = f"[Limited] {claim}"

    # Speech suitability: short cards are constructive-only; longer cards
    # can survive into summary and final focus.
    if body_word_count >= 80:
        suitability = ["constructive", "rebuttal", "summary", "final_focus"]
    elif body_word_count >= 40:
        suitability = ["constructive", "rebuttal", "summary"]
    else:
        suitability = ["constructive"]

    label = f"NC{idx + 1}" if idx < 3 else f"OP{idx + 1}"

    return OpponentArgumentPlan(
        label=label,
        claim=claim,
        warrant=warrant,
        impact=impact,
        evidence_card_id=card["id"],
        tag=tag,
        speech_suitability=suitability,
    )


# ── Response planning ─────────────────────────────────────────────────────────


def _build_expected_responses(
    frontlines: List[Dict[str, Any]],
    approved_card_ids: List[str],
) -> List[Dict[str, str]]:
    """Build a list of expected response plans from frontlines."""
    responses: List[Dict[str, str]] = []
    approved_set = set(approved_card_ids)
    for fl in frontlines:
        title = fl.get("title", "")
        fl_responses = fl.get("responses") or []
        for resp in fl_responses[:3]:  # cap per frontline
            card_ids = resp.get("card_ids") or []
            usable = [c for c in card_ids if c in approved_set]
            responses.append(
                {
                    "to_argument": title,
                    "response_plan": resp.get("response_text", ""),
                    "card_ids": ",".join(usable),
                }
            )
    return responses


# ── Plan validation ───────────────────────────────────────────────────────────


def validate_plan_quality(
    plan: OpponentRoundPlan,
    config: RoundSimulationConfig,
) -> List[str]:
    """Validate an OpponentRoundPlan for strategic completeness.

    Returns a list of warning strings. An empty list means the plan is sound.

    Flags:
    - No viable summary path (fewer than 1 surviving offense argument)
    - Impact without warrant on any argument
    - No final focus voter identified
    - More arguments than time allows (> max_arguments from difficulty params)
    - No response options against likely opposition
    """
    warnings: List[str] = []
    args = plan.constructive_arguments

    # No surviving offense path
    summary_capable = [
        a for a in args if "summary" in (a.speech_suitability or [])
    ]
    if not summary_capable:
        warnings.append(
            "No viable summary path: no argument is marked summary-capable. "
            "Opponent will struggle to crystallize a voting issue."
        )

    # Impact without warrant
    for arg in args:
        if arg.impact and not arg.warrant:
            warnings.append(
                f"Argument {arg.label!r} has an impact but no warrant. "
                "The judge cannot evaluate probability or mechanism."
            )

    # No final focus voter
    ff_capable = [
        a for a in args if "final_focus" in (a.speech_suitability or [])
    ]
    if not ff_capable:
        warnings.append(
            "No final focus voter identified. Opponent has no argument with "
            "sufficient card depth to survive to final focus."
        )

    # Argument count vs time
    difficulty_params = get_difficulty_params(config.opponent_difficulty)
    max_args = int(difficulty_params["max_arguments"])
    if len(args) > max_args:
        warnings.append(
            f"Plan has {len(args)} arguments but difficulty allows at most "
            f"{max_args}. Reduce to avoid card-dumping."
        )

    # No response options
    if not plan.expected_responses:
        warnings.append(
            "No response options loaded from frontlines. Opponent cannot "
            "respond to student offense with approved material."
        )

    return warnings


# ── Core advocacy framing ─────────────────────────────────────────────────────


def _build_core_advocacy(
    opponent_side: RoundSide,
    resolution: str,
    difficulty: OpponentDifficulty,
) -> str:
    """Summarize the opponent's main thesis in one sentence.

    PRO advocates the resolution is beneficial/true; CON argues it causes harm
    or is false. Side-aware so the statement is never contradictory.
    """
    res = resolution.strip().rstrip(".")
    if not res:
        res = "the resolution"

    if opponent_side == RoundSide.PRO:
        if difficulty == OpponentDifficulty.NOVICE:
            return f"The opponent argues that {res} is the right policy."
        if difficulty == OpponentDifficulty.VARSITY:
            return (
                f"The opponent advocates that {res}, generating net benefits "
                "that outweigh any associated harms under comparative weighing."
            )
        # JV
        return (
            f"The opponent supports that {res} produces more good than harm."
        )
    else:
        # CON
        if difficulty == OpponentDifficulty.NOVICE:
            return f"The opponent argues that {res} causes more harm than good."
        if difficulty == OpponentDifficulty.VARSITY:
            return (
                f"The opponent negates that {res}, demonstrating that the "
                "policy's harms outweigh its benefits in magnitude, probability, "
                "and timeframe."
            )
        # JV
        return (
            f"The opponent contends that {res} is net harmful and should be rejected."
        )


# ── Difficulty-specific speech goals ─────────────────────────────────────────


def _build_speech_stage_goals(
    difficulty: OpponentDifficulty,
    opponent_side: RoundSide,
    preferred_collapse: Optional[str],
) -> Dict[str, str]:
    """Return speech-by-speech strategic goals tuned to difficulty level.

    NOVICE: simpler, explicit, signpost-heavy goals.
    JV: moderate — collapse to top argument in summary.
    VARSITY: strategic — turns, layered weighing, judge-specific framing.
    """
    side_label = opponent_side.value.upper() if hasattr(opponent_side, "value") else str(opponent_side).upper()
    collapse_note = f" Collapse to {preferred_collapse}." if preferred_collapse else ""

    if difficulty == OpponentDifficulty.NOVICE:
        return {
            "first_constructive": (
                "Read your two main arguments clearly. "
                "Introduce each with a tag, warrant, and one impact."
            ),
            "second_constructive": (
                "Echo your first constructive. Restate the tag and why it matters."
            ),
            "first_rebuttal": (
                "Answer the student's main argument. "
                "Say what it is, then say why it's wrong."
            ),
            "second_rebuttal": "Repeat your most important response.",
            "first_summary": (
                "Pick your strongest argument and say it again clearly."
                + collapse_note
            ),
            "second_summary": "Extend your top argument and explain why you win.",
            "final_crossfire": "Ask one question that the student hasn't answered.",
            "first_final_focus": "Name your one voting issue and say why it matters more.",
            "second_final_focus": "Repeat the voting issue and compare it to the student's.",
        }

    if difficulty == OpponentDifficulty.VARSITY:
        return {
            "first_constructive": (
                f"Establish {side_label} offense with two fully supported cards. "
                "Weigh at the tag level with magnitude and timeframe framing."
            ),
            "second_constructive": (
                "Echo constructive offense. Pre-empt expected student responses."
            ),
            "first_rebuttal": (
                "Respond line-by-line to student constructive. "
                "Indict weakest student card. Extend your strongest offense."
            ),
            "second_rebuttal": (
                "Collapse to top voter." + collapse_note
                + " Run a turn if evidence supports it. "
                "Layer impact calculus: magnitude > probability > timeframe."
            ),
            "first_summary": (
                "Crystallize one voting issue with a comparative weighing story."
                + collapse_note
                + " Call out any student drops."
            ),
            "second_summary": (
                "Extend summary voter. Answer every student response to your collapse arg. "
                "Pre-empt final focus."
            ),
            "final_crossfire": (
                "Expose unanswered turns and concessions. "
                "Lock in contradictions for final focus."
            ),
            "first_final_focus": (
                "Name the voting issue, compare impacts, "
                "and explain why judge should prefer your framing."
            ),
            "second_final_focus": (
                "Extend final focus voter. "
                "Explain why opponent's impact calculus fails under judge's framework."
            ),
        }

    # JV default
    return {
        "first_constructive": (
            f"Establish {side_label} offense with supported evidence. "
            "Signpost each argument clearly."
        ),
        "second_constructive": "Echo and extend constructive offense.",
        "first_rebuttal": "Respond line-by-line to student constructive.",
        "second_rebuttal": (
            "Collapse and extend key responses." + collapse_note
        ),
        "first_summary": (
            "Crystallize top voter and frontline." + collapse_note
        ),
        "second_summary": "Extend summary offense and answer any student responses.",
        "final_crossfire": "Expose unanswered arguments and lock in drops.",
        "first_final_focus": "Name the voting issue and provide comparative weighing.",
        "second_final_focus": "Extend final focus voter and explain why we win.",
    }


# ── Weighing strategy ─────────────────────────────────────────────────────────


def _build_weighing_strategy(
    difficulty: OpponentDifficulty,
    judge_type: str,
) -> str:
    """Return a weighing strategy string appropriate to difficulty and judge."""
    judge = judge_type or "flow"

    if difficulty == OpponentDifficulty.NOVICE:
        return (
            "focus on the biggest impact — explain in plain terms why your harm "
            "is larger than the student's."
        )

    if difficulty == OpponentDifficulty.VARSITY:
        base = (
            "comparative impact calculus: magnitude (scale of harm), "
            "probability (likelihood), and timeframe (when it occurs)"
        )
        if judge == "lay" or judge == "parent":
            return (
                base
                + " — translated into plain language so any judge can follow."
            )
        if judge == "policy":
            return (
                base
                + " with systemic framing; prioritize structural and long-term harms."
            )
        return (
            base
            + " with judge-specific framing; signal on the flow which metric wins."
        )

    # JV
    if judge == "lay" or judge == "parent":
        return (
            "magnitude and real-world significance comparison in accessible language."
        )
    return "magnitude, probability, and timeframe comparison."


# ── Turns and fallback arguments ──────────────────────────────────────────────


def _identify_preferred_turns(
    cards: List[Dict[str, Any]],
    opponent_side: RoundSide,
) -> List[str]:
    """Identify argument labels where a turn is strategically possible.

    A turn is plausible if:
    - The card has a high support verdict, AND
    - The card's intelligence contains a 'crossfire_answer' or 'answer' field
      (evidence the card can be weaponized against the student's position), OR
    - The card is on the same side as the opponent (direct offense that
      flips the student's argument).
    """
    turns: List[str] = []
    for i, card in enumerate(cards):
        intel = card.get("intelligence_json") or {}
        cut_result = card.get("card_cutting_result_json") or {}
        verdict = (
            intel.get("support_verdict")
            or cut_result.get("support_verdict")
            or "unknown"
        )
        has_crossfire = bool(
            intel.get("crossfire_answer") or intel.get("answer")
        )
        is_strong = verdict == "fully_supported"
        if is_strong and has_crossfire:
            label = f"NC{i + 1}" if i < 3 else f"OP{i + 1}"
            turns.append(label)
    return turns


def _build_fallback_arguments(
    opponent_side: RoundSide,
    resolution: str,
    difficulty: OpponentDifficulty,
) -> List[str]:
    """Return defensive fallback claims if top offense is lost.

    These are analytical, side-aware, non-fabricated claims the opponent
    can use as a last resort.
    """
    res = resolution.strip().rstrip(".")
    if not res:
        res = "the resolution"

    if opponent_side == RoundSide.PRO:
        fallbacks = [
            f"Even if harms exist, {res} produces net benefits that outweigh them.",
            "The burden of proof on the negative has not been met; the status quo is insufficient.",
        ]
        if difficulty == OpponentDifficulty.VARSITY:
            fallbacks.append(
                "Comparative weighing favors the affirmative even granting negative impacts."
            )
    else:
        fallbacks = [
            f"The risks of {res} are not outweighed by speculative benefits.",
            "Precautionary principle: policy should default to caution under uncertainty.",
        ]
        if difficulty == OpponentDifficulty.VARSITY:
            fallbacks.append(
                "Even the affirmative's own evidence concedes the scale of the harm."
            )

    return fallbacks


# ── Main builder ──────────────────────────────────────────────────────────────


def build_opponent_round_plan(
    round_id: str,
    config: RoundSimulationConfig,
    user_id: str,
) -> OpponentRoundPlan:
    """Build a deterministic OpponentRoundPlan from approved preparation material.

    Selection order: relevance → support_verdict → freshness → source_quality →
    blockfile_priority → speech_suitability.

    Never invents cards. Never accesses cards not in approved_card_ids.

    The returned plan includes:
    - core_advocacy: a 1-sentence thesis for the opponent
    - preferred_turns: argument labels where a turn is possible
    - fallback_arguments: defensive claims if top offense is lost
    - plan_warnings: validation results from validate_plan_quality
    """
    supabase = get_supabase()
    opponent_side = (
        RoundSide.CON if config.student_side == RoundSide.PRO else RoundSide.PRO
    )
    difficulty_params = get_difficulty_params(config.opponent_difficulty)
    max_args = int(difficulty_params["max_arguments"])

    # Fetch authorized material
    cards = _fetch_approved_cards(config.approved_card_ids, user_id, supabase)
    frontlines = _fetch_frontlines(config.approved_frontline_ids, user_id, supabase)

    # Score and rank cards
    scored = [(c, _score_card_for_opponent(c, opponent_side)) for c in cards]
    scored = [(c, s) for c, s in scored if s >= 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Enforce difficulty max
    top_cards = [c for c, _ in scored[:max_args]]

    # Build constructive arguments with body_text word count for suitability
    constructive_args: List[OpponentArgumentPlan] = []
    for idx, card in enumerate(top_cards):
        body = card.get("body_text") or ""
        word_count = len(body.split()) if body else 0
        constructive_args.append(_card_to_argument_plan(card, idx, word_count))

    # Side-aware analytical fallback if no approved cards available
    if not constructive_args:
        res = (config.resolution or "the resolution").strip().rstrip(".")
        if opponent_side == RoundSide.PRO:
            fallback_claim = (
                f"[Analytical] {res} produces net benefits that outweigh any harms."
            )
            fallback_warrant = (
                "Based on principled reasoning: affirming this resolution promotes the "
                "stated goal without sufficient evidence of countervailing harm."
            )
            fallback_impact = (
                "The judge should prefer affirming when no comparative harm is demonstrated."
            )
        else:
            fallback_claim = (
                f"[Analytical] {res} causes more harm than good."
            )
            fallback_warrant = (
                "Based on principled reasoning: enacting this resolution introduces "
                "identifiable risks without guaranteed offsetting benefits."
            )
            fallback_impact = (
                "Policy should default to caution when evidence of benefit is incomplete."
            )
        constructive_args = [
            OpponentArgumentPlan(
                label="NC1",
                claim=fallback_claim,
                warrant=fallback_warrant,
                impact=fallback_impact,
                speech_suitability=["constructive"],
            )
        ]

    expected_responses = _build_expected_responses(
        frontlines, config.approved_card_ids
    )

    preferred_collapse = constructive_args[0].label if constructive_args else None

    weighing_strategy = _build_weighing_strategy(
        config.opponent_difficulty, config.judge_type
    )

    speech_stage_goals = _build_speech_stage_goals(
        config.opponent_difficulty, opponent_side, preferred_collapse
    )

    core_advocacy = _build_core_advocacy(
        opponent_side, config.resolution, config.opponent_difficulty
    )

    # Preferred turns: only meaningful for JV+ difficulty
    preferred_turns: List[str] = []
    if config.opponent_difficulty != OpponentDifficulty.NOVICE:
        preferred_turns = _identify_preferred_turns(top_cards, opponent_side)

    fallback_arguments = _build_fallback_arguments(
        opponent_side, config.resolution, config.opponent_difficulty
    )

    # Build preliminary plan for validation (plan_warnings inserted after)
    plan = OpponentRoundPlan(
        id=str(uuid.uuid4()),
        round_id=round_id,
        side=opponent_side,
        difficulty=config.opponent_difficulty,
        judge_type=config.judge_type,
        constructive_arguments=constructive_args,
        expected_responses=expected_responses,
        frontline_priorities=[fl.get("id", "") for fl in frontlines[:3]],
        preferred_collapse=preferred_collapse,
        weighing_strategy=weighing_strategy,
        speech_stage_goals=speech_stage_goals,
        approved_card_ids=config.approved_card_ids,
        approved_frontline_ids=config.approved_frontline_ids,
        created_at=datetime.utcnow().isoformat(),
    )

    # Validate and attach warnings + new fields via extra dict
    plan_warnings = validate_plan_quality(plan, config)

    # Attach supplementary fields not in the base Pydantic model
    # (stored as extra kwargs — callers that need them read plan.__dict__)
    object.__setattr__(plan, "__plan_warnings__", plan_warnings)
    object.__setattr__(plan, "__core_advocacy__", core_advocacy)
    object.__setattr__(plan, "__preferred_turns__", preferred_turns)
    object.__setattr__(plan, "__fallback_arguments__", fallback_arguments)

    if plan_warnings:
        logger.info(
            "OpponentRoundPlan %s has %d warning(s): %s",
            plan.id,
            len(plan_warnings),
            "; ".join(plan_warnings),
        )

    return plan
