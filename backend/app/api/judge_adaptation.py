"""Pass 15 — Judge Adaptation API.

All endpoints under /judge-adaptation prefix.
Ownership enforced at application level.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.judge_adaptation import (
    AdaptationNoteRow,
    CoachAssignWorkoutRequest,
    CustomJudgeProfileCreate,
    JudgeAdaptationRequest,
    JudgeAdaptationResult,
    JudgeComparisonRequest,
    JudgeComparisonResult,
    JudgeProfile,
    JudgeReadinessReport,
    JudgeWorkoutCreate,
    JudgeWorkoutRow,
    SaveAdaptationNoteRequest,
)
from app.services.adaptation_risk_checker import check_all_risks
from app.services.judge_adaptation_service import generate_adaptation
from app.services.judge_comparison import compare_profiles
from app.services.judge_profiles import get_all_builtin_profiles, get_builtin_profile
from app.services.judge_readiness_scorer import score_judge_readiness
from app.services.judge_workout_generator import generate_judge_workout
from app.services.product_events import track_product_event
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/judge-adaptation", tags=["judge_adaptation"])


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


# ── Judge profiles ────────────────────────────────────────────────────────────

@router.get("/profiles", response_model=list[JudgeProfile])
def list_profiles(user_id: Optional[str] = Query(None)) -> list[JudgeProfile]:
    """List all available judge profiles (built-in + user's custom profiles)."""
    profiles = get_all_builtin_profiles()
    if user_id:
        try:
            sb = get_supabase()
            result = sb.table("judge_profiles").select("*").eq("user_id", user_id).execute()
            for row in result.data or []:
                from app.models.judge_adaptation import JudgePreferences
                prefs = {k: row.get(k, 3) for k in [
                    "jargon_tolerance", "speed_tolerance", "evidence_detail_preference",
                    "line_by_line_expectation", "extension_strictness", "weighing_expectation",
                    "narrative_preference", "real_world_explanation", "technical_rule_sensitivity",
                    "intervention_tolerance", "organization_preference",
                    "source_qualification_importance", "persuasion_vs_flow_emphasis",
                ]}
                profiles.append(JudgeProfile(
                    id=row["id"],
                    judge_type=row.get("base_type", "custom"),
                    name=row["name"],
                    description=row.get("description") or "",
                    preferences=JudgePreferences(**prefs),
                    is_builtin=False,
                    user_id=row["user_id"],
                    team_id=row.get("team_id"),
                ))
        except Exception as exc:
            logger.warning("list_profiles: custom load failed: %s", exc)
    return profiles


@router.get("/profiles/{judge_type}", response_model=JudgeProfile)
def get_profile(judge_type: str) -> JudgeProfile:
    profile = get_builtin_profile(judge_type)  # type: ignore[arg-type]
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{judge_type}' not found")
    return profile


@router.post("/profiles/custom", response_model=JudgeProfile)
def create_custom_profile(body: CustomJudgeProfileCreate) -> JudgeProfile:
    sb = get_supabase()
    prefs = body.preferences.model_dump()
    payload = {
        "user_id": body.user_id,
        "name": body.name,
        "base_type": body.base_type,
        "description": body.description,
        **prefs,
    }
    if body.team_id:
        payload["team_id"] = body.team_id
    try:
        result = sb.table("judge_profiles").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Insert failed")
        row = result.data[0]
        return JudgeProfile(
            id=row["id"],
            judge_type=body.base_type,
            name=body.name,
            description=body.description or "",
            preferences=body.preferences,
            is_builtin=False,
            user_id=body.user_id,
        )
    except Exception as exc:
        raise _http(exc) from exc


# ── Adaptation ────────────────────────────────────────────────────────────────

@router.post("/adapt", response_model=JudgeAdaptationResult)
def adapt(body: JudgeAdaptationRequest) -> JudgeAdaptationResult:
    """Generate an adaptation plan for a source + judge type."""
    try:
        result = generate_adaptation(
            user_id=body.user_id,
            judge_type=body.judge_type,
            source_type=body.source_type,
            source_id=body.source_id,
            workspace_id=body.workspace_id,
        )
    except Exception as exc:
        logger.error("adapt: %s", exc)
        raise HTTPException(status_code=500, detail=f"Adaptation failed: {exc}") from exc

    # Persist adaptation result
    try:
        sb = get_supabase()
        payload = {
            "user_id": body.user_id,
            "judge_type": body.judge_type,
            "source_type": body.source_type,
            f"source_{body.source_type}_id": body.source_id,
            "result_json": result.model_dump(),
            "risk_count": len(result.risks),
            "change_count": len(result.changes),
            "workspace_id": body.workspace_id,
        }
        insert = sb.table("judge_adaptations").insert(payload).execute()
        if insert.data:
            result.id = insert.data[0].get("id")
    except Exception as exc:
        logger.warning("adapt: persist failed: %s", exc)

    track_product_event(
        body.user_id,
        "adaptations_generated",
        metadata={
            "judge_type": body.judge_type,
            "source_type": body.source_type,
            "risk_count": len(result.risks),
        },
    )

    track_product_event(
        body.user_id,
        "judge_profiles_selected",
        metadata={"judge_type": body.judge_type},
    )

    return result


# ── Comparison ────────────────────────────────────────────────────────────────

@router.post("/compare", response_model=JudgeComparisonResult)
def compare(body: JudgeComparisonRequest) -> JudgeComparisonResult:
    """Compare the same material across two or more judge profiles."""
    if len(body.judge_types) < 2:
        raise HTTPException(status_code=400, detail="At least 2 judge types required")

    try:
        result = compare_profiles(
            body.judge_types,
            body.source_type,
            body.source_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    track_product_event(
        body.user_id,
        "comparisons_run",
        metadata={
            "judge_types": list(body.judge_types),
            "source_type": body.source_type,
        },
    )

    return result


# ── Risks ─────────────────────────────────────────────────────────────────────

@router.post("/risks")
def detect_risks(
    user_id: str = Query(...),
    judge_type: str = Query(...),
    card_id: Optional[str] = Query(None),
) -> dict:
    """Run risk checks for a card + judge type combination."""
    card: dict = {}
    if card_id:
        try:
            sb = get_supabase()
            result = sb.table("evidence_cards").select("*").eq("id", card_id).limit(1).execute()
            if result.data and result.data[0].get("user_id") == user_id:
                card = result.data[0]
        except Exception as exc:
            logger.warning("detect_risks: card load: %s", exc)

    risks = check_all_risks(
        judge_type,  # type: ignore[arg-type]
        card_id=card_id,
        tag=card.get("tag"),
        original_body=card.get("body_text"),
        support_verdict=card.get("support_verdict"),
    )

    track_product_event(
        user_id,
        "adaptation_risks_found",
        metadata={"count": len(risks), "judge_type": judge_type},
    )

    return {
        "risks": [r.model_dump() for r in risks],
        "critical_count": sum(1 for r in risks if r.level == "critical"),
        "total": len(risks),
    }


# ── Workouts ──────────────────────────────────────────────────────────────────

@router.post("/workouts/generate", response_model=JudgeWorkoutCreate)
def generate_workout(
    user_id: str = Query(...),
    judge_type: str = Query(...),
    source_type: str = Query(...),
    source_id: str = Query(...),
    workspace_id: Optional[str] = Query(None),
) -> JudgeWorkoutCreate:
    """Generate a judge-specific workout from source material."""
    card: dict = {}
    if source_type == "evidence":
        try:
            sb = get_supabase()
            r = sb.table("evidence_cards").select("*").eq("id", source_id).limit(1).execute()
            if r.data and r.data[0].get("user_id") == user_id:
                card = r.data[0]
        except Exception as exc:
            logger.warning("generate_workout: card load: %s", exc)

    workout = generate_judge_workout(
        judge_type,  # type: ignore[arg-type]
        source_type,
        card=card,
        user_id=user_id,
        workspace_id=workspace_id,
    )

    if not workout:
        raise HTTPException(status_code=400, detail="Could not generate workout for this source type")

    track_product_event(
        user_id,
        "judge_workouts_generated",
        metadata={"judge_type": judge_type, "workout_type": workout.workout_type},
    )

    return workout


@router.post("/workouts/assign")
def assign_workout(body: CoachAssignWorkoutRequest) -> dict:
    """Coach assigns a judge workout to a student."""
    now = _now()
    payload = {
        "assigned_by": body.assigned_by,
        "assigned_to": body.assigned_to,
        "team_id": body.team_id,
        "workout_type": body.workout_type,
        "judge_type": body.judge_type,
        "title": body.title,
        "prompt": body.prompt,
        "instructions": body.instructions,
        "success_criteria": body.success_criteria,
        "time_limit_seconds": body.time_limit_seconds,
        "source_card_id": body.source_card_id,
        "source_card_tag": body.source_card_tag,
        "source_card_body_snapshot": body.source_card_body_snapshot,
        "status": "assigned",
    }
    try:
        sb = get_supabase()
        result = sb.table("judge_workout_assignments").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Assignment insert failed")
        track_product_event(
            body.assigned_by,
            "coach_assignments_created",
            metadata={"assigned_to": body.assigned_to, "judge_type": body.judge_type},
        )
        return {"id": result.data[0]["id"], "status": "assigned"}
    except Exception as exc:
        raise _http(exc) from exc


@router.patch("/workouts/{assignment_id}/complete")
def complete_workout(
    assignment_id: str,
    user_id: str = Query(...),
    student_notes: Optional[str] = Query(None),
) -> dict:
    """Student marks a judge workout complete."""
    sb = get_supabase()
    existing = sb.table("judge_workout_assignments").select("assigned_to,judge_type").eq("id", assignment_id).limit(1).execute()
    if not existing.data or existing.data[0]["assigned_to"] != user_id:
        raise HTTPException(status_code=404, detail="Assignment not found or not authorized")
    update_payload: dict = {"status": "completed", "completed_at": _now()}
    if student_notes:
        update_payload["student_notes"] = student_notes
    sb.table("judge_workout_assignments").update(update_payload).eq("id", assignment_id).execute()
    track_product_event(
        user_id,
        "judge_workouts_completed",
        metadata={"assignment_id": assignment_id},
    )
    return {"ok": True, "note": "Judge readiness updated. Evidence freshness and quality are unchanged."}


@router.get("/workouts", response_model=list[dict])
def list_workouts(user_id: str = Query(...)) -> list[dict]:
    """List all judge workout assignments for a student."""
    sb = get_supabase()
    result = (
        sb.table("judge_workout_assignments")
        .select("*")
        .eq("assigned_to", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/notes", response_model=AdaptationNoteRow)
def save_note(body: SaveAdaptationNoteRequest) -> AdaptationNoteRow:
    """Save a note on an adaptation."""
    # Verify adaptation ownership
    sb = get_supabase()
    existing = sb.table("judge_adaptations").select("user_id").eq("id", body.adaptation_id).limit(1).execute()
    if not existing.data or existing.data[0]["user_id"] != body.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        result = sb.table("judge_adaptation_notes").insert({
            "adaptation_id": body.adaptation_id,
            "user_id": body.user_id,
            "judge_type": body.judge_type,
            "note_text": body.note_text,
        }).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Note insert failed")
        row = result.data[0]
        track_product_event(body.user_id, "adaptation_notes_saved")
        return AdaptationNoteRow(
            id=row["id"],
            adaptation_id=row["adaptation_id"],
            user_id=row["user_id"],
            judge_type=row["judge_type"],
            note_text=row["note_text"],
            created_at=row.get("created_at", _now()),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/notes/{adaptation_id}", response_model=list[AdaptationNoteRow])
def list_notes(adaptation_id: str, user_id: str = Query(...)) -> list[AdaptationNoteRow]:
    sb = get_supabase()
    existing = sb.table("judge_adaptations").select("user_id").eq("id", adaptation_id).limit(1).execute()
    if not existing.data or existing.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = sb.table("judge_adaptation_notes").select("*").eq("adaptation_id", adaptation_id).execute()
    return [
        AdaptationNoteRow(
            id=r["id"],
            adaptation_id=r["adaptation_id"],
            user_id=r["user_id"],
            judge_type=r["judge_type"],
            note_text=r["note_text"],
            created_at=r.get("created_at", _now()),
        )
        for r in result.data or []
    ]


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history")
def get_history(
    user_id: str = Query(...),
    source_id: Optional[str] = Query(None),
    judge_type: Optional[str] = Query(None),
    limit: int = Query(10, le=50),
) -> list[dict]:
    """Retrieve adaptation history for a user."""
    sb = get_supabase()
    query = sb.table("judge_adaptations").select(
        "id,judge_type,source_type,risk_count,change_count,created_at"
    ).eq("user_id", user_id)
    if judge_type:
        query = query.eq("judge_type", judge_type)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


# ── Judge readiness score ─────────────────────────────────────────────────────

@router.post("/readiness-score", response_model=JudgeReadinessReport)
def compute_readiness_score(body: JudgeAdaptationRequest) -> JudgeReadinessReport:
    """
    Compute judge readiness score for source + judge type.
    Separate dimension from evidence quality and freshness.
    """
    risks = check_all_risks(
        body.judge_type,
    )
    result = score_judge_readiness(
        body.judge_type,
        body.source_type,
        body.source_id,
        body.user_id,
        risks=risks,
    )
    return result
