"""Pass 17 — Crossfire simulation.

AI opponent asks targeted questions based on unresolved flow issues.
Challenges evidence support, tests warrants, exposes missing links.
Never introduces new evidence.
Records concessions, contradictions, and evasions using the dedicated
concession_detector module.

Improvements over Pass 16:
- Argument rotation: don't keep targeting the same argument
- Question type taxonomy (8 types)
- Multi-turn follow-up via generate_followup_question
- Improved evasion detection via concession_detector
- Question dedup via _normalize_question
- AI answers to student questions via generate_ai_answer
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set

import openai
from pydantic import BaseModel

from app.config import settings
from app.models.round_simulation import (
    ArgumentFlowStatus,
    CrossfireExchange,
    CrossfireExchangeType,
    RoundArgument,
    RoundPhaseType,
    RoundSide,
    RoundSimulationConfig,
)
from app.services.concession_detector import (
    ConcessionFinding,
    detect_concessions,
    detect_contradiction,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Question type literals
# ---------------------------------------------------------------------------

QuestionType = Literal[
    "clarification",
    "warrant_test",
    "evidence_challenge",
    "scope_challenge",
    "causal_challenge",
    "impact_comparison",
    "concession_extraction",
    "contradiction_exposure",
]

_ALL_QUESTION_TYPES: List[QuestionType] = [
    "clarification",
    "warrant_test",
    "evidence_challenge",
    "scope_challenge",
    "causal_challenge",
    "impact_comparison",
    "concession_extraction",
    "contradiction_exposure",
]

# ---------------------------------------------------------------------------
# Stopwords for question dedup
# ---------------------------------------------------------------------------

_STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "on",
    "at", "by", "for", "with", "about", "from", "and", "or", "but",
    "if", "then", "so", "that", "this", "these", "those", "you", "your",
    "I", "my", "we", "our", "it", "its", "what", "which", "how",
}


def _normalize_question(q: str) -> str:
    """Lowercase and remove stopwords for dedup comparison."""
    tokens = re.findall(r"\b\w+\b", q.lower())
    return " ".join(t for t in tokens if t not in _STOPWORDS)


# ---------------------------------------------------------------------------
# Argument targeting with rotation
# ---------------------------------------------------------------------------

def _already_targeted(arg: RoundArgument, prior_exchanges: List[CrossfireExchange]) -> bool:
    """Return True if this argument was already targeted in prior exchanges."""
    for ex in prior_exchanges:
        if ex.target_argument and ex.target_argument == arg.label:
            return True
    return False


def _find_target_argument(
    live_args: List[RoundArgument],
    questioner_side: RoundSide,
    prior_exchanges: Optional[List[CrossfireExchange]] = None,
    prefer_dropped: bool = False,
) -> Optional[RoundArgument]:
    """Select the best argument to target with a crossfire question.

    Priority order:
      1. LIVE arguments not yet targeted this crossfire
      2. EXTENDED arguments not yet targeted
      3. INTRODUCED arguments not yet targeted
      4. Any untargeted opponent argument
      5. Already-targeted arguments (rotation fallback)
      6. First available opponent argument (last resort)
    """
    prior_exchanges = prior_exchanges or []
    opponent_side = RoundSide.CON if questioner_side == RoundSide.PRO else RoundSide.PRO
    candidates = [a for a in live_args if a.side == opponent_side]
    if not candidates:
        return None

    untargeted = [a for a in candidates if not _already_targeted(a, prior_exchanges)]

    # Tier 1: untargeted LIVE
    tier1 = [a for a in untargeted if a.status == ArgumentFlowStatus.LIVE]
    if tier1:
        return tier1[0]

    # Tier 2: untargeted EXTENDED
    tier2 = [a for a in untargeted if a.status == ArgumentFlowStatus.EXTENDED]
    if tier2:
        return tier2[0]

    # Tier 3: untargeted INTRODUCED
    tier3 = [a for a in untargeted if a.status == ArgumentFlowStatus.INTRODUCED]
    if tier3:
        return tier3[0]

    # Tier 4: any untargeted
    if untargeted:
        return untargeted[0]

    # Fallback: rotation among already-targeted — pick a different one than last
    if prior_exchanges:
        last_target = prior_exchanges[-1].target_argument
        rotation = [a for a in candidates if a.label != last_target]
        if rotation:
            return rotation[0]

    # Last resort: prefer dropped if requested
    if prefer_dropped:
        dropped = [a for a in candidates if a.status == ArgumentFlowStatus.DROPPED]
        if dropped:
            return dropped[0]

    return candidates[0]


# ---------------------------------------------------------------------------
# LLM-based question generation
# ---------------------------------------------------------------------------

class _CrossfireOutput(BaseModel):
    question: str
    target_argument: str
    question_type: str = "warrant_test"
    strategic_significance: str = "medium"


def _generate_question_llm(
    target_arg: RoundArgument,
    questioner_side: RoundSide,
    judge_type: str,
    phase: RoundPhaseType,
    question_type: QuestionType = "warrant_test",
    asked_questions: Optional[List[str]] = None,
) -> Optional[str]:
    """Use LLM to generate a targeted crossfire question. Returns None on failure."""
    if not settings.openai_api_key:
        return None

    asked_note = ""
    if asked_questions:
        asked_note = (
            "\n\nAvoid repeating these already-asked questions:\n"
            + "\n".join(f"- {q}" for q in asked_questions[-5:])
        )

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a {questioner_side.value} debater in a PF crossfire "
                        f"({phase.value}). Generate ONE sharp crossfire question of type "
                        f"'{question_type}'. "
                        "Do NOT introduce new evidence or make new arguments. "
                        "Do NOT ask compound or multi-part questions. "
                        "The question should be under 40 words and end with a question mark. "
                        "Return a JSON object with keys: "
                        "\"question\", \"target_argument\", \"question_type\", \"strategic_significance\"."
                        + asked_note
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Target argument: [{target_arg.label}] {target_arg.claim}\n"
                        f"Warrant: {target_arg.warrant or 'not clearly stated'}\n"
                        f"Impact: {target_arg.impact or 'not stated'}\n"
                        f"Status: {target_arg.status.value}\n"
                        f"Judge type: {judge_type}\n"
                        f"Question type requested: {question_type}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=250,
            temperature=0.6,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        out = _CrossfireOutput.model_validate(data)
        return out.question
    except Exception as exc:
        logger.warning("LLM crossfire question failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Deterministic fallback questions per question type
# ---------------------------------------------------------------------------

_FALLBACK_TEMPLATES: Dict[str, str] = {
    "clarification": (
        "In your {label} argument, you claim '{claim}'. "
        "Can you clarify exactly what you mean by that?"
    ),
    "warrant_test": (
        "In your {label} argument, you claim '{claim}'. "
        "What is the specific mechanism that links your warrant to that impact?"
    ),
    "evidence_challenge": (
        "For your {label} argument, what is the source for '{claim}' "
        "and can you tell me the year of that evidence?"
    ),
    "scope_challenge": (
        "Your {label} argument claims '{claim}'. "
        "Does that apply in all cases, or are there significant exceptions?"
    ),
    "causal_challenge": (
        "In your {label} argument, you say '{claim}'. "
        "What is the direct causal link from that claim to your impact?"
    ),
    "impact_comparison": (
        "Even if your {label} argument is true, why does '{impact}' "
        "outweigh our impacts on probability and magnitude?"
    ),
    "concession_extraction": (
        "Can you tell me specifically what evidence supports '{claim}' "
        "in your {label} argument, or is this an analytical assertion?"
    ),
    "contradiction_exposure": (
        "Earlier you said '{claim}' in your {label} argument. "
        "How does that square with what you said in your previous speech?"
    ),
}


def _fallback_question(target_arg: RoundArgument, question_type: QuestionType = "warrant_test") -> str:
    """Generate a deterministic crossfire question without LLM."""
    template = _FALLBACK_TEMPLATES.get(question_type, _FALLBACK_TEMPLATES["warrant_test"])
    impact_text = target_arg.impact or "your stated impact"
    return template.format(
        label=target_arg.label,
        claim=target_arg.claim[:120],
        impact=impact_text[:80],
    )


def _pick_question_type(
    target_arg: RoundArgument,
    sequence: int,
    prior_exchanges: List[CrossfireExchange],
) -> QuestionType:
    """Pick the most strategically appropriate question type for this exchange."""
    # Vary by sequence so consecutive questions to same argument use different types
    if target_arg.warrant is None:
        return "warrant_test"
    if target_arg.evidence_card_id is None and sequence % 3 == 0:
        return "evidence_challenge"
    if target_arg.impact is None:
        return "impact_comparison"
    # Rotate through the full set based on sequence parity
    rotation_types: List[QuestionType] = [
        "warrant_test",
        "causal_challenge",
        "scope_challenge",
        "evidence_challenge",
        "impact_comparison",
        "concession_extraction",
    ]
    idx = sequence % len(rotation_types)
    return rotation_types[idx]


# ---------------------------------------------------------------------------
# Public: generate_crossfire_question
# ---------------------------------------------------------------------------

def generate_crossfire_question(
    round_id: str,
    phase: RoundPhaseType,
    questioner_side: RoundSide,
    live_args: List[RoundArgument],
    sequence: int,
    judge_type: str = "flow",
    prior_exchanges: Optional[List[CrossfireExchange]] = None,
) -> CrossfireExchange:
    """Generate one AI-opponent crossfire question.

    Parameters
    ----------
    round_id:   The round being simulated.
    phase:      Current phase (e.g. GRAND_CROSSFIRE).
    questioner_side:
                Which side is asking.
    live_args:  All arguments on the flow.
    sequence:   Exchange sequence number (0-based).
    judge_type: "flow", "lay", "tab", etc.
    prior_exchanges:
                All prior CrossfireExchanges in this crossfire (used for
                argument rotation and dedup).
    """
    prior_exchanges = prior_exchanges or []
    asked_questions = [ex.question for ex in prior_exchanges if ex.question]

    now = datetime.utcnow().isoformat()
    target = _find_target_argument(live_args, questioner_side, prior_exchanges)

    if target:
        question_type = _pick_question_type(target, sequence, prior_exchanges)
        question = (
            _generate_question_llm(
                target, questioner_side, judge_type, phase,
                question_type=question_type,
                asked_questions=asked_questions,
            )
            or _fallback_question(target, question_type)
        )
        # Dedup: if question is too similar to a prior one, use fallback
        norm_new = _normalize_question(question)
        for aq in asked_questions:
            if _normalize_question(aq) == norm_new:
                question = _fallback_question(target, question_type)
                break
        target_label = target.label
    else:
        question = "Can you clarify your position on the resolution and explain your key impact?"
        target_label = "general"
        question_type = "clarification"

    return CrossfireExchange(
        id=str(uuid.uuid4()),
        round_id=round_id,
        phase=phase,
        sequence=sequence,
        questioner_side=questioner_side,
        question=question,
        target_argument=target_label,
        exchange_type=CrossfireExchangeType.QUESTION,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Public: generate_followup_question
# ---------------------------------------------------------------------------

def generate_followup_question(
    prior_exchange: CrossfireExchange,
    questioner_side: RoundSide,
    live_args: List[RoundArgument],
    judge_type: str = "flow",
) -> CrossfireExchange:
    """Generate a targeted follow-up after an evasive answer.

    The follow-up:
    - References the original question and what was NOT answered
    - Does NOT introduce new evidence
    - Is more pointed than the original

    Parameters
    ----------
    prior_exchange:
        The exchange whose answer was detected as evasive (must have .answer set).
    questioner_side:
        Which side is asking the follow-up.
    live_args:
        All live arguments (used for context only).
    judge_type:
        Judge preference style.
    """
    now = datetime.utcnow().isoformat()
    original_q = prior_exchange.question or "your previous question"
    evasive_answer = prior_exchange.answer or ""
    target_label = prior_exchange.target_argument or "general"

    followup_question: Optional[str] = None

    # LLM path
    if settings.openai_api_key:
        try:
            client = openai.OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a {questioner_side.value} debater pressing your opponent "
                            "after an evasive answer in PF crossfire. "
                            "Generate ONE pointed follow-up question that:\n"
                            "1. References the original unanswered question\n"
                            "2. Identifies specifically what was not answered\n"
                            "3. Does NOT introduce new evidence or arguments\n"
                            "4. Is under 35 words\n"
                            "Return JSON: {\"question\": \"...\"}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Original question: {original_q}\n"
                            f"Evasive answer received: {evasive_answer[:300]}\n"
                            f"Target argument: {target_label}\n"
                            f"Judge type: {judge_type}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.5,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            followup_question = data.get("question")
        except Exception as exc:
            logger.warning("LLM follow-up question failed: %s", exc)

    # Deterministic fallback
    if not followup_question:
        followup_question = (
            f"You didn't directly answer my question: '{original_q[:80]}'. "
            f"I'll ask again — can you specifically address that point?"
        )

    return CrossfireExchange(
        id=str(uuid.uuid4()),
        round_id=prior_exchange.round_id,
        phase=prior_exchange.phase,
        sequence=prior_exchange.sequence + 1,
        questioner_side=questioner_side,
        question=followup_question,
        target_argument=target_label,
        exchange_type=CrossfireExchangeType.QUESTION,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Public: generate_ai_answer
# ---------------------------------------------------------------------------

def generate_ai_answer(
    question: str,
    opponent_side: RoundSide,
    live_args: List[RoundArgument],
    prior_exchanges: List[CrossfireExchange],
    config: RoundSimulationConfig,
) -> str:
    """Generate an AI opponent answer to a student crossfire question.

    Rules:
    - Consistent with prior opponent speeches (uses live_args as ground truth)
    - No new evidence introduced
    - Max 2 sentences for crossfire economy
    - Uses concession_detector internally to note if a partial concession is forced

    Parameters
    ----------
    question:
        The student's question text.
    opponent_side:
        The AI opponent's side.
    live_args:
        All current flow arguments (opponent's args supply the factual basis).
    prior_exchanges:
        Prior exchanges in this crossfire for consistency.
    config:
        Round simulation config (judge_type, resolution, etc.).

    Returns
    -------
    A short string answer (1–2 sentences).
    """
    # Build a summary of the opponent's own arguments for grounding
    opp_args = [a for a in live_args if a.side == opponent_side]
    arg_summary = "\n".join(
        f"- [{a.label}] {a.claim} (status: {a.status.value})"
        for a in opp_args[:6]
    )
    prior_summary = "\n".join(
        f"Q: {ex.question}\nA: {ex.answer or '[no answer]'}"
        for ex in prior_exchanges[-3:]
        if ex.answer
    )

    # LLM path
    if settings.openai_api_key:
        try:
            client = openai.OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are the {opponent_side.value} side AI debater in a PF crossfire. "
                            "Answer the student's question in exactly 1-2 sentences. Rules:\n"
                            "- Stay consistent with your prior speeches\n"
                            "- Do NOT introduce new evidence\n"
                            "- Do NOT make new arguments\n"
                            "- Be direct but strategic\n"
                            "- If the question exposes a real weakness, you may partially concede "
                            "  (e.g. 'That's fair to a degree, but...')"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Resolution: {config.resolution}\n"
                            f"Your ({opponent_side.value}) arguments:\n{arg_summary}\n\n"
                            + (f"Prior crossfire exchanges:\n{prior_summary}\n\n" if prior_summary else "")
                            + f"Student's question: {question}"
                        ),
                    },
                ],
                max_tokens=120,
                temperature=0.55,
            )
            answer_text = (resp.choices[0].message.content or "").strip()
            if answer_text:
                # Run concession detection so the caller can observe if a
                # forced partial concession occurred — log it at DEBUG level.
                findings = detect_concessions(
                    answer_text=answer_text,
                    speaker_side=opponent_side.value,
                    target_argument_label=None,
                    prior_positions=[a.claim for a in opp_args],
                )
                for f in findings:
                    if f.type in ("explicit", "partial"):
                        logger.debug(
                            "AI answer forced a %s concession: %s",
                            f.type,
                            f.transcript_span[:80],
                        )
                return answer_text
        except Exception as exc:
            logger.warning("LLM AI answer failed: %s", exc)

    # Deterministic fallback: pick the most relevant opponent argument
    if opp_args:
        arg = opp_args[0]
        return (
            f"Our {arg.label} argument stands — {arg.claim[:100]}. "
            "The evidence clearly supports our position, and your question doesn't undermine the warrant."
        )
    return (
        "Our position on the resolution remains the same. "
        "We'd need to see evidence that directly contradicts our warrant before conceding that point."
    )


# ---------------------------------------------------------------------------
# Existing: process_crossfire_response (upgraded with concession_detector)
# ---------------------------------------------------------------------------

def process_crossfire_response(
    exchange: CrossfireExchange,
    student_answer: str,
    live_args: List[RoundArgument],
    prior_positions: Optional[List[str]] = None,
) -> CrossfireExchange:
    """Analyze a student crossfire answer.

    Detects concessions, contradictions, and evasions using concession_detector.
    Does NOT introduce new evidence.

    Parameters
    ----------
    exchange:       The exchange being answered.
    student_answer: The student's raw answer text.
    live_args:      Current flow arguments (for context).
    prior_positions:
                    Prior claims/positions by the student's side (for contradiction
                    detection). Falls back to claim list from live_args if None.
    """
    questioner_side = exchange.questioner_side
    # The student is on the side being questioned, i.e. the opponent of the questioner
    student_side = (
        RoundSide.CON if questioner_side == RoundSide.PRO else RoundSide.PRO
    )

    if prior_positions is None:
        prior_positions = [
            a.claim for a in live_args if a.side == student_side and a.claim
        ]

    # Run concession detection
    findings = detect_concessions(
        answer_text=student_answer,
        speaker_side=student_side.value,
        target_argument_label=exchange.target_argument,
        prior_positions=prior_positions,
    )

    # Run contradiction detection
    contradiction_finding = detect_contradiction(
        new_statement=student_answer,
        prior_statements=prior_positions,
        argument_label=exchange.target_argument,
    )

    # --- Classify the exchange based on findings ---
    concession_text: Optional[str] = None
    contradiction_text: Optional[str] = None
    evasion_detected = False

    high_confidence_types = {"explicit", "partial"}
    evasion_types = {"evasion"}

    for f in findings:
        if f.type in high_confidence_types and not f.requires_confirmation:
            concession_text = f.transcript_span[:200]
            break
        if f.type in evasion_types:
            evasion_detected = True

    if contradiction_finding:
        contradiction_text = contradiction_finding.transcript_span[:200]

    # Determine strategic significance
    if concession_text:
        sig = "high"
    elif contradiction_text or evasion_detected:
        sig = "medium"
    else:
        sig = "low"

    # Determine exchange type
    if concession_text:
        exchange_type = CrossfireExchangeType.CONCESSION
    elif contradiction_text:
        exchange_type = CrossfireExchangeType.CONTRADICTION
    elif evasion_detected:
        exchange_type = CrossfireExchangeType.EVASION
    else:
        exchange_type = CrossfireExchangeType.ANSWER

    updated = exchange.model_copy(
        update={
            "answer": student_answer,
            "evasion_detected": evasion_detected,
            "concession_extracted": concession_text,
            "contradiction": contradiction_text,
            "exchange_type": exchange_type,
            "strategic_significance": sig,
        }
    )
    return updated


# ---------------------------------------------------------------------------
# DB helpers (unchanged from Pass 16)
# ---------------------------------------------------------------------------

def save_crossfire_exchange(exchange: CrossfireExchange) -> None:
    """Persist a crossfire exchange record."""
    supabase = get_supabase()
    try:
        supabase.table("round_crossfire_exchanges").insert(exchange.model_dump()).execute()
    except Exception as exc:
        logger.error("Failed to save crossfire exchange: %s", exc)


def load_crossfire_exchanges(
    round_id: str,
    phase: Optional[RoundPhaseType] = None,
) -> List[CrossfireExchange]:
    """Load crossfire exchanges for a round, optionally filtered by phase."""
    supabase = get_supabase()
    try:
        q = supabase.table("round_crossfire_exchanges").select("*").eq("round_id", round_id)
        if phase:
            q = q.eq("phase", phase.value)
        resp = q.order("sequence").execute()
        return [CrossfireExchange.model_validate(r) for r in (resp.data or [])]
    except Exception as exc:
        logger.warning("Failed to load crossfire exchanges: %s", exc)
        return []
