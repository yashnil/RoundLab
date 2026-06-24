"""Pass 16 — Round-wide flow tracker.

Maintains append-only flow events and deterministically updates argument statuses.
The LLM cannot freely overwrite flow history. Every status change is event-driven.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.models.round_simulation import (
    ArgumentFlowStatus,
    RoundArgument,
    RoundFlowEvent,
    RoundPhaseType,
    RoundSide,
)
from app.services.round_state_machine import LATE_PHASES_NO_NEW_ARGS
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# ── Status transition table ───────────────────────────────────────────────────
# Maps (event_type, current_status) → new_status
# Events: introduce | answer | extend | drop | turn | weigh | concede | indict | mitigate

_TRANSITIONS: Dict[Tuple[str, ArgumentFlowStatus], ArgumentFlowStatus] = {
    ("introduce", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.INTRODUCED,
    ("answer", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.ANSWERED,
    ("answer", ArgumentFlowStatus.EXTENDED): ArgumentFlowStatus.ANSWERED,
    ("answer", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.ANSWERED,
    ("extend", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.EXTENDED,
    ("extend", ArgumentFlowStatus.ANSWERED): ArgumentFlowStatus.LIVE,
    ("extend", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.LIVE,
    ("extend", ArgumentFlowStatus.UNRESOLVED): ArgumentFlowStatus.LIVE,
    ("drop", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.DROPPED,
    ("drop", ArgumentFlowStatus.ANSWERED): ArgumentFlowStatus.DROPPED,
    ("drop", ArgumentFlowStatus.EXTENDED): ArgumentFlowStatus.DROPPED,
    ("drop", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.DROPPED,
    ("drop", ArgumentFlowStatus.UNRESOLVED): ArgumentFlowStatus.DROPPED,
    ("turn", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.TURNED,
    ("turn", ArgumentFlowStatus.ANSWERED): ArgumentFlowStatus.TURNED,
    ("turn", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.TURNED,
    ("concede", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.CONCEDED,
    ("concede", ArgumentFlowStatus.EXTENDED): ArgumentFlowStatus.CONCEDED,
    ("concede", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.CONCEDED,
    ("concede", ArgumentFlowStatus.ANSWERED): ArgumentFlowStatus.CONCEDED,
    ("weigh", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.LIVE,
    ("weigh", ArgumentFlowStatus.EXTENDED): ArgumentFlowStatus.LIVE,
    ("indict", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.MITIGATED,
    ("indict", ArgumentFlowStatus.EXTENDED): ArgumentFlowStatus.MITIGATED,
    ("indict", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.MITIGATED,
    ("mitigate", ArgumentFlowStatus.INTRODUCED): ArgumentFlowStatus.MITIGATED,
    ("mitigate", ArgumentFlowStatus.EXTENDED): ArgumentFlowStatus.MITIGATED,
    ("mitigate", ArgumentFlowStatus.LIVE): ArgumentFlowStatus.MITIGATED,
    ("mitigate", ArgumentFlowStatus.ANSWERED): ArgumentFlowStatus.MITIGATED,
}


def apply_event(
    current_status: ArgumentFlowStatus,
    event_type: str,
) -> ArgumentFlowStatus:
    """Return the new status after applying an event."""
    return _TRANSITIONS.get((event_type, current_status), current_status)


# ── Extraction helpers ────────────────────────────────────────────────────────

def _extract_argument_labels(transcript: str) -> List[str]:
    """
    Heuristically extract debater argument labels from transcript text.
    Looks for patterns like 'AC1', 'NC2', 'contention 1', 'off case 1'.
    """
    patterns = [
        r'\b((?:AC|NC|OP|PRO|CON|off)\s*\d+)\b',
        r'\bcontention\s+(\d+)\b',
        r'\b(C\d+)\b',
    ]
    labels: List[str] = []
    for pat in patterns:
        found = re.findall(pat, transcript, re.IGNORECASE)
        labels.extend([f.strip().upper() for f in found])
    return list(dict.fromkeys(labels))  # dedupe, preserve order


def _extract_responses(transcript: str, known_labels: List[str]) -> List[str]:
    """Extract references to arguments being responded to."""
    responses: List[str] = []
    for label in known_labels:
        if re.search(rf'\b{re.escape(label)}\b', transcript, re.IGNORECASE):
            responses.append(label)
    return responses


def _extract_extensions(transcript: str, known_labels: List[str]) -> List[str]:
    """Detect extensions ('extend X', 'our X argument still stands', 'across the flow on X')."""
    extensions: List[str] = []
    extend_pats = [
        r'extend\s+(?:our\s+)?({label})',
        r'({label})\s+(?:still\s+stands?|goes?\s+(?:uncontested|unanswered)|is\s+extended|stands?\s+uncontested)',
        r'across\s+the\s+flow\s+on\s+({label})',
    ]
    for label in known_labels:
        for pat in extend_pats:
            if re.search(pat.replace("{label}", re.escape(label)), transcript, re.IGNORECASE):
                extensions.append(label)
                break
    return list(set(extensions))


def _detect_drops(
    transcript: str,
    live_args: List[RoundArgument],
    speaker_side: RoundSide,
    phase: RoundPhaseType,
) -> List[str]:
    """
    Detect arguments that should have been responded to but weren't.
    Only checks opponent arguments that are live/extended/introduced.
    """
    opponent_side = RoundSide.CON if speaker_side == RoundSide.PRO else RoundSide.PRO
    actionable_statuses = {
        ArgumentFlowStatus.INTRODUCED,
        ArgumentFlowStatus.EXTENDED,
        ArgumentFlowStatus.LIVE,
        ArgumentFlowStatus.ANSWERED,
    }
    drops: List[str] = []
    for arg in live_args:
        if arg.side != opponent_side:
            continue
        if arg.status not in actionable_statuses:
            continue
        # Check if the transcript mentions this argument
        mentioned = bool(re.search(rf'\b{re.escape(arg.label)}\b', transcript, re.IGNORECASE))
        if not mentioned and phase in (
            RoundPhaseType.FIRST_REBUTTAL,
            RoundPhaseType.SECOND_REBUTTAL,
            RoundPhaseType.FIRST_SUMMARY,
            RoundPhaseType.SECOND_SUMMARY,
        ):
            drops.append(arg.label)
    return drops


# ── Persistence ───────────────────────────────────────────────────────────────


def load_round_arguments(round_id: str) -> List[RoundArgument]:
    """Load all arguments for a round from the database."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("round_arguments")
            .select("*")
            .eq("round_id", round_id)
            .execute()
        )
        rows = resp.data or []
        return [RoundArgument.model_validate(r) for r in rows]
    except Exception as exc:
        logger.warning("Failed to load round arguments: %s", exc)
        return []


def append_flow_event(event: RoundFlowEvent) -> None:
    """Persist a flow event (append-only)."""
    supabase = get_supabase()
    try:
        supabase.table("round_flow_events").insert(event.model_dump()).execute()
    except Exception as exc:
        logger.error("Failed to append flow event: %s", exc)


def upsert_argument(arg: RoundArgument) -> None:
    """Insert or update an argument row."""
    supabase = get_supabase()
    try:
        supabase.table("round_arguments").upsert(arg.model_dump()).execute()
    except Exception as exc:
        logger.error("Failed to upsert argument: %s", exc)


# ── Core flow update ──────────────────────────────────────────────────────────


def process_speech_for_flow(
    round_id: str,
    phase: RoundPhaseType,
    speaker_side: RoundSide,
    transcript: str,
    is_ai: bool,
    explicit_argument_labels: Optional[List[str]] = None,
    explicit_responses: Optional[List[str]] = None,
    explicit_extensions: Optional[List[str]] = None,
    explicit_drops: Optional[List[str]] = None,
    evidence_card_ids: Optional[List[str]] = None,
) -> Tuple[List[RoundArgument], List[RoundFlowEvent]]:
    """
    Process a speech transcript and update the round flow.

    Returns (updated_arguments, new_events).
    Appends events to the database. Updates argument statuses.
    """
    now = datetime.utcnow().isoformat()
    live_args = load_round_arguments(round_id)
    events: List[RoundFlowEvent] = []
    updated: Dict[str, RoundArgument] = {a.id: a for a in live_args}

    # Determine labels from transcript or explicit list
    all_known_labels = [a.label for a in live_args]
    arg_labels = explicit_argument_labels or _extract_argument_labels(transcript)
    response_labels = explicit_responses or _extract_responses(transcript, all_known_labels)
    extension_labels = explicit_extensions or _extract_extensions(transcript, all_known_labels)
    drop_labels = explicit_drops or _detect_drops(transcript, live_args, speaker_side, phase)

    # Introduce new arguments (only legal in early phases)
    for label in arg_labels:
        if not any(a.label == label for a in live_args):
            legal, reason = _legal_to_introduce(phase, label)
            new_arg = RoundArgument(
                id=str(uuid.uuid4()),
                round_id=round_id,
                label=label,
                side=speaker_side,
                claim=f"[{label}] claim extracted from speech.",
                initial_phase=phase,
                status=(
                    ArgumentFlowStatus.NEW_IN_LATE_SPEECH
                    if not legal
                    else ArgumentFlowStatus.INTRODUCED
                ),
                last_updated_phase=phase.value,
            )
            upsert_argument(new_arg)
            updated[new_arg.id] = new_arg
            event = RoundFlowEvent(
                id=str(uuid.uuid4()),
                round_id=round_id,
                phase=phase,
                event_type="introduce",
                argument_id=new_arg.id,
                side=speaker_side,
                description=f"{label} introduced{' (late — may be illegal)' if not legal else ''}.",
                new_status=new_arg.status,
                created_at=now,
            )
            events.append(event)
            append_flow_event(event)

    # Apply events to existing arguments
    def _update_arg(arg_id: str, event_type: str, description: str, card_id: Optional[str] = None) -> None:
        if arg_id not in updated:
            return
        arg = updated[arg_id]
        new_status = apply_event(arg.status, event_type)
        arg.status = new_status
        arg.last_updated_phase = phase.value
        upsert_argument(arg)
        event = RoundFlowEvent(
            id=str(uuid.uuid4()),
            round_id=round_id,
            phase=phase,
            event_type=event_type,
            argument_id=arg_id,
            side=speaker_side,
            description=description,
            new_status=new_status,
            evidence_card_id=card_id,
            created_at=now,
        )
        events.append(event)
        append_flow_event(event)

    # Process responses
    for label in response_labels:
        target = next((a for a in live_args if a.label == label), None)
        if target and target.side != speaker_side:
            _update_arg(target.id, "answer", f"{label} answered by {speaker_side.value}.")

    # Process extensions
    for label in extension_labels:
        target = next((a for a in live_args if a.label == label), None)
        if target and target.side == speaker_side:
            _update_arg(target.id, "extend", f"{label} extended by {speaker_side.value}.")

    # Process drops
    for label in drop_labels:
        target = next((a for a in live_args if a.label == label), None)
        if target and target.side != speaker_side:
            _update_arg(target.id, "drop", f"{label} dropped (not answered by {speaker_side.value}).")

    return list(updated.values()), events


def _legal_to_introduce(phase: RoundPhaseType, label: str) -> Tuple[bool, Optional[str]]:
    """Return (legal, reason) for introducing a new argument in this phase."""
    from app.services.round_state_machine import is_new_argument_legal
    return is_new_argument_legal(phase)


def reconstruct_flow_status(events: List[RoundFlowEvent]) -> Dict[str, ArgumentFlowStatus]:
    """Replay event log to rebuild current argument statuses deterministically."""
    status_map: Dict[str, ArgumentFlowStatus] = {}
    for event in sorted(events, key=lambda e: e.created_at):
        status_map[event.argument_id] = event.new_status
    return status_map
