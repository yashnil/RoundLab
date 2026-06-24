"""Pass 16 / 16.5 — Full-Round PF Simulation API.

All endpoints derive user identity from the verified Supabase JWT (via
get_current_user_id dependency). user_id is never trusted from request bodies
or query strings. RLS on Supabase tables provides defense-in-depth.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.round_simulation import (
    AddAnnotationRequest,
    AdvancePhaseRequest,
    AutomatedFindingRating,
    CoachAnnotation,
    CreateAdaptationReviewRequest,
    CreateRoundRequest,
    CrossfireSubmitRequest,
    GenerateDecisionRequest,
    GenerateDrillsRequest,
    GenerateOpponentSpeechRequest,
    LoadPreparationRequest,
    RateFindingRequest,
    RejudgeRequest,
    ReplayPhase,
    RoundAdaptationReview,
    RoundArgument,
    RoundDecision,
    RoundDrill,
    RoundEvidenceUse,
    RoundHistoryItem,
    RoundPhaseType,
    RoundQualityReport,
    RoundSimulation,
    RoundSimulationConfig,
    RoundSide,
    RoundSpeech,
    RoundStateResponse,
    RoundStatus,
    StudentCrossfireQuestionRequest,
    SubmitStudentSpeechRequest,
    TurningPoint,
)
from app.services.auth import get_current_user_id
from app.services.coach_round_review import (
    add_coach_annotation,
    assign_drill_from_round,
    export_round_report,
    list_coach_annotations,
    rate_automated_finding,
)
from app.services.round_replay import build_replay_timeline, get_replay_timeline, identify_turning_points
from app.services.crossfire_simulator import (
    generate_crossfire_question,
    load_crossfire_exchanges,
    process_crossfire_response,
    save_crossfire_exchange,
)
from app.services.evidence_use_tracker import (
    create_evidence_use_record,
    generate_evidence_report,
    load_evidence_uses,
    save_evidence_use,
)
from app.services.opponent_speech_generator import generate_opponent_speech
from app.services.opponent_strategy import build_opponent_round_plan
from app.services.product_events import track_product_event
from app.services.round_decision_engine import rejudge_round, run_decision_engine
from app.services.round_drill_generator import (
    generate_post_round_drills,
    load_round_drills,
    save_round_drills,
)
from app.services.round_flow_tracker import (
    load_round_arguments,
    process_speech_for_flow,
)
from app.services.round_prep_connector import (
    get_pre_round_readiness_warnings,
    record_post_round_gaps,
)
from app.services.round_state_machine import (
    CROSSFIRE_PHASES,
    PHASE_LABELS,
    get_time_limit,
    next_phase,
    student_speaks_in_phase,
    validate_phase_transition,
)
from app.services.speech_legality_checker import check_speech_legality
from app.services.supabase_client import get_supabase
from app.services.transcription import transcribe_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/round-simulations", tags=["round_simulations"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verify_owner(round_id: str, user_id: str, supabase: Any) -> Dict[str, Any]:
    """Fetch round and verify user owns it. Raises 404/403 on failure."""
    try:
        resp = supabase.table("round_simulations").select("*").eq("id", round_id).single().execute()
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Round not found.") from exc
    row = resp.data
    if not row:
        raise HTTPException(status_code=404, detail="Round not found.")
    if row.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return row


def _load_simulation(row: Dict[str, Any]) -> RoundSimulation:
    config_data = row.get("config_json") or {}
    return RoundSimulation(
        id=row["id"],
        user_id=row["user_id"],
        team_id=row.get("team_id"),
        config=RoundSimulationConfig.model_validate(config_data),
        status=RoundStatus(row.get("status", "setup")),
        current_phase=RoundPhaseType(row.get("current_phase", "first_constructive")),
        phase_history=row.get("phase_history") or [],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        is_practice_mode=row.get("is_practice_mode", False),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _coaching_hint(phase: RoundPhaseType, judge_type: str) -> Optional[str]:
    hints = {
        RoundPhaseType.FIRST_CONSTRUCTIVE: "Lead with your strongest argument. Clear tag → cite → warrant → impact.",
        RoundPhaseType.SECOND_CONSTRUCTIVE: "Echo your case. Foreshadow responses to likely opposition attacks.",
        RoundPhaseType.FIRST_CROSSFIRE: "Expose unresolved warrant gaps. Ask one focused question at a time.",
        RoundPhaseType.FIRST_REBUTTAL: "Go line-by-line. Address every opponent argument before extending yours.",
        RoundPhaseType.SECOND_REBUTTAL: "Collapse to your strongest responses. Start to extend your best offense.",
        RoundPhaseType.GRAND_CROSSFIRE: "Target live arguments. Expose missing extensions.",
        RoundPhaseType.FIRST_SUMMARY: "Extend your top voter. Include weighing. No new arguments.",
        RoundPhaseType.SECOND_SUMMARY: "Mirror your summary voter. Answer the opponent's summary voter directly.",
        RoundPhaseType.FINAL_CROSSFIRE: "Force concessions on the key voter. Do not introduce new evidence.",
        RoundPhaseType.FIRST_FINAL_FOCUS: "Name one voting issue. Explain why you extended it. Give comparative weighing.",
        RoundPhaseType.SECOND_FINAL_FOCUS: "The ballot is won by the clearest comparison. Who wins and why.",
    }
    return hints.get(phase)


def _check_duplicate_speech(round_id: str, phase: RoundPhaseType, idempotency_key: Optional[str], supabase: Any) -> Optional[Dict[str, Any]]:
    """Return existing speech row if already submitted (idempotency guard)."""
    if idempotency_key:
        try:
            resp = (
                supabase.table("round_speeches")
                .select("*")
                .eq("round_id", round_id)
                .eq("idempotency_key", idempotency_key)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]
        except Exception:
            pass
    return None


# ── Round lifecycle ───────────────────────────────────────────────────────────


@router.post("", response_model=RoundSimulation, status_code=201)
def create_round(
    req: CreateRoundRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundSimulation:
    """Create a new round simulation in SETUP state."""
    supabase = get_supabase()
    row_id = str(uuid.uuid4())
    now = _now()
    row = {
        "id": row_id,
        "user_id": user_id,
        "team_id": req.team_id,
        "config_json": req.config.model_dump(),
        "status": RoundStatus.SETUP.value,
        "current_phase": RoundPhaseType.FIRST_CONSTRUCTIVE.value,
        "phase_history": [],
        "is_practice_mode": bool(req.config.practice_mode_overrides),
        "created_at": now,
        "updated_at": now,
        "phase_started_at": now,
    }
    try:
        supabase.table("round_simulations").insert(row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create round: {exc}") from exc
    track_product_event(user_id, "simulations_created", {"format": req.config.format.value})
    return _load_simulation(row)


@router.get("/{round_id}", response_model=RoundStateResponse)
def get_round_state(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
    include_coaching_hint: bool = Query(True),
) -> RoundStateResponse:
    """Fetch current round state, live flow, and speeches."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)
    phase = sim.current_phase
    time_limit = get_time_limit(phase, sim.config)
    student_speaks = student_speaks_in_phase(phase, sim.config)

    try:
        speeches_resp = (
            supabase.table("round_speeches")
            .select("*")
            .eq("round_id", round_id)
            .order("created_at")
            .execute()
        )
        speeches = [_load_speech(r) for r in (speeches_resp.data or [])]
    except Exception:
        speeches = []

    flow_args = load_round_arguments(round_id)

    active_crossfire = None
    if phase in CROSSFIRE_PHASES:
        active_crossfire = load_crossfire_exchanges(round_id, phase)

    decision: Optional[RoundDecision] = None
    if sim.status == RoundStatus.COMPLETED:
        try:
            d_resp = (
                supabase.table("round_decisions")
                .select("*")
                .eq("round_id", round_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if d_resp.data:
                decision = RoundDecision.model_validate(d_resp.data[0])
        except Exception:
            pass

    hint: Optional[str] = None
    if include_coaching_hint and sim.config.coaching_hints_enabled:
        hint = _coaching_hint(phase, sim.config.judge_type)

    return RoundStateResponse(
        simulation=sim,
        current_phase=phase,
        phase_label=PHASE_LABELS.get(phase, phase.value),
        student_speaks_now=student_speaks,
        time_limit_seconds=time_limit,
        phase_started_at=row.get("phase_started_at"),
        speeches=speeches,
        flow_arguments=flow_args,
        active_crossfire=active_crossfire,
        decision=decision,
        coaching_hint=hint,
    )


@router.post("/{round_id}/start", response_model=RoundSimulation)
def start_round(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> RoundSimulation:
    """Transition round from SETUP to ACTIVE."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)
    if sim.status != RoundStatus.SETUP:
        raise HTTPException(status_code=400, detail="Round must be in SETUP to start.")
    now = _now()
    supabase.table("round_simulations").update({
        "status": RoundStatus.ACTIVE.value,
        "started_at": now,
        "updated_at": now,
        "phase_started_at": now,
    }).eq("id", round_id).execute()
    row.update({"status": RoundStatus.ACTIVE.value, "started_at": now, "updated_at": now, "phase_started_at": now})
    return _load_simulation(row)


@router.get("/{round_id}/prep-warnings")
def get_prep_warnings(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Get pre-round readiness warnings from Tournament Prep."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)
    warnings = get_pre_round_readiness_warnings(sim.config, user_id)
    return {"warnings": warnings, "count": len(warnings)}


@router.post("/{round_id}/load-preparation")
def load_preparation(
    round_id: str,
    req: LoadPreparationRequest,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Load approved preparation material into the round config."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)
    config = sim.config

    card_set = set(config.approved_card_ids) | set(req.card_ids)
    blockfile_set = set(config.approved_blockfile_ids) | set(req.blockfile_ids)
    frontline_set = set(config.approved_frontline_ids) | set(req.frontline_ids)
    if req.prep_workspace_id:
        config = config.model_copy(update={"prep_workspace_id": req.prep_workspace_id})
    config = config.model_copy(update={
        "approved_card_ids": list(card_set),
        "approved_blockfile_ids": list(blockfile_set),
        "approved_frontline_ids": list(frontline_set),
    })

    supabase.table("round_simulations").update({
        "config_json": config.model_dump(),
        "updated_at": _now(),
    }).eq("id", round_id).execute()

    plan = build_opponent_round_plan(round_id, config, user_id)
    supabase.table("opponent_round_plans").upsert(plan.model_dump()).execute()

    return {
        "approved_cards": len(card_set),
        "approved_blockfiles": len(blockfile_set),
        "approved_frontlines": len(frontline_set),
        "opponent_plan_id": plan.id,
    }


# ── Student speech submission ─────────────────────────────────────────────────


@router.post("/{round_id}/speeches/student", response_model=RoundSpeech)
def submit_student_speech(
    round_id: str,
    req: SubmitStudentSpeechRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundSpeech:
    """Submit a student speech (audio URL or transcript). Idempotent on key."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)

    # Idempotency: return existing speech if already submitted
    existing = _check_duplicate_speech(round_id, req.phase, req.idempotency_key, supabase)
    if existing:
        return _load_speech(existing)

    sim = _load_simulation(row)
    if sim.current_phase != req.phase:
        raise HTTPException(
            status_code=400,
            detail=f"Current phase is {sim.current_phase.value}, got {req.phase.value}.",
        )
    if not student_speaks_in_phase(req.phase, sim.config):
        raise HTTPException(
            status_code=400,
            detail=f"Student does not speak in phase {req.phase.value}.",
        )

    transcript = req.transcript_text or req.typed_outline or ""
    word_count = 0
    if req.audio_url and not transcript:
        try:
            transcript, word_count = transcribe_speech(req.audio_url)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    else:
        word_count = len(transcript.split())

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Speech is empty.")

    live_args = load_round_arguments(round_id)
    violations = check_speech_legality(
        phase=req.phase,
        transcript=transcript,
        speaker_side=sim.config.student_side,
        live_args=live_args,
    )

    speech_id = str(uuid.uuid4())
    now = _now()
    speech_row: Dict[str, Any] = {
        "id": speech_id,
        "round_id": round_id,
        "phase": req.phase.value,
        "speaker_side": sim.config.student_side.value,
        "is_ai": False,
        "transcript": transcript,
        "audio_url": req.audio_url,
        "legality_violations": [v.model_dump() for v in violations],
        "word_count": word_count,
        "is_immutable": True,
        "created_at": now,
        "evidence_card_ids": [],
        "argument_labels": [],
        "strategic_goal": "",
        "estimated_speaking_time": None,
        "idempotency_key": req.idempotency_key,
    }
    try:
        supabase.table("round_speeches").insert(speech_row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save speech: {exc}") from exc

    if transcript:
        process_speech_for_flow(
            round_id=round_id,
            phase=req.phase,
            speaker_side=sim.config.student_side,
            transcript=transcript,
        )

    track_product_event(user_id, "speeches_submitted", {"phase": req.phase.value})
    return _load_speech(speech_row)


# ── Opponent speech generation ────────────────────────────────────────────────


@router.post("/{round_id}/speeches/opponent", response_model=RoundSpeech)
def generate_opponent_speech_endpoint(
    round_id: str,
    req: GenerateOpponentSpeechRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundSpeech:
    """Generate a bounded AI opponent speech. Idempotent on key."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)

    # Idempotency: return existing opponent speech if already generated
    existing = _check_duplicate_speech(round_id, req.phase, req.idempotency_key, supabase)
    if existing and existing.get("is_ai"):
        return _load_speech(existing)

    sim = _load_simulation(row)
    if sim.current_phase != req.phase:
        raise HTTPException(
            status_code=400,
            detail=f"Current phase is {sim.current_phase.value}, got {req.phase.value}.",
        )
    if student_speaks_in_phase(req.phase, sim.config):
        raise HTTPException(
            status_code=400,
            detail=f"Student speaks in phase {req.phase.value}, not the opponent.",
        )

    try:
        plan_resp = (
            supabase.table("opponent_round_plans")
            .select("*")
            .eq("round_id", round_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not plan_resp.data:
            raise ValueError("No opponent plan. Call /load-preparation first.")
        from app.models.round_simulation import OpponentRoundPlan
        plan = OpponentRoundPlan.model_validate(plan_resp.data[0])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    live_args = load_round_arguments(round_id)
    time_limit = get_time_limit(req.phase, sim.config)
    prior_speeches = _get_prior_speeches_summary(round_id, supabase)

    result = generate_opponent_speech(
        plan=plan,
        phase=req.phase,
        live_args=live_args,
        time_limit=time_limit,
        config=sim.config,
        prior_speeches_summary=prior_speeches,
    )

    opponent_side = (
        RoundSide.CON if sim.config.student_side == RoundSide.PRO else RoundSide.PRO
    )

    violations = check_speech_legality(
        phase=req.phase,
        transcript=result.speech_text,
        speaker_side=opponent_side,
        live_args=live_args,
    )

    speech_id = str(uuid.uuid4())
    now = _now()
    card_ids = [r.card_id for r in result.evidence_references]
    speech_row: Dict[str, Any] = {
        "id": speech_id,
        "round_id": round_id,
        "phase": req.phase.value,
        "speaker_side": opponent_side.value,
        "is_ai": True,
        "transcript": result.speech_text,
        "audio_url": None,
        "argument_labels": result.argument_labels,
        "responses_made": result.responses_made,
        "arguments_extended": result.arguments_extended,
        "arguments_dropped": result.arguments_dropped,
        "evidence_card_ids": card_ids,
        "weighing_used": result.weighing_used,
        "strategic_goal": result.strategic_goal,
        "estimated_speaking_time": result.estimated_speaking_time,
        "legality_violations": [v.model_dump() for v in violations],
        "word_count": len(result.speech_text.split()),
        "is_immutable": True,
        "created_at": now,
        "idempotency_key": req.idempotency_key,
    }
    try:
        supabase.table("round_speeches").insert(speech_row).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save opponent speech: {exc}") from exc

    process_speech_for_flow(
        round_id=round_id,
        phase=req.phase,
        speaker_side=opponent_side,
        transcript=result.speech_text,
        is_ai=True,
        explicit_argument_labels=result.argument_labels,
        explicit_responses=result.responses_made,
        explicit_extensions=result.arguments_extended,
        explicit_drops=result.arguments_dropped,
    )

    for ref in result.evidence_references:
        card_data = {
            "id": ref.card_id, "tag": ref.tag, "cite": ref.cite,
            "body_text": ref.quoted_text or "",
            "intelligence_json": {
                "support_verdict": ref.support_verdict,
                "source_classification": ref.source_classification,
            },
        }
        use = create_evidence_use_record(
            round_id, speech_id, ref.card_id, opponent_side, req.phase,
            result.speech_text, card_data
        )
        save_evidence_use(use)

    track_product_event(user_id, "opponent_speeches_generated", {"phase": req.phase.value})
    return _load_speech(speech_row)


# ── Crossfire ─────────────────────────────────────────────────────────────────


@router.get("/{round_id}/crossfire/question")
def get_crossfire_question(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
    sequence: int = Query(1),
) -> Dict[str, Any]:
    """Generate the next AI crossfire question targeting a student argument."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    if sim.current_phase not in CROSSFIRE_PHASES:
        raise HTTPException(status_code=400, detail="Not in a crossfire phase.")

    opponent_side = RoundSide.CON if sim.config.student_side == RoundSide.PRO else RoundSide.PRO
    live_args = load_round_arguments(round_id)

    exchange = generate_crossfire_question(
        round_id=round_id,
        phase=sim.current_phase,
        questioner_side=opponent_side,
        live_args=live_args,
        sequence=sequence,
        judge_type=sim.config.judge_type,
    )
    save_crossfire_exchange(exchange)
    return exchange.model_dump()


@router.post("/{round_id}/crossfire/answer")
def submit_crossfire_answer(
    round_id: str,
    req: CrossfireSubmitRequest,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Submit a student answer to an AI crossfire question."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    if sim.current_phase not in CROSSFIRE_PHASES:
        raise HTTPException(status_code=400, detail="Not in a crossfire phase.")

    exchanges = load_crossfire_exchanges(round_id, sim.current_phase)
    unanswered = [e for e in exchanges if e.questioner_side != sim.config.student_side and not e.answer]
    if not unanswered:
        raise HTTPException(status_code=400, detail="No pending AI question.")

    exchange = unanswered[-1]
    student_answer = req.typed_response or ""
    live_args = load_round_arguments(round_id)
    updated = process_crossfire_response(exchange, student_answer, live_args)

    try:
        supabase.table("round_crossfire_exchanges").update(
            updated.model_dump()
        ).eq("id", updated.id).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save answer: {exc}") from exc

    track_product_event(user_id, "crossfire_questions_answered", {})
    return updated.model_dump()


@router.post("/{round_id}/crossfire/student-question")
def submit_student_crossfire_question(
    round_id: str,
    req: StudentCrossfireQuestionRequest,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Student asks a question; the AI opponent generates an answer."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    if sim.current_phase not in CROSSFIRE_PHASES:
        raise HTTPException(status_code=400, detail="Not in a crossfire phase.")

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    opponent_side = RoundSide.CON if sim.config.student_side == RoundSide.PRO else RoundSide.PRO
    live_args = load_round_arguments(round_id)
    prior_speeches = _get_prior_speeches_summary(round_id, supabase)

    ai_answer = _generate_ai_crossfire_answer(
        question=req.question,
        questioner_side=sim.config.student_side,
        opponent_side=opponent_side,
        live_args=live_args,
        prior_speeches_summary=prior_speeches,
        config=sim.config,
    )

    exchange_id = str(uuid.uuid4())
    now = _now()
    exchange_row: Dict[str, Any] = {
        "id": exchange_id,
        "round_id": round_id,
        "phase": sim.current_phase.value,
        "questioner_side": sim.config.student_side.value,
        "question": req.question,
        "answer": ai_answer,
        "target_argument_label": None,
        "concession": None,
        "contradiction": None,
        "evasion_detected": False,
        "sequence": 0,
        "created_at": now,
        "status": "completed",
    }
    try:
        supabase.table("round_crossfire_exchanges").insert(exchange_row).execute()
    except Exception as exc:
        logger.warning("Failed to save student crossfire exchange: %s", exc)

    track_product_event(user_id, "student_crossfire_questions_asked", {})
    return {"id": exchange_id, "question": req.question, "answer": ai_answer, "created_at": now}


# ── Phase advancement ─────────────────────────────────────────────────────────


@router.post("/{round_id}/advance-phase", response_model=RoundSimulation)
def advance_phase(
    round_id: str,
    req: AdvancePhaseRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundSimulation:
    """Advance to the next phase or a specific target phase."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    if sim.status not in (RoundStatus.ACTIVE, RoundStatus.PAUSED):
        raise HTTPException(status_code=400, detail="Round is not active.")

    target = req.target_phase or next_phase(sim.current_phase, sim.config.format)
    if not target:
        raise HTTPException(status_code=400, detail="Already at the final phase.")

    ok, error = validate_phase_transition(
        sim.current_phase, target, sim.config.format, req.practice_override
    )
    if not ok:
        raise HTTPException(status_code=400, detail=error)

    new_history = sim.phase_history + [sim.current_phase.value]
    new_status = sim.status
    completed_at: Optional[str] = None
    if target == RoundPhaseType.COMPLETED:
        new_status = RoundStatus.COMPLETED
        completed_at = _now()
        track_product_event(user_id, "simulations_completed", {"round_id": round_id})

    now = _now()
    supabase.table("round_simulations").update({
        "current_phase": target.value,
        "phase_history": new_history,
        "status": new_status.value,
        "completed_at": completed_at,
        "updated_at": now,
        "phase_started_at": now,
    }).eq("id", round_id).execute()
    row.update({
        "current_phase": target.value,
        "phase_history": new_history,
        "status": new_status.value,
        "completed_at": completed_at,
        "updated_at": now,
        "phase_started_at": now,
    })
    return _load_simulation(row)


@router.post("/{round_id}/pause", response_model=RoundSimulation)
def pause_round(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> RoundSimulation:
    """Pause an active round."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)
    if sim.status != RoundStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Round is not active.")
    now = _now()
    supabase.table("round_simulations").update({
        "status": RoundStatus.PAUSED.value,
        "updated_at": now,
    }).eq("id", round_id).execute()
    row.update({"status": RoundStatus.PAUSED.value, "updated_at": now})
    return _load_simulation(row)


@router.post("/{round_id}/resume", response_model=RoundSimulation)
def resume_round(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> RoundSimulation:
    """Resume a paused round."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)
    if sim.status != RoundStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Round is not paused.")
    now = _now()
    supabase.table("round_simulations").update({
        "status": RoundStatus.ACTIVE.value,
        "updated_at": now,
    }).eq("id", round_id).execute()
    row.update({"status": RoundStatus.ACTIVE.value, "updated_at": now})
    return _load_simulation(row)


# ── Decision ──────────────────────────────────────────────────────────────────


@router.post("/{round_id}/decision", response_model=RoundDecision)
def generate_decision(
    round_id: str,
    req: GenerateDecisionRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundDecision:
    """Generate a round decision after completion."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    if sim.status != RoundStatus.COMPLETED and sim.current_phase != RoundPhaseType.JUDGE_DELIBERATION:
        raise HTTPException(status_code=400, detail="Round must be completed before generating a decision.")

    judge_type = req.judge_type or sim.config.judge_type
    all_args = load_round_arguments(round_id)
    evidence_uses = load_evidence_uses(round_id)

    try:
        speeches_resp = supabase.table("round_speeches").select("legality_violations").eq("round_id", round_id).execute()
        all_violations: List[Dict[str, Any]] = []
        for s in speeches_resp.data or []:
            all_violations.extend(s.get("legality_violations") or [])
    except Exception:
        all_violations = []

    speeches_summary = _get_prior_speeches_summary(round_id, supabase)
    decision = run_decision_engine(
        round_id=round_id,
        judge_type=judge_type,
        all_args=all_args,
        evidence_uses=evidence_uses,
        legality_violations=all_violations,
        speeches_summary=speeches_summary,
    )

    try:
        supabase.table("round_decisions").insert(decision.model_dump()).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save decision: {exc}") from exc

    record_post_round_gaps(
        round_id=round_id,
        user_id=user_id,
        workspace_id=sim.config.prep_workspace_id,
        all_args=all_args,
        evidence_uses=evidence_uses,
        student_side=sim.config.student_side,
        decision=decision,
    )

    return decision


@router.post("/{round_id}/rejudge", response_model=RoundDecision)
def rejudge(
    round_id: str,
    req: RejudgeRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundDecision:
    """Re-judge the round under a different judge profile without altering history."""
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    if sim.status != RoundStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Round must be completed to rejudge.")

    all_args = load_round_arguments(round_id)
    evidence_uses = load_evidence_uses(round_id)
    try:
        speeches_resp = supabase.table("round_speeches").select("legality_violations").eq("round_id", round_id).execute()
        all_violations: List[Dict[str, Any]] = []
        for s in speeches_resp.data or []:
            all_violations.extend(s.get("legality_violations") or [])
    except Exception:
        all_violations = []

    speeches_summary = _get_prior_speeches_summary(round_id, supabase)
    decision = rejudge_round(
        round_id=round_id,
        new_judge_type=req.judge_type,
        all_args=all_args,
        evidence_uses=evidence_uses,
        legality_violations=all_violations,
        speeches_summary=speeches_summary,
    )

    try:
        supabase.table("round_decisions").insert(decision.model_dump()).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save rejudge decision: {exc}") from exc

    track_product_event(user_id, "rounds_rejudged", {"new_judge_type": req.judge_type})
    return decision


# ── Adaptation reviews ────────────────────────────────────────────────────────


@router.post("/{round_id}/adaptation-reviews", response_model=RoundAdaptationReview, status_code=201)
def create_adaptation_review(
    round_id: str,
    req: CreateAdaptationReviewRequest,
    user_id: str = Depends(get_current_user_id),
) -> RoundAdaptationReview:
    """Create an adaptation review comparing judge profiles for this round."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    all_args = load_round_arguments(round_id)
    evidence_uses = load_evidence_uses(round_id)

    successes, failures = _analyze_judge_adaptation(
        judge_type=req.judge_type,
        all_args=all_args,
        evidence_uses=evidence_uses,
        student_side=sim.config.student_side,
    )

    now = _now()
    review_id = str(uuid.uuid4())
    review_row: Dict[str, Any] = {
        "id": review_id,
        "round_id": round_id,
        "judge_type": req.judge_type,
        "decision_id": req.decision_id,
        "adaptation_successes": successes,
        "adaptation_failures": failures,
        "alternate_judge_type": req.alternate_judge_type,
        "created_at": now,
    }
    try:
        supabase.table("round_adaptation_reviews").insert(review_row).execute()
    except Exception as exc:
        logger.warning("Failed to save adaptation review: %s", exc)

    return RoundAdaptationReview(
        id=review_id,
        round_id=round_id,
        judge_type=req.judge_type,
        adaptation_successes=successes,
        adaptation_failures=failures,
        alternate_judge_type=req.alternate_judge_type,
        created_at=now,
    )


@router.get("/{round_id}/adaptation-reviews", response_model=List[RoundAdaptationReview])
def list_adaptation_reviews(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> List[RoundAdaptationReview]:
    """List all adaptation reviews for a round."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)
    try:
        resp = (
            supabase.table("round_adaptation_reviews")
            .select("*")
            .eq("round_id", round_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [RoundAdaptationReview.model_validate(r) for r in (resp.data or [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Drills and flow ───────────────────────────────────────────────────────────


@router.post("/{round_id}/drills", response_model=List[RoundDrill])
def generate_drills_endpoint(
    round_id: str,
    req: GenerateDrillsRequest,
    user_id: str = Depends(get_current_user_id),
) -> List[RoundDrill]:
    """Generate post-round drills from round failures."""
    if req.round_id != round_id:
        raise HTTPException(status_code=400, detail="round_id mismatch.")
    supabase = get_supabase()
    row = _verify_owner(round_id, user_id, supabase)
    sim = _load_simulation(row)

    all_args = load_round_arguments(round_id)
    evidence_uses = load_evidence_uses(round_id)

    decision: Optional[RoundDecision] = None
    try:
        d_resp = supabase.table("round_decisions").select("*").eq("round_id", round_id).order("created_at", desc=True).limit(1).execute()
        if d_resp.data:
            decision = RoundDecision.model_validate(d_resp.data[0])
    except Exception:
        pass

    drills = generate_post_round_drills(
        round_id=round_id,
        student_side=sim.config.student_side,
        all_args=all_args,
        evidence_uses=evidence_uses,
        decision=decision,
    )
    save_round_drills(drills)

    track_product_event(user_id, "post_round_drills_generated", {"count": len(drills)})
    return drills


@router.get("/{round_id}/drills", response_model=List[RoundDrill])
def get_round_drills(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> List[RoundDrill]:
    """Retrieve generated drills for a round."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)
    return load_round_drills(round_id)


# ── Coach review ──────────────────────────────────────────────────────────────


@router.post("/{round_id}/annotations")
def create_annotation(
    round_id: str,
    req: AddAnnotationRequest,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Add a coach annotation to a round.
    Coach must own the round or be a team member — ownership verified by _verify_owner.
    Coach feedback never alters historical records.
    """
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)

    try:
        annotation = add_coach_annotation(
            round_id=round_id,
            coach_id=user_id,
            annotation_type=req.annotation_type,
            content=req.content,
            target_id=req.target_id,
            target_type=req.target_type,
            is_correction=req.is_correction,
            finding_id=req.finding_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save annotation: {exc}") from exc

    track_product_event(user_id, "coach_annotation_added", {"annotation_type": req.annotation_type})
    return {
        "id": annotation.id,
        "round_id": annotation.round_id,
        "coach_id": annotation.coach_id,
        "annotation_type": annotation.annotation_type,
        "target_id": annotation.target_id,
        "target_type": annotation.target_type,
        "content": annotation.content,
        "is_correction": annotation.is_correction,
        "finding_id": annotation.finding_id,
        "created_at": annotation.created_at,
    }


@router.get("/{round_id}/annotations")
def list_annotations(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
    coach_id: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """List coach annotations for a round."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)

    try:
        annotations = list_coach_annotations(round_id, coach_id=coach_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [
        {
            "id": a.id,
            "round_id": a.round_id,
            "coach_id": a.coach_id,
            "annotation_type": a.annotation_type,
            "target_id": a.target_id,
            "target_type": a.target_type,
            "content": a.content,
            "is_correction": a.is_correction,
            "finding_id": a.finding_id,
            "created_at": a.created_at,
        }
        for a in annotations
    ]


@router.post("/{round_id}/findings/{finding_id}/rate")
def rate_finding(
    round_id: str,
    finding_id: str,
    req: RateFindingRequest,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Rate an automated finding (correct / incorrect / useful / not_useful)."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)

    try:
        rating = rate_automated_finding(
            round_id=round_id,
            finding_id=finding_id,
            rater_id=user_id,
            rating=req.rating,
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save rating: {exc}") from exc

    track_product_event(user_id, "finding_rated", {"rating": req.rating})
    return {
        "id": rating.id,
        "round_id": rating.round_id,
        "finding_id": rating.finding_id,
        "rater_id": rating.rater_id,
        "rating": rating.rating,
        "note": rating.note,
        "created_at": rating.created_at,
    }


@router.get("/{round_id}/report")
def get_round_report(
    round_id: str,
    include_private_notes: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Export a round report suitable for display or sharing."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)

    try:
        report = export_round_report(round_id, include_private_notes=include_private_notes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {exc}") from exc

    return report


# ── Replay ────────────────────────────────────────────────────────────────────


@router.get("/{round_id}/replay")
def get_round_replay(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> List[Dict[str, Any]]:
    """Return the phase-by-phase replay timeline for a completed round."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)

    try:
        phases = get_replay_timeline(round_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build replay: {exc}") from exc

    return [
        {
            "phase": p.phase,
            "phase_label": p.phase_label,
            "speaker_label": p.speaker_label,
            "transcript_preview": p.transcript_preview,
            "flow_events": p.flow_events,
            "arguments_changed": p.arguments_changed,
            "evidence_used": p.evidence_used,
            "legality_violations": p.legality_violations,
            "turning_points": p.turning_points,
        }
        for p in phases
    ]


@router.get("/{round_id}/turning-points")
def get_turning_points(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> List[Dict[str, Any]]:
    """Return the key turning points identified in this round."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)

    # Fetch all data needed for turning point analysis
    try:
        args_resp = supabase.table("round_arguments").select("*").eq("round_id", round_id).execute()
        all_args = [dict(a) for a in (args_resp.data or [])]

        speeches_resp = supabase.table("round_speeches").select("*").eq("round_id", round_id).execute()
        speeches = [dict(s) for s in (speeches_resp.data or [])]

        cx_resp = supabase.table("round_crossfire_exchanges").select("*").eq("round_id", round_id).execute()
        crossfire_exchanges = [dict(c) for c in (cx_resp.data or [])]

        eu_resp = supabase.table("round_evidence_uses").select("*").eq("round_id", round_id).execute()
        evidence_uses = [dict(e) for e in (eu_resp.data or [])]

        decision = None
        d_resp = (
            supabase.table("round_decisions")
            .select("*")
            .eq("round_id", round_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if d_resp.data:
            decision = dict(d_resp.data[0])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load round data: {exc}") from exc

    turning_points = identify_turning_points(
        all_args=all_args,
        speeches=speeches,
        crossfire_exchanges=crossfire_exchanges,
        evidence_uses=evidence_uses,
        decision=decision,
    )

    return [
        {
            "phase": tp.phase,
            "type": tp.type,
            "description": tp.description,
            "argument_label": tp.argument_label,
            "severity": tp.severity,
        }
        for tp in turning_points
    ]


@router.get("/{round_id}/flow", response_model=List[RoundArgument])
def get_round_flow(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> List[RoundArgument]:
    """Retrieve live round flow."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)
    return load_round_arguments(round_id)


@router.get("/{round_id}/evidence-report")
def get_evidence_report(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Retrieve evidence-use report for the round."""
    supabase = get_supabase()
    _verify_owner(round_id, user_id, supabase)
    uses = load_evidence_uses(round_id)
    return generate_evidence_report(uses)


# ── History ───────────────────────────────────────────────────────────────────


@router.get("", response_model=List[RoundHistoryItem])
def list_rounds(
    user_id: str = Depends(get_current_user_id),
) -> List[RoundHistoryItem]:
    """List the authenticated user's round simulations."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("round_simulations")
            .select("id,config_json,status,completed_at,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    items: List[RoundHistoryItem] = []
    for r in resp.data or []:
        cfg = r.get("config_json") or {}
        items.append(RoundHistoryItem(
            id=r["id"],
            resolution=cfg.get("resolution", ""),
            student_side=cfg.get("student_side", ""),
            judge_type=cfg.get("judge_type", ""),
            status=r.get("status", ""),
            created_at=r["created_at"],
            completed_at=r.get("completed_at"),
        ))
    return items


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_speech(row: Dict[str, Any]) -> RoundSpeech:
    return RoundSpeech(
        id=row["id"],
        round_id=row["round_id"],
        phase=RoundPhaseType(row["phase"]),
        speaker_side=RoundSide(row["speaker_side"]),
        is_ai=row.get("is_ai", False),
        transcript=row.get("transcript"),
        audio_url=row.get("audio_url"),
        argument_labels=row.get("argument_labels") or [],
        responses_made=row.get("responses_made") or [],
        arguments_extended=row.get("arguments_extended") or [],
        arguments_dropped=row.get("arguments_dropped") or [],
        evidence_card_ids=row.get("evidence_card_ids") or [],
        weighing_used=row.get("weighing_used"),
        strategic_goal=row.get("strategic_goal"),
        estimated_speaking_time=row.get("estimated_speaking_time"),
        legality_violations=row.get("legality_violations") or [],
        word_count=row.get("word_count"),
        is_immutable=row.get("is_immutable", False),
        created_at=row.get("created_at", _now()),
    )


def _get_prior_speeches_summary(round_id: str, supabase: Any) -> str:
    try:
        resp = (
            supabase.table("round_speeches")
            .select("phase,speaker_side,transcript,argument_labels")
            .eq("round_id", round_id)
            .order("created_at")
            .limit(10)
            .execute()
        )
        parts: List[str] = []
        for s in resp.data or []:
            labels = ", ".join(s.get("argument_labels") or []) or "?"
            preview = (s.get("transcript") or "")[:200]
            parts.append(f"[{s['phase']} / {s['speaker_side']}] Args: {labels}. Preview: {preview}")
        return "\n".join(parts)
    except Exception:
        return ""


def _generate_ai_crossfire_answer(
    question: str,
    questioner_side: RoundSide,
    opponent_side: RoundSide,
    live_args: List[RoundArgument],
    prior_speeches_summary: str,
    config: RoundSimulationConfig,
) -> str:
    """Generate a short AI opponent answer to a student question.

    No new evidence allowed. Only relies on approved material or analytics.
    Falls back to a deterministic template on failure.
    """
    try:
        from openai import OpenAI
        from app.config import settings
        if not settings.openai_api_key:
            raise RuntimeError("no key")
        client = OpenAI(api_key=settings.openai_api_key)
        opponent_label = f"{opponent_side.value.upper()} debater"
        args_summary = "; ".join(a.label for a in live_args if a.side == opponent_side) or "none"
        prompt = (
            f"You are the {opponent_label} in a Public Forum debate round. "
            f"Your live arguments: {args_summary}. "
            f"Prior round context (2 sentences max): {prior_speeches_summary[:300]}. "
            f"A student just asked you: '{question}'. "
            f"Answer directly in 1-3 sentences. "
            f"RULES: Do not introduce new evidence or cite any new sources. "
            f"Do not concede unless the question is logically airtight. "
            f"Answer as a {config.opponent_difficulty.value}-level debater."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4,
        )
        answer = resp.choices[0].message.content or ""
        if answer.strip():
            return answer.strip()
    except Exception:
        pass

    # Deterministic fallback
    topic = question.split()[:5]
    return (
        f"That's an interesting point about {' '.join(topic) if topic else 'your argument'}. "
        f"Based on our evidence and analysis, we maintain our position. "
        f"The {opponent_side.value} side's argument still stands as extended."
    )


def _analyze_judge_adaptation(
    judge_type: str,
    all_args: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    student_side: RoundSide,
) -> tuple[List[str], List[str]]:
    """Deterministically identify adaptation successes and failures for a judge profile."""
    from app.services.judge_profiles import get_judge_profile
    try:
        profile = get_judge_profile(judge_type)
    except Exception:
        return [], [f"Unknown judge type: {judge_type}"]

    successes: List[str] = []
    failures: List[str] = []

    # Evidence quality
    student_uses = [u for u in evidence_uses if u.speaker_side == student_side]
    cited = [u for u in student_uses if u.citation_given]
    if student_uses:
        cite_pct = len(cited) / len(student_uses)
        if cite_pct >= 0.8:
            successes.append("Consistent citation across evidence uses.")
        elif profile.get("evidence_detail_preference", 0.5) > 0.5:
            failures.append("Evidence citations were incomplete for this judge type.")

    # Weighing
    extended = [a for a in all_args if a.side == student_side and a.status in ("extended", "live")]
    dropped = [a for a in all_args if a.side == student_side and a.status == "dropped"]
    if dropped and profile.get("weighing_expectation", 0.5) > 0.6:
        failures.append(f"{len(dropped)} student argument(s) were dropped without weighing.")
    if extended:
        successes.append(f"{len(extended)} argument(s) survived and were extended.")

    return successes, failures


# ── Pass 18: Round deletion ────────────────────────────────────────────────────

@router.delete("/{round_id}")
async def delete_round(
    round_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Delete a round simulation and all associated data.

    Removes: arguments, speeches, crossfire exchanges, evidence uses,
    decisions, coach annotations, finding ratings, replay markers,
    quality report, strategic memory. The round row itself is deleted last.

    Irreversible. Student must own the round.
    """
    supabase = get_supabase()
    _verify_owner(round_id, user_id)

    cascade_tables = [
        "round_coach_annotations",
        "round_finding_ratings",
        "round_strategic_memory",
        "round_replay_markers",
        "round_quality_reports",
        "round_arguments",
        "round_speeches",
        "round_crossfire_exchanges",
        "round_evidence_uses",
        "round_decisions",
        "round_adaptation_reviews",
    ]

    errors: list[str] = []
    for table in cascade_tables:
        try:
            supabase.table(table).delete().eq("round_id", round_id).execute()
        except Exception as exc:
            errors.append(f"{table}: {type(exc).__name__}")

    try:
        supabase.table("round_simulations").delete().eq("id", round_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to delete round.") from exc

    logger.info("delete_round: %s | user=%s | errors=%s", round_id, user_id[:8], errors)
    return {"deleted": True, "round_id": round_id, "partial_errors": errors or None}
