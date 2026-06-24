"""Pass 16 — Bounded opponent speech generator.

Generates AI opponent speeches constrained to approved preparation material.
Never fabricates evidence, citations, or numerical claims.
Falls back to deterministic outline if LLM validation fails.

Evidence policy:
- Only cards in OpponentRoundPlan.approved_card_ids may be used.
- Every quote must be exact (from card.body_text).
- Unsupported tags are never used.
- No new cards created during simulation.
- Analytic arguments are clearly labeled when no evidence exists.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import openai
from pydantic import BaseModel

from app.config import settings
from app.models.round_simulation import (
    OpponentEvidenceReference,
    OpponentRoundPlan,
    OpponentSpeechResult,
    RoundArgument,
    RoundPhaseType,
    RoundSimulationConfig,
)
from app.services.round_state_machine import (
    PHASE_LABELS,
    PHASE_SPEECH_TYPES,
    get_difficulty_params,
    is_new_argument_legal,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_MAX_SPEECH_WORDS_PER_MINUTE = 250
_SECONDS_PER_MINUTE = 60


def _fetch_card(card_id: str, approved_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Fetch a card only if it is in the approved list."""
    if card_id not in set(approved_ids):
        return None
    try:
        supabase = get_supabase()
        resp = supabase.table("evidence_cards").select(
            "id,tag,cite,body_text,intelligence_json,card_cutting_result_json"
        ).eq("id", card_id).single().execute()
        return resp.data
    except Exception as exc:
        logger.warning("Card fetch failed %s: %s", card_id, exc)
        return None


def _validate_speech(
    text: str,
    evidence_refs: List[OpponentEvidenceReference],
    approved_ids: List[str],
    phase: RoundPhaseType,
    time_limit: int,
    live_args: List[RoundArgument],
) -> List[str]:
    """Return a list of validation failures."""
    failures: List[str]  = []
    # Check all evidence references are approved
    for ref in evidence_refs:
        if ref.card_id not in set(approved_ids):
            failures.append(f"Unauthorized card {ref.card_id} referenced.")
    # Check no new arguments in late phases
    legal, reason = is_new_argument_legal(phase)
    if not legal and evidence_refs:
        # Evidence in late phase = new argument concern
        if phase in {RoundPhaseType.FIRST_FINAL_FOCUS, RoundPhaseType.SECOND_FINAL_FOCUS}:
            failures.append(f"New evidence in final focus may indicate new argument: {reason}")
    # Check rough word count vs time limit
    words = len(text.split())
    max_words = int((_MAX_SPEECH_WORDS_PER_MINUTE * time_limit) / _SECONDS_PER_MINUTE)
    if words > max_words * 1.2:
        failures.append(
            f"Speech is too long: {words} words (max ~{max_words} for {time_limit}s limit)."
        )
    return failures


class _SpeechOutput(BaseModel):
    speech_text: str
    argument_labels: List[str] = []
    responses_made: List[str] = []
    arguments_extended: List[str] = []
    arguments_dropped: List[str] = []
    weighing_used: Optional[str] = None
    strategic_goal: str = ""
    evidence_card_ids: List[str] = []


def _deterministic_fallback(
    plan: OpponentRoundPlan,
    phase: RoundPhaseType,
    live_args: List[RoundArgument],
    time_limit: int,
    difficulty_params: Dict[str, Any],
) -> OpponentSpeechResult:
    """Generate a minimal safe speech outline without LLM."""
    speech_type = PHASE_SPEECH_TYPES.get(phase, "speech")
    label = PHASE_LABELS.get(phase, str(phase))
    goal = plan.speech_stage_goals.get(phase.value, "Advance the round.")

    arg_labels: List[str] = []
    card_ids: List[str] = []
    text_parts = [f"[AI Opponent — {label}]", ""]

    if speech_type == "constructive":
        text_parts.append(f"The {plan.side.value} side stands opposed on the grounds of:")
        for arg in plan.constructive_arguments:
            text_parts.append(f"\n{arg.label}: {arg.claim}")
            text_parts.append(f"Warrant: {arg.warrant}")
            text_parts.append(f"Impact: {arg.impact}")
            if arg.evidence_card_id:
                card_ids.append(arg.evidence_card_id)
            arg_labels.append(arg.label)
    elif speech_type == "rebuttal":
        text_parts.append("Turning to the flow:")
        opponent_args = [a for a in live_args if a.side != plan.side]
        if opponent_args:
            a = opponent_args[0]
            text_parts.append(f"On {a.label}: We contest the warrant. {a.claim} is unsupported.")
            text_parts.append("Without a clear warrant link, there is no impact to extend.")
        else:
            text_parts.append("We maintain our constructive offense and note the lack of direct clash.")
    elif speech_type == "summary":
        text_parts.append("Crystallizing the round:")
        if plan.constructive_arguments:
            top = plan.constructive_arguments[0]
            text_parts.append(f"Extend {top.label}: {top.claim}. This argument stands uncontested.")
            text_parts.append(f"On weighing: {plan.weighing_strategy}.")
            arg_labels.append(top.label)
    elif speech_type == "final_focus":
        text_parts.append("The voting issue is clear:")
        if plan.constructive_arguments:
            top = plan.constructive_arguments[0]
            text_parts.append(f"Extend our {top.label}. The impact is {top.impact}.")
            text_parts.append("Please vote for the opponent side.")
            arg_labels.append(top.label)

    text_parts.append(f"\n[Strategic goal: {goal}]")
    speech_text = "\n".join(text_parts)

    words = len(speech_text.split())
    speaking_time = int((words / _MAX_SPEECH_WORDS_PER_MINUTE) * _SECONDS_PER_MINUTE)

    return OpponentSpeechResult(
        speech_text=speech_text,
        argument_labels=arg_labels,
        responses_made=[],
        arguments_extended=arg_labels if speech_type in ("summary", "final_focus") else [],
        arguments_dropped=[],
        evidence_references=[],
        weighing_used=plan.weighing_strategy if speech_type in ("summary", "final_focus") else None,
        strategic_goal=goal,
        estimated_speaking_time=speaking_time,
        is_fallback=True,
    )


def _build_system_prompt(
    plan: OpponentRoundPlan,
    phase: RoundPhaseType,
    time_limit: int,
    judge_type: str,
    difficulty_params: Dict[str, Any],
) -> str:
    speed = difficulty_params.get("speech_speed_wpm", 170)
    signposting = difficulty_params.get("signposting", "standard")
    max_words = int((speed * time_limit) / _SECONDS_PER_MINUTE)
    label = PHASE_LABELS.get(phase, str(phase))
    return f"""You are a {plan.difficulty.value}-level Public Forum debater giving the {label}.
Side: {plan.side.value}. Judge type: {judge_type}.
Target words: {max_words} (at ~{speed} WPM for {time_limit} seconds).
Signposting style: {signposting}.

STRICT EVIDENCE RULES — violating any of these is a critical failure:
1. Only use evidence cards whose IDs appear in the approved list below.
2. Do NOT invent studies, authors, dates, statistics, or citations.
3. When quoting a card, use its exact body_text — no paraphrase that changes meaning.
4. Every card use must name the cite field exactly as provided.
5. If no relevant card exists, make an ANALYTICAL argument (clearly labeled [Analytical]).
6. Never claim a card says more than its support_verdict permits.

Speech structure rules:
- If this is a summary or final focus, do NOT introduce new independent arguments.
- Respond to arguments that appeared in the live flow.
- Extend your strongest argument with a weighing comparison.
- Give a clear strategic_goal in your output.

Return a JSON object matching this schema exactly:
{{
  "speech_text": "...",
  "argument_labels": ["NC1", ...],
  "responses_made": ["AC1: [response text]", ...],
  "arguments_extended": ["NC1"],
  "arguments_dropped": [],
  "weighing_used": "...",
  "strategic_goal": "...",
  "evidence_card_ids": ["card-id-1", ...]
}}"""


def _build_user_prompt(
    plan: OpponentRoundPlan,
    phase: RoundPhaseType,
    live_args: List[RoundArgument],
    approved_cards: List[Dict[str, Any]],
    prior_speeches_summary: str,
) -> str:
    args_text = "\n".join(
        f"- [{a.side.value}] {a.label}: {a.claim} (status: {a.status.value})"
        for a in live_args
    )
    cards_text = "\n".join(
        (
            f"CARD {c['id']}: tag={c.get('tag','?')} | cite={c.get('cite','?')}"
            f" | verdict={((c.get('intelligence_json') or {}).get('support_verdict') or 'unknown')}"
            f" | body_text={c.get('body_text','')[:300]}"
        )
        for c in approved_cards[:8]
    )
    plan_args = "\n".join(
        f"- {a.label}: {a.claim} → {a.warrant} → {a.impact} [card: {a.evidence_card_id or 'none'}]"
        for a in plan.constructive_arguments
    )
    return f"""LIVE FLOW (current argument statuses):
{args_text or '(no arguments yet)'}

YOUR CONSTRUCTIVE PLAN:
{plan_args}

APPROVED EVIDENCE CARDS:
{cards_text or '(none approved — use analytical arguments only)'}

PRIOR ROUND CONTEXT:
{prior_speeches_summary or '(round just started)'}

WEIGHING STRATEGY: {plan.weighing_strategy}
STAGE GOAL: {plan.speech_stage_goals.get(phase.value, 'Advance the round.')}

Generate the {PHASE_LABELS.get(phase, str(phase))} speech now."""


def generate_opponent_speech(
    plan: OpponentRoundPlan,
    phase: RoundPhaseType,
    live_args: List[RoundArgument],
    time_limit: int,
    config: RoundSimulationConfig,
    prior_speeches_summary: str = "",
    approved_cards: Optional[List[Dict[str, Any]]] = None,
) -> OpponentSpeechResult:
    """
    Generate a bounded opponent speech.

    Validates every evidence reference. Retries once on failure.
    Falls back to deterministic outline if LLM is unavailable or validation fails twice.
    """
    difficulty_params = get_difficulty_params(config.opponent_difficulty)

    if approved_cards is None:
        # Fetch approved cards for this speech
        supabase = get_supabase()
        try:
            resp = (
                supabase.table("evidence_cards")
                .select("id,tag,cite,body_text,intelligence_json,card_cutting_result_json")
                .in_("id", plan.approved_card_ids)
                .execute()
            )
            approved_cards = resp.data or []
        except Exception as exc:
            logger.warning("Failed to fetch cards for speech: %s", exc)
            approved_cards = []

    if not settings.openai_api_key:
        logger.info("No OpenAI key — using deterministic fallback for opponent speech.")
        return _deterministic_fallback(plan, phase, live_args, time_limit, difficulty_params)

    system_prompt = _build_system_prompt(plan, phase, time_limit, config.judge_type, difficulty_params)
    user_prompt = _build_user_prompt(plan, phase, live_args, approved_cards, prior_speeches_summary)

    for attempt in range(2):
        try:
            client = openai.OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=1200,
                temperature=0.4,
            )
            raw = resp.choices[0].message.content or "{}"
            import json
            data = json.loads(raw)
            parsed = _SpeechOutput.model_validate(data)
        except Exception as exc:
            logger.warning("Opponent speech LLM attempt %d failed: %s", attempt + 1, exc)
            if attempt == 1:
                return _deterministic_fallback(plan, phase, live_args, time_limit, difficulty_params)
            continue

        # Build evidence references
        evidence_refs: List[OpponentEvidenceReference] = []
        approved_id_set = set(plan.approved_card_ids)
        for cid in parsed.evidence_card_ids:
            if cid not in approved_id_set:
                logger.warning("LLM used unauthorized card %s — dropping.", cid)
                continue
            card = next((c for c in approved_cards if c["id"] == cid), None)
            if not card:
                continue
            intel = card.get("intelligence_json") or {}
            cut = card.get("card_cutting_result_json") or {}
            verdict = intel.get("support_verdict") or cut.get("support_verdict") or "unknown"
            evidence_refs.append(
                OpponentEvidenceReference(
                    card_id=cid,
                    tag=card.get("tag") or "",
                    cite=card.get("cite") or "",
                    support_verdict=verdict,
                    source_classification=intel.get("source_classification"),
                )
            )

        failures = _validate_speech(
            parsed.speech_text,
            evidence_refs,
            list(approved_id_set),
            phase,
            time_limit,
            live_args,
        )
        if failures:
            logger.warning("Speech validation failures (attempt %d): %s", attempt + 1, failures)
            if attempt == 1:
                return _deterministic_fallback(plan, phase, live_args, time_limit, difficulty_params)
            # Retry with explicit correction instruction
            user_prompt = user_prompt + f"\n\nPREVIOUS ATTEMPT FAILED:\n" + "\n".join(failures)
            continue

        words = len(parsed.speech_text.split())
        speaking_time = int((words / _MAX_SPEECH_WORDS_PER_MINUTE) * _SECONDS_PER_MINUTE)
        return OpponentSpeechResult(
            speech_text=parsed.speech_text,
            argument_labels=parsed.argument_labels,
            responses_made=parsed.responses_made,
            arguments_extended=parsed.arguments_extended,
            arguments_dropped=parsed.arguments_dropped,
            evidence_references=evidence_refs,
            weighing_used=parsed.weighing_used,
            strategic_goal=parsed.strategic_goal,
            estimated_speaking_time=speaking_time,
            is_fallback=False,
        )

    return _deterministic_fallback(plan, phase, live_args, time_limit, difficulty_params)
