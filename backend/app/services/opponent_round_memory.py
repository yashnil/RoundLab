"""Pass 17 — Opponent round memory.

A bounded, structured object that tracks what has happened in the round.
Used by opponent speech generation and crossfire to maintain consistency.

Design principles:
- Append-only history (never mutate past events)
- Deterministic reconstruction from round_flow_events + speeches
- No private chain-of-thought
- Only concise strategic facts and round events
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Dict, List, Optional

from app.models.round_simulation import (
    RoundFormat,
    RoundPhaseType,
    RoundSimulationConfig,
    RoundSide,
)
from app.services.round_state_machine import get_phase_order

logger = logging.getLogger(__name__)

# Maximum characters for to_prompt_context output
_MAX_PROMPT_CONTEXT_CHARS = 600


@dataclasses.dataclass(frozen=True)
class OpponentRoundMemory:
    """Immutable snapshot of all strategically relevant round facts.

    All mutation returns a new instance (immutable pattern).
    """

    round_id: str
    opponent_side: str  # RoundSide value

    # Commitments
    opponent_commitments: List[str] = dataclasses.field(default_factory=list)
    student_commitments: List[str] = dataclasses.field(default_factory=list)

    # Flow tracking
    concessions: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    # Each: {by_side, argument_label, text, confidence}
    contradictions: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    # Each: {by_side, argument_label, prior_text, new_text}

    # Argument status
    unanswered_arguments: List[str] = dataclasses.field(default_factory=list)
    abandoned_arguments: List[str] = dataclasses.field(default_factory=list)

    # Evidence tracking
    evidence_read: List[str] = dataclasses.field(default_factory=list)
    evidence_challenges: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    # Each: {card_id, challenge_text, answered: bool}

    # Strategic state
    strategic_priorities: List[str] = dataclasses.field(default_factory=list)
    planned_collapse: Optional[str] = None
    judge_risk_notes: List[str] = dataclasses.field(default_factory=list)
    remaining_phases: List[str] = dataclasses.field(default_factory=list)


# ── Builder ───────────────────────────────────────────────────────────────────


def build_memory_for_phase(
    round_id: str,
    opponent_side: RoundSide,
    all_args: List[Dict[str, Any]],
    evidence_uses: List[Dict[str, Any]],
    crossfire_exchanges: List[Dict[str, Any]],
    prior_speeches: List[Dict[str, Any]],
    config: RoundSimulationConfig,
) -> OpponentRoundMemory:
    """Build OpponentRoundMemory deterministically from live round data.

    Deterministically reconstructable on refresh — no hidden state.

    Args:
        round_id: The current round's ID.
        opponent_side: Which side the AI opponent is playing.
        all_args: List of RoundArgument dicts from the DB.
        evidence_uses: List of RoundEvidenceUse dicts from the DB.
        crossfire_exchanges: List of CrossfireExchange dicts from the DB.
        prior_speeches: List of RoundSpeech dicts (is_ai, transcript,
            argument_labels, responses_made, arguments_extended,
            arguments_dropped, evidence_card_ids, phase, speaker_side).
        config: The RoundSimulationConfig for this round.

    Returns:
        A fully constructed OpponentRoundMemory.
    """
    opponent_side_str = opponent_side.value if hasattr(opponent_side, "value") else str(opponent_side)
    student_side_str = (
        RoundSide.PRO.value if opponent_side_str == RoundSide.CON.value else RoundSide.CON.value
    )

    # ── Commitments from prior speeches ──────────────────────────────────────
    opponent_commitments: List[str] = []
    student_commitments: List[str] = []

    for speech in prior_speeches:
        labels = speech.get("argument_labels") or []
        side = speech.get("speaker_side") or ""
        if hasattr(side, "value"):
            side = side.value
        is_ai = speech.get("is_ai", False)

        # Collect labels for each side
        if is_ai or side == opponent_side_str:
            for label in labels:
                if label and label not in opponent_commitments:
                    opponent_commitments.append(label)
        elif not is_ai or side == student_side_str:
            for label in labels:
                if label and label not in student_commitments:
                    student_commitments.append(label)

    # ── Unanswered student arguments ─────────────────────────────────────────
    # Arguments on the student's side that the opponent hasn't addressed
    opponent_responses_made: List[str] = []
    for speech in prior_speeches:
        side = speech.get("speaker_side") or ""
        if hasattr(side, "value"):
            side = side.value
        is_ai = speech.get("is_ai", False)
        if is_ai or side == opponent_side_str:
            responses = speech.get("responses_made") or []
            for r in responses:
                if r and r not in opponent_responses_made:
                    opponent_responses_made.append(r)

    unanswered_arguments: List[str] = [
        label for label in student_commitments
        if label not in opponent_responses_made
    ]

    # ── Abandoned arguments (opponent dropped their own case) ─────────────────
    # An opponent argument is abandoned if it was in a constructive but not
    # extended in any rebuttal or summary speech.
    opp_introduced: List[str] = []
    opp_extended: List[str] = []

    for speech in prior_speeches:
        side = speech.get("speaker_side") or ""
        if hasattr(side, "value"):
            side = side.value
        is_ai = speech.get("is_ai", False)
        phase = speech.get("phase") or ""
        if hasattr(phase, "value"):
            phase = phase.value

        if not (is_ai or side == opponent_side_str):
            continue

        labels = speech.get("argument_labels") or []
        extended = speech.get("arguments_extended") or []

        # Constructive = introduction phase
        if "constructive" in phase:
            for label in labels:
                if label not in opp_introduced:
                    opp_introduced.append(label)

        # Rebuttal/summary = extension opportunity
        if "rebuttal" in phase or "summary" in phase:
            for label in extended:
                if label not in opp_extended:
                    opp_extended.append(label)

    # Only mark as abandoned if a rebuttal/summary has already occurred
    rebuttal_happened = any(
        ("rebuttal" in (s.get("phase") or "")) or ("summary" in (s.get("phase") or ""))
        for s in prior_speeches
        if s.get("is_ai") or (s.get("speaker_side") or "") == opponent_side_str
    )
    abandoned_arguments: List[str] = (
        [a for a in opp_introduced if a not in opp_extended]
        if rebuttal_happened
        else []
    )

    # ── Evidence read by opponent ─────────────────────────────────────────────
    evidence_read: List[str] = []
    for speech in prior_speeches:
        side = speech.get("speaker_side") or ""
        if hasattr(side, "value"):
            side = side.value
        is_ai = speech.get("is_ai", False)
        if is_ai or side == opponent_side_str:
            card_ids = speech.get("evidence_card_ids") or []
            for cid in card_ids:
                if cid and cid not in evidence_read:
                    evidence_read.append(cid)

    # ── Evidence challenges from crossfire ────────────────────────────────────
    evidence_challenges: List[Dict[str, Any]] = []
    challenge_answered_set: set[str] = set()

    for ex in crossfire_exchanges:
        ex_type = ex.get("exchange_type") or ""
        if hasattr(ex_type, "value"):
            ex_type = ex_type.value
        card_id = ex.get("evidence_challenge")  # card_id or challenge text stored here
        if ex_type == "evidence_challenge" and card_id:
            challenge_text = ex.get("question") or ""
            questioner = ex.get("questioner_side") or ""
            if hasattr(questioner, "value"):
                questioner = questioner.value
            answered = bool(ex.get("answer"))
            # Track latest answered state per card
            if answered:
                challenge_answered_set.add(card_id)
            existing = next((c for c in evidence_challenges if c["card_id"] == card_id), None)
            if existing is None:
                evidence_challenges.append({
                    "card_id": card_id,
                    "challenge_text": challenge_text,
                    "answered": answered,
                })
            else:
                existing["answered"] = answered or existing["answered"]

    # Sync answered state from set
    for ch in evidence_challenges:
        if ch["card_id"] in challenge_answered_set:
            ch["answered"] = True

    # ── Concessions and contradictions from crossfire ─────────────────────────
    concessions: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []

    for ex in crossfire_exchanges:
        ex_type = ex.get("exchange_type") or ""
        if hasattr(ex_type, "value"):
            ex_type = ex_type.value
        questioner = ex.get("questioner_side") or ""
        if hasattr(questioner, "value"):
            questioner = questioner.value

        if ex_type == "concession":
            concession_text = ex.get("concession_extracted") or ex.get("answer") or ""
            target = ex.get("target_argument") or ""
            # The answerer is the opposite of the questioner
            answerer = student_side_str if questioner == opponent_side_str else opponent_side_str
            concessions.append({
                "by_side": answerer,
                "argument_label": target,
                "text": concession_text,
                "confidence": "high" if ex.get("concession_extracted") else "medium",
            })

        if ex_type == "contradiction":
            contradiction_text = ex.get("contradiction") or ""
            target = ex.get("target_argument") or ""
            answerer = student_side_str if questioner == opponent_side_str else opponent_side_str
            contradictions.append({
                "by_side": answerer,
                "argument_label": target,
                "prior_text": contradiction_text,
                "new_text": ex.get("answer") or "",
            })

    # ── Strategic priorities (surviving opponent offense) ─────────────────────
    strategic_priorities: List[str] = []
    surviving_statuses = {"introduced", "extended", "live", "unresolved"}

    for arg in all_args:
        arg_side = arg.get("side") or ""
        if hasattr(arg_side, "value"):
            arg_side = arg_side.value
        status = arg.get("status") or ""
        if hasattr(status, "value"):
            status = status.value
        is_offense = arg.get("is_offense", True)

        if arg_side == opponent_side_str and is_offense and status in surviving_statuses:
            label = arg.get("label") or ""
            if label and label not in strategic_priorities:
                strategic_priorities.append(label)

    # ── Planned collapse: highest-scored surviving opponent argument ───────────
    planned_collapse: Optional[str] = None

    # Score each surviving argument by evidence support verdict
    best_score = -1.0
    for arg in all_args:
        arg_side = arg.get("side") or ""
        if hasattr(arg_side, "value"):
            arg_side = arg_side.value
        status = arg.get("status") or ""
        if hasattr(status, "value"):
            status = status.value
        is_offense = arg.get("is_offense", True)
        label = arg.get("label") or ""

        if arg_side != opponent_side_str or not is_offense or label not in strategic_priorities:
            continue

        # Score: prefer extended > introduced, and arguments with evidence
        score = 0.0
        if status == "extended":
            score += 2.0
        elif status == "live":
            score += 1.5
        elif status == "introduced":
            score += 1.0
        if arg.get("evidence_card_id"):
            score += 1.0
        if arg.get("weighing"):
            score += 0.5
        if score > best_score:
            best_score = score
            planned_collapse = label

    # ── Judge risk notes ──────────────────────────────────────────────────────
    judge_risk_notes: List[str] = []
    judge_type = config.judge_type or "flow"

    if judge_type == "lay":
        judge_risk_notes.append("Lay judge: avoid jargon, use plain language and clear impacts.")
    elif judge_type == "flow":
        judge_risk_notes.append("Flow judge: signpost clearly, extend every argument explicitly.")
    elif judge_type == "policy":
        judge_risk_notes.append("Policy judge: prioritize magnitude and systemic impacts.")
    elif judge_type == "parent":
        judge_risk_notes.append("Parent judge: use intuitive framing; avoid technical debate terms.")

    # ── Remaining phases ──────────────────────────────────────────────────────
    current_phase_raw = config.practice_mode_overrides  # not the right field
    # Derive remaining phases from last speech phase
    full_order = get_phase_order(config.format)
    phase_values = [p.value if hasattr(p, "value") else str(p) for p in full_order]

    # Find the latest phase seen in prior speeches
    last_phase_idx = -1
    for speech in prior_speeches:
        sp = speech.get("phase") or ""
        if hasattr(sp, "value"):
            sp = sp.value
        if sp in phase_values:
            idx = phase_values.index(sp)
            if idx > last_phase_idx:
                last_phase_idx = idx

    remaining_phases: List[str] = (
        phase_values[last_phase_idx + 1:]
        if last_phase_idx >= 0
        else phase_values
    )

    return OpponentRoundMemory(
        round_id=round_id,
        opponent_side=opponent_side_str,
        opponent_commitments=opponent_commitments,
        student_commitments=student_commitments,
        concessions=concessions,
        contradictions=contradictions,
        unanswered_arguments=unanswered_arguments,
        abandoned_arguments=abandoned_arguments,
        evidence_read=evidence_read,
        evidence_challenges=evidence_challenges,
        strategic_priorities=strategic_priorities,
        planned_collapse=planned_collapse,
        judge_risk_notes=judge_risk_notes,
        remaining_phases=remaining_phases,
    )


# ── Prompt serialization ──────────────────────────────────────────────────────


def to_prompt_context(memory: OpponentRoundMemory) -> str:
    """Convert memory to a compact prompt string (max 600 chars).

    Only includes strategically relevant facts.
    No private chain-of-thought is included.

    Returns:
        A string of at most _MAX_PROMPT_CONTEXT_CHARS characters.
    """
    parts: List[str] = ["ROUND MEMORY"]

    if memory.opponent_commitments:
        parts.append("Opponent case: " + ", ".join(memory.opponent_commitments[:4]))

    if memory.student_commitments:
        parts.append("Student said: " + ", ".join(memory.student_commitments[:4]))

    concessions_opp = [
        c for c in memory.concessions if c.get("by_side") != memory.opponent_side
    ]
    if concessions_opp:
        texts = [c.get("text", c.get("argument_label", "")) for c in concessions_opp[:2]]
        parts.append("Concessions: " + "; ".join(t for t in texts if t))

    if memory.strategic_priorities:
        parts.append("Priorities: " + ", ".join(memory.strategic_priorities[:3]))

    if memory.planned_collapse:
        parts.append(f"Collapse to: {memory.planned_collapse}")

    if memory.unanswered_arguments:
        parts.append("Unanswered: " + ", ".join(memory.unanswered_arguments[:3]))

    if memory.evidence_read:
        parts.append("Avoid re-reading cards: " + ", ".join(memory.evidence_read[:4]))

    if memory.judge_risk_notes:
        parts.append("Judge risk: " + memory.judge_risk_notes[0])

    result = "\n".join(parts)

    # Truncate to max length, preserving whole lines where possible
    if len(result) <= _MAX_PROMPT_CONTEXT_CHARS:
        return result

    truncated = result[: _MAX_PROMPT_CONTEXT_CHARS - 3]
    # Try to break on a newline boundary
    last_newline = truncated.rfind("\n")
    if last_newline > _MAX_PROMPT_CONTEXT_CHARS // 2:
        truncated = truncated[:last_newline]
    return truncated + "..."


# ── Immutable update helpers ──────────────────────────────────────────────────


def record_opponent_commitment(
    memory: OpponentRoundMemory,
    claim: str,
) -> OpponentRoundMemory:
    """Return a new memory with the opponent commitment appended.

    Idempotent: if claim is already present, returns memory unchanged.
    """
    if not claim or claim in memory.opponent_commitments:
        return memory
    return dataclasses.replace(
        memory,
        opponent_commitments=[*memory.opponent_commitments, claim],
    )


def record_student_commitment(
    memory: OpponentRoundMemory,
    claim: str,
) -> OpponentRoundMemory:
    """Return a new memory with the student commitment appended.

    Idempotent: if claim is already present, returns memory unchanged.
    """
    if not claim or claim in memory.student_commitments:
        return memory
    return dataclasses.replace(
        memory,
        student_commitments=[*memory.student_commitments, claim],
    )
