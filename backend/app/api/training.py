"""Training OS API — mastery tracking, training plans, curriculum, diagnostics."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.event_packs.public_forum import (
    CANONICAL_TO_LEGACY,
    EVENT_PACK,
    LEGACY_SKILL_MAP,
    NOVICE_PF_CURRICULUM,
    SKILL_REGISTRY,
    get_lesson,
    get_skill,
    resolve_legacy_skill,
)
from app.models.training import (
    AddMasteryEvidenceRequest,
    CoachCalibrationRequest,
    CoachOverrideRequest,
    CurriculumProgress,
    DiagnosticCompleteRequest,
    DiagnosticStartRequest,
    GeneratePlanRequest,
    MarkLessonRequest,
    MasteryProfile,
    MasteryScore,
    PracticeAgendaRequest,
    TrainingPlan,
)
from app.services.auth import get_current_user_id
from app.services.unified_priority import compute_next_action, sync_plan_with_mission_completion
from app.services.diagnostic_engine import (
    compute_initial_mastery_from_diagnostic,
    get_first_week_plan,
    identify_strengths_and_priorities,
    recommend_starting_track,
)
from app.services.mastery_engine import (
    aggregate_mastery,
    build_mastery_explanation,
    compute_team_skill_gaps,
    determine_mastery_state,
    normalize_score,
)
from app.services.supabase_client import get_supabase
from app.services.training_planner import (
    generate_plan,
    prioritize_skills,
    suggest_practice_agenda,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training"])


# ── Internal helpers ──────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _member_role(supabase, team_id: str, user_id: str) -> Optional[str]:
    """Return the role of user_id in team_id, or None if not a member."""
    try:
        rows = (
            supabase.table("team_members")
            .select("role")
            .eq("team_id", team_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        return rows[0]["role"] if rows else None
    except Exception:
        return None


def _require_coach(supabase, team_id: str, caller: str) -> None:
    role = _member_role(supabase, team_id, caller)
    if role != "coach":
        raise HTTPException(status_code=403, detail="Coach access required")


def _build_mastery_profile(user_id: str, supabase) -> dict[str, dict]:
    """Fetch mastery_scores rows and return as {skill_id: row_dict}."""
    try:
        rows = (
            supabase.table("mastery_scores")
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        return {r["skill_id"]: r for r in rows}
    except Exception:
        return {}


def _scores_to_profile(user_id: str, scores: dict[str, dict]) -> MasteryProfile:
    """Build a MasteryProfile response from the raw DB scores dict."""
    now_str = _now().isoformat()
    skills_out: dict[str, MasteryScore] = {}
    for skill_id in SKILL_REGISTRY:
        row = scores.get(skill_id, {})
        last_at = row.get("last_demonstrated_at")
        skills_out[skill_id] = MasteryScore(
            user_id=user_id,
            skill_id=skill_id,
            mastery_score=float(row.get("mastery_score", 0)),
            confidence=float(row.get("confidence", 0)),
            evidence_count=int(row.get("evidence_count", 0)),
            mastery_state=row.get("mastery_state", "not_started"),
            last_demonstrated_at=last_at.isoformat() if hasattr(last_at, "isoformat") else last_at,
            coach_override_score=row.get("coach_override_score"),
            coach_override_note=row.get("coach_override_note"),
            recurring_weakness=int(row.get("recurring_weakness", 0)),
        )
    return MasteryProfile(
        user_id=user_id,
        skills=skills_out,
        computed_at=now_str,
        event_pack="public_forum",
    )


# ── Public / no-auth endpoints ────────────────────────────────────────────────


@router.get("/event-pack")
async def get_event_pack() -> dict:
    """Return the full Public Forum event pack (skills, curriculum, tracks)."""
    return EVENT_PACK


@router.get("/skills")
async def list_skills() -> list[dict]:
    """Return all skills in the event pack."""
    return list(SKILL_REGISTRY.values())


@router.get("/curriculum")
async def list_curriculum() -> list[dict]:
    """Return the novice PF curriculum lessons."""
    return NOVICE_PF_CURRICULUM


@router.get("/curriculum/lesson/{lesson_id}")
async def get_curriculum_lesson(lesson_id: str) -> dict:
    """Return a single curriculum lesson by ID."""
    lesson = get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    return lesson


# ── Mastery endpoints ─────────────────────────────────────────────────────────


@router.get("/mastery", response_model=MasteryProfile)
async def get_mastery_profile(
    caller: str = Depends(get_current_user_id),
) -> MasteryProfile:
    """Fetch the authenticated user's full mastery profile."""
    supabase = get_supabase()
    scores = _build_mastery_profile(caller, supabase)
    return _scores_to_profile(caller, scores)


@router.post("/mastery/evidence")
async def add_mastery_evidence(
    req: AddMasteryEvidenceRequest,
    caller: str = Depends(get_current_user_id),
) -> MasteryScore:
    """
    Record a new evidence item for a skill and recompute the mastery score.

    Returns the updated MasteryScore for the affected skill.
    """
    supabase = get_supabase()
    now = _now()

    # Resolve skill_id (support legacy names)
    skill_id = resolve_legacy_skill(req.skill_id)
    if skill_id not in SKILL_REGISTRY:
        raise HTTPException(status_code=422, detail=f"Unknown skill: '{req.skill_id}'")

    normalized = normalize_score(req.raw_score, req.source_type, req.input_scale)

    # Insert evidence record
    try:
        supabase.table("mastery_evidence").insert({
            "user_id": caller,
            "skill_id": skill_id,
            "raw_score": req.raw_score,
            "normalized_score": normalized,
            "source_type": req.source_type,
            "source_id": req.source_id,
            "change_reason": req.change_reason,
            "recorded_at": now.isoformat(),
        }).execute()
    except Exception as exc:
        logger.error("mastery_evidence insert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to record evidence") from exc

    # Fetch all evidence for this user + skill
    try:
        evidence_rows = (
            supabase.table("mastery_evidence")
            .select("*")
            .eq("user_id", caller)
            .eq("skill_id", skill_id)
            .order("recorded_at", desc=False)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch evidence") from exc

    # Parse recorded_at strings to datetime
    evidence_items = []
    for row in evidence_rows:
        recorded_at = row.get("recorded_at")
        if isinstance(recorded_at, str):
            recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        evidence_items.append({
            "normalized_score": float(row["normalized_score"]),
            "source_type": row["source_type"],
            "recorded_at": recorded_at,
            "change_reason": row.get("change_reason"),
        })

    # Fetch old score for explanation
    old_row = _build_mastery_profile(caller, supabase).get(skill_id, {})
    old_score = float(old_row.get("mastery_score", 0))

    # Re-aggregate
    agg = aggregate_mastery(evidence_items, now)
    new_state = determine_mastery_state(
        mastery_score=agg["mastery_score"],
        confidence=agg["confidence"],
        evidence_count=agg["evidence_count"],
        last_demonstrated_at=agg["last_demonstrated_at"],
        now=now,
    )

    explanation = build_mastery_explanation(
        skill_id, old_score, agg["mastery_score"],
        [{"source_type": req.source_type, "change_reason": req.change_reason}],
    )

    # Upsert mastery_scores
    last_at = agg["last_demonstrated_at"]
    upsert_payload: dict[str, Any] = {
        "user_id": caller,
        "skill_id": skill_id,
        "mastery_score": agg["mastery_score"],
        "confidence": agg["confidence"],
        "evidence_count": agg["evidence_count"],
        "mastery_state": new_state,
        "last_demonstrated_at": last_at.isoformat() if last_at else None,
        "updated_at": now.isoformat(),
    }

    try:
        supabase.table("mastery_scores").upsert(upsert_payload, on_conflict="user_id,skill_id").execute()
    except Exception as exc:
        logger.error("mastery_scores upsert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update mastery score") from exc

    return MasteryScore(
        user_id=caller,
        skill_id=skill_id,
        mastery_score=agg["mastery_score"],
        confidence=agg["confidence"],
        evidence_count=agg["evidence_count"],
        mastery_state=new_state,
        last_demonstrated_at=last_at.isoformat() if last_at else None,
        explanation=explanation,
    )


@router.post("/mastery/coach-override")
async def coach_mastery_override(
    req: CoachOverrideRequest,
    target_user_id: str,
    caller: str = Depends(get_current_user_id),
) -> MasteryScore:
    """
    Coach sets an override score for a student's skill.

    Requires the caller to be a coach on a team that includes target_user_id.
    """
    supabase = get_supabase()
    now = _now()

    # Resolve skill
    skill_id = resolve_legacy_skill(req.skill_id)
    if skill_id not in SKILL_REGISTRY:
        raise HTTPException(status_code=422, detail=f"Unknown skill: '{req.skill_id}'")

    # Verify caller is a coach of a team that target_user_id belongs to
    try:
        shared_teams = (
            supabase.table("team_members")
            .select("team_id, role")
            .eq("user_id", caller)
            .eq("role", "coach")
            .execute()
            .data
            or []
        )
        coach_team_ids = {r["team_id"] for r in shared_teams}

        student_teams = (
            supabase.table("team_members")
            .select("team_id")
            .eq("user_id", target_user_id)
            .execute()
            .data
            or []
        )
        student_team_ids = {r["team_id"] for r in student_teams}

        if not coach_team_ids.intersection(student_team_ids):
            raise HTTPException(status_code=403, detail="You are not a coach of this student's team")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify coach authorization") from exc

    # Fetch existing row (to preserve evidence-based fields)
    existing = _build_mastery_profile(target_user_id, supabase).get(skill_id, {})
    evidence_count = int(existing.get("evidence_count", 0))
    existing_state = existing.get("mastery_state", "not_started")
    last_at = existing.get("last_demonstrated_at")

    # Upsert with override
    try:
        supabase.table("mastery_scores").upsert({
            "user_id": target_user_id,
            "skill_id": skill_id,
            "mastery_score": float(existing.get("mastery_score", 0)),
            "confidence": float(existing.get("confidence", 0)),
            "evidence_count": evidence_count,
            "mastery_state": existing_state,
            "last_demonstrated_at": last_at,
            "coach_override_score": req.override_score,
            "coach_override_note": req.note,
            "coach_overridden_by": caller,
            "updated_at": now.isoformat(),
        }, on_conflict="user_id,skill_id").execute()
    except Exception as exc:
        logger.error("coach override upsert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to apply override") from exc

    # Audit the override — does NOT create mastery_evidence (not a performance signal)
    if req.override_score is not None:
        try:
            from app.services.mastery_integration import emit_mastery_override
            emit_mastery_override(
                supabase=supabase,
                coach_id=caller,
                student_id=target_user_id,
                skill=skill_id,
                override_score=float(req.override_score),
                reason=req.note or f"Coach override",
                artifact_id=req.artifact_id if hasattr(req, "artifact_id") else None,
            )
        except Exception:
            pass

    return MasteryScore(
        user_id=target_user_id,
        skill_id=skill_id,
        mastery_score=float(existing.get("mastery_score", 0)),
        confidence=float(existing.get("confidence", 0)),
        evidence_count=evidence_count,
        mastery_state=existing_state,
        last_demonstrated_at=last_at.isoformat() if hasattr(last_at, "isoformat") else last_at,
        coach_override_score=req.override_score,
        coach_override_note=req.note,
    )


# ── Training plan endpoints ───────────────────────────────────────────────────


@router.get("/plans")
async def get_active_plan(
    caller: str = Depends(get_current_user_id),
) -> Optional[TrainingPlan]:
    """Return the active training plan for the authenticated user, or null."""
    supabase = get_supabase()
    try:
        rows = (
            supabase.table("training_plans")
            .select("*")
            .eq("user_id", caller)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch plan") from exc

    if not rows:
        return None

    row = rows[0]
    return TrainingPlan(
        id=row["id"],
        user_id=caller,
        plan_type=row["plan_type"],
        event_pack=row.get("event_pack", "public_forum"),
        current_week=row.get("current_week", 1),
        total_weeks=row.get("total_weeks", 1),
        weeks=row.get("weeks", []),
        status=row.get("status", "active"),
        tournament_date=str(row["tournament_date"]) if row.get("tournament_date") else None,
        created_at=str(row["created_at"]),
    )


@router.post("/plans/generate", response_model=TrainingPlan)
async def generate_training_plan(
    req: GeneratePlanRequest,
    caller: str = Depends(get_current_user_id),
) -> TrainingPlan:
    """Generate a new training plan based on the user's mastery profile."""
    supabase = get_supabase()
    now = _now()

    # Fetch mastery profile
    scores = _build_mastery_profile(caller, supabase)
    mastery_profile_dict: dict[str, dict] = {
        skill_id: {
            "mastery_score": float(row.get("mastery_score", 0)),
            "mastery_state": row.get("mastery_state", "not_started"),
        }
        for skill_id, row in scores.items()
    }

    # Parse tournament date
    tournament_date_obj: Optional[date] = None
    if req.tournament_date:
        try:
            tournament_date_obj = date.fromisoformat(req.tournament_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid tournament_date format; use YYYY-MM-DD")

    # Deactivate any existing active plans
    try:
        supabase.table("training_plans").update({"status": "abandoned"}).eq("user_id", caller).eq("status", "active").execute()
    except Exception:
        pass

    # Generate plan
    plan_data = generate_plan(
        mastery_profile=mastery_profile_dict,
        plan_type=req.plan_type,
        tournament_date=tournament_date_obj,
        coach_priority_skills=req.coach_priority_skills,
    )

    # Insert into DB
    insert_payload: dict[str, Any] = {
        "user_id": caller,
        "plan_type": req.plan_type,
        "event_pack": "public_forum",
        "current_week": 1,
        "total_weeks": plan_data["total_weeks"],
        "weeks": plan_data["weeks"],
        "status": "active",
        "tournament_date": req.tournament_date,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    try:
        result = supabase.table("training_plans").insert(insert_payload).execute()
        new_id = result.data[0]["id"] if result.data else "unknown"
    except Exception as exc:
        logger.error("training_plans insert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save training plan") from exc

    return TrainingPlan(
        id=new_id,
        user_id=caller,
        plan_type=req.plan_type,
        event_pack="public_forum",
        current_week=1,
        total_weeks=plan_data["total_weeks"],
        weeks=plan_data["weeks"],
        status="active",
        tournament_date=req.tournament_date,
        created_at=now.isoformat(),
    )


@router.put("/plans/{plan_id}/week")
async def advance_plan_week(
    plan_id: str,
    current_week: int,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """Update the current week of a training plan. User must own the plan."""
    supabase = get_supabase()
    now = _now()

    # Verify ownership
    try:
        rows = (
            supabase.table("training_plans")
            .select("id, user_id, total_weeks")
            .eq("id", plan_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch plan") from exc

    if not rows:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_row = rows[0]
    if plan_row["user_id"] != caller:
        raise HTTPException(status_code=403, detail="Access denied")

    total_weeks = plan_row.get("total_weeks", 1)
    if current_week < 1 or current_week > total_weeks:
        raise HTTPException(
            status_code=422,
            detail=f"current_week must be between 1 and {total_weeks}",
        )

    try:
        supabase.table("training_plans").update({
            "current_week": current_week,
            "updated_at": now.isoformat(),
        }).eq("id", plan_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update plan") from exc

    return {"plan_id": plan_id, "current_week": current_week}


# ── Curriculum progress endpoints ─────────────────────────────────────────────


@router.get("/progress", response_model=list[CurriculumProgress])
async def get_curriculum_progress(
    caller: str = Depends(get_current_user_id),
) -> list[CurriculumProgress]:
    """Return all curriculum progress records for the authenticated user."""
    supabase = get_supabase()
    try:
        rows = (
            supabase.table("curriculum_progress")
            .select("*")
            .eq("user_id", caller)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch curriculum progress") from exc

    return [
        CurriculumProgress(
            lesson_id=row["lesson_id"],
            status=row.get("status", "not_started"),
            score=row.get("score"),
            completed_at=str(row["completed_at"]) if row.get("completed_at") else None,
            coach_note=row.get("coach_note"),
        )
        for row in rows
    ]


@router.post("/progress/lesson")
async def mark_lesson(
    req: MarkLessonRequest,
    caller: str = Depends(get_current_user_id),
) -> CurriculumProgress:
    """Mark a curriculum lesson as in_progress, completed, or skipped."""
    supabase = get_supabase()
    now = _now()

    valid_statuses = ("not_started", "in_progress", "completed", "skipped")
    if req.status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid_statuses}")

    if get_lesson(req.lesson_id) is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{req.lesson_id}' not found")

    completed_at = now.isoformat() if req.status == "completed" else None

    try:
        supabase.table("curriculum_progress").upsert({
            "user_id": caller,
            "lesson_id": req.lesson_id,
            "event_pack": "public_forum",
            "status": req.status,
            "score": req.score,
            "completed_at": completed_at,
            "created_at": now.isoformat(),
        }, on_conflict="user_id,lesson_id").execute()
    except Exception as exc:
        logger.error("curriculum_progress upsert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update lesson progress") from exc

    return CurriculumProgress(
        lesson_id=req.lesson_id,
        status=req.status,
        score=req.score,
        completed_at=completed_at,
    )


# ── Coach calibration endpoint ────────────────────────────────────────────────


@router.post("/calibration/{team_id}")
async def set_coach_calibration(
    team_id: str,
    req: CoachCalibrationRequest,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """Set coach calibration settings for a team. Requires coach role."""
    supabase = get_supabase()
    now = _now()

    _require_coach(supabase, team_id, caller)

    valid_standards = ("novice", "jv", "varsity")
    valid_emphasis = ("lay", "flow", "technical", "mixed")
    if req.standard not in valid_standards:
        raise HTTPException(status_code=422, detail=f"standard must be one of {valid_standards}")
    if req.judge_emphasis not in valid_emphasis:
        raise HTTPException(status_code=422, detail=f"judge_emphasis must be one of {valid_emphasis}")

    try:
        supabase.table("coach_calibration").upsert({
            "team_id": team_id,
            "standard": req.standard,
            "judge_emphasis": req.judge_emphasis,
            "rubric_weights": req.rubric_weights,
            "preferences": req.preferences,
            "updated_at": now.isoformat(),
            "updated_by": caller,
        }, on_conflict="team_id").execute()
    except Exception as exc:
        logger.error("coach_calibration upsert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save calibration") from exc

    return {
        "team_id": team_id,
        "standard": req.standard,
        "judge_emphasis": req.judge_emphasis,
        "updated_at": now.isoformat(),
    }


# ── Diagnostic endpoints ──────────────────────────────────────────────────────


@router.get("/diagnostic")
async def get_diagnostic_status(
    caller: str = Depends(get_current_user_id),
) -> dict:
    """Return the most recent diagnostic status for the authenticated user."""
    supabase = get_supabase()
    try:
        rows = (
            supabase.table("diagnostic_results")
            .select("*")
            .eq("user_id", caller)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch diagnostic") from exc

    if not rows:
        return {"status": "not_started", "diagnostic_id": None}

    row = rows[0]
    return {
        "diagnostic_id": row["id"],
        "status": row["status"],
        "experience_level": row.get("experience_level"),
        "strengths": row.get("strengths", []),
        "priorities": row.get("priorities", []),
        "recommended_track": row.get("recommended_track"),
        "completed_at": str(row["completed_at"]) if row.get("completed_at") else None,
    }


@router.post("/diagnostic/start")
async def start_diagnostic(
    req: DiagnosticStartRequest,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """Begin a new diagnostic intake session."""
    supabase = get_supabase()
    now = _now()

    valid_levels = ("first_time", "novice", "jv", "varsity")
    if req.experience_level not in valid_levels:
        raise HTTPException(
            status_code=422,
            detail=f"experience_level must be one of {valid_levels}",
        )

    # Merge experience_level into intake_data
    intake_data = dict(req.intake_data)
    intake_data["experience_level"] = req.experience_level

    try:
        result = supabase.table("diagnostic_results").insert({
            "user_id": caller,
            "event_pack": "public_forum",
            "experience_level": req.experience_level,
            "intake_data": intake_data,
            "status": "in_progress",
            "created_at": now.isoformat(),
        }).execute()
        diagnostic_id = result.data[0]["id"]
    except Exception as exc:
        logger.error("diagnostic_results insert failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to start diagnostic") from exc

    return {
        "diagnostic_id": diagnostic_id,
        "status": "in_progress",
        "next_steps": [
            "Record a 2-minute practice speech for more accurate assessment",
            "Complete your self-rating for each skill area",
            "Call POST /training/diagnostic/complete when done",
        ],
    }


@router.post("/diagnostic/complete")
async def complete_diagnostic(
    req: DiagnosticCompleteRequest,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """
    Complete a diagnostic and seed initial mastery scores.

    Optionally merges speech analysis scores for a more accurate assessment.
    Also generates the user's first training plan.
    """
    supabase = get_supabase()
    now = _now()

    # Fetch the diagnostic record
    try:
        rows = (
            supabase.table("diagnostic_results")
            .select("*")
            .eq("id", req.diagnostic_id)
            .eq("user_id", caller)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch diagnostic") from exc

    if not rows:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    diag_row = rows[0]
    if diag_row["status"] == "completed":
        raise HTTPException(status_code=409, detail="Diagnostic already completed")

    # Build full intake_data including speech_scores
    intake_data: dict = dict(diag_row.get("intake_data") or {})
    if req.speech_scores:
        intake_data["speech_scores"] = req.speech_scores

    # Compute initial mastery
    initial_mastery = compute_initial_mastery_from_diagnostic(intake_data)
    strengths, priorities = identify_strengths_and_priorities(initial_mastery)
    track = recommend_starting_track(diag_row.get("experience_level", "novice"), priorities)

    # Upsert mastery_scores for each skill
    failed_upserts = 0
    for skill_id, m in initial_mastery.items():
        try:
            supabase.table("mastery_scores").upsert({
                "user_id": caller,
                "skill_id": skill_id,
                "mastery_score": m["mastery_score"],
                "confidence": m["confidence"],
                "evidence_count": 1,
                "mastery_state": m["mastery_state"],
                "updated_at": now.isoformat(),
                "created_at": now.isoformat(),
            }, on_conflict="user_id,skill_id").execute()
        except Exception:
            failed_upserts += 1

    if failed_upserts > 0:
        logger.warning("diagnostic complete: %d mastery upserts failed", failed_upserts)

    # Mark diagnostic as completed
    try:
        supabase.table("diagnostic_results").update({
            "status": "completed",
            "strengths": strengths,
            "priorities": priorities,
            "recommended_track": track,
            "completed_at": now.isoformat(),
        }).eq("id", req.diagnostic_id).execute()
    except Exception as exc:
        logger.error("diagnostic_results update failed | %s", exc)

    # Generate first training plan
    mastery_profile_dict = {
        skill_id: {
            "mastery_score": m["mastery_score"],
            "mastery_state": m["mastery_state"],
        }
        for skill_id, m in initial_mastery.items()
    }

    # Deactivate old plans
    try:
        supabase.table("training_plans").update({"status": "abandoned"}).eq("user_id", caller).eq("status", "active").execute()
    except Exception:
        pass

    plan_data = generate_plan(mastery_profile_dict, "4_week")
    first_plan_id = None
    try:
        plan_result = supabase.table("training_plans").insert({
            "user_id": caller,
            "plan_type": "4_week",
            "event_pack": "public_forum",
            "current_week": 1,
            "total_weeks": plan_data["total_weeks"],
            "weeks": plan_data["weeks"],
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).execute()
        first_plan_id = plan_result.data[0]["id"] if plan_result.data else None
    except Exception as exc:
        logger.error("initial plan insert failed | %s", exc)

    first_week_actions = get_first_week_plan(
        diag_row.get("experience_level", "novice"), priorities
    )

    return {
        "mastery_profile": {
            "user_id": caller,
            "skills": {
                sid: {
                    "skill_id": sid,
                    "mastery_score": m["mastery_score"],
                    "mastery_state": m["mastery_state"],
                    "confidence": m["confidence"],
                }
                for sid, m in initial_mastery.items()
            },
            "computed_at": now.isoformat(),
            "event_pack": "public_forum",
        },
        "strengths": strengths,
        "priorities": priorities,
        "recommended_track": track,
        "first_plan": {
            "id": first_plan_id,
            "plan_type": "4_week",
            "total_weeks": plan_data["total_weeks"],
            "summary": plan_data["summary"],
        },
        "first_week_actions": first_week_actions,
    }


# ── Practice agenda endpoint ──────────────────────────────────────────────────


@router.post("/practice-agenda")
async def get_practice_agenda(
    req: PracticeAgendaRequest,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """
    Generate a coach-facing practice agenda for a team session.

    Requires the caller to be a coach on the specified team.
    """
    supabase = get_supabase()

    _require_coach(supabase, req.team_id, caller)

    # Fetch all student IDs on the team
    try:
        members = (
            supabase.table("team_members")
            .select("user_id, role")
            .eq("team_id", req.team_id)
            .execute()
            .data
            or []
        )
        student_ids = [m["user_id"] for m in members if m.get("role") == "student"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch team members") from exc

    if not student_ids:
        return {"team_id": req.team_id, "agenda": [], "student_count": 0}

    # Fetch mastery scores for all students
    try:
        mastery_rows = (
            supabase.table("mastery_scores")
            .select("user_id, skill_id, mastery_score, mastery_state")
            .in_("user_id", student_ids)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch mastery data") from exc

    if not mastery_rows:
        return {
            "team_id": req.team_id,
            "agenda": [],
            "student_count": len(student_ids),
            "note": "No mastery data yet for this team. Run diagnostics first.",
        }

    # Compute team skill gaps
    gaps = compute_team_skill_gaps(mastery_rows)
    agenda = suggest_practice_agenda(gaps, req.duration_minutes)

    return {
        "team_id": req.team_id,
        "student_count": len(student_ids),
        "duration_minutes": req.duration_minutes,
        "agenda": agenda,
        "skill_gaps_summary": {
            sid: {
                "avg_score": data["avg_score"],
                "pct_proficient": data["pct_proficient"],
            }
            for sid, data in sorted(gaps.items(), key=lambda kv: kv[1]["avg_score"])[:5]
        },
    }


# ── Unified next action endpoint ──────────────────────────────────────────────


@router.get("/next-action")
async def get_next_action(
    caller: str = Depends(get_current_user_id),
) -> dict:
    """
    Return the single best next activity for the authenticated student.

    Runs the unified priority pipeline:
      mastery gaps → prerequisites → coach priorities → assignments
      → tournament urgency → recent performance → fallback

    Used by the student dashboard and training hub to show one primary CTA.
    """
    supabase = get_supabase()

    # Fetch mastery profile
    scores = _build_mastery_profile(caller, supabase)
    mastery_profile = {
        sid: {
            "mastery_score": float(row.get("mastery_score", 0)),
            "mastery_state": row.get("mastery_state", "not_started"),
            "confidence": float(row.get("confidence", 0)),
        }
        for sid, row in scores.items()
    }

    # Fetch active training plan
    try:
        plan_rows = (
            supabase.table("training_plans")
            .select("*")
            .eq("user_id", caller)
            .eq("status", "active")
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        plan_rows = []

    active_plan = plan_rows[0] if plan_rows else None
    weeks = active_plan.get("weeks", []) if active_plan else []
    current_week_idx = (active_plan.get("current_week", 1) - 1) if active_plan else 0
    active_plan_week = weeks[current_week_idx] if weeks and current_week_idx < len(weeks) else None

    # Fetch coach calibration priorities (best-effort)
    coach_priority_skills: list[str] = []
    try:
        team_rows = (
            supabase.table("team_members")
            .select("team_id")
            .eq("user_id", caller)
            .eq("role", "student")
            .limit(1)
            .execute()
            .data
            or []
        )
        if team_rows:
            team_id = team_rows[0]["team_id"]
            cal_rows = (
                supabase.table("coach_calibration")
                .select("preferences")
                .eq("team_id", team_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if cal_rows:
                prefs = cal_rows[0].get("preferences", {}) or {}
                coach_priority_skills = prefs.get("priority_skills", [])
    except Exception:
        pass

    # Fetch pending assignments for this student (best-effort)
    pending_assignments: list[dict] = []
    try:
        from app.api.assignments import router as _ar  # noqa: F401 — just validate import
        assignment_rows = (
            supabase.table("assignments")
            .select("skill_focus, due_date, status")
            .eq("student_id", caller)
            .eq("status", "pending")
            .order("due_date", desc=False)
            .limit(5)
            .execute()
            .data
            or []
        )
        pending_assignments = assignment_rows
    except Exception:
        pass

    # Fetch active missions
    active_missions: list[dict] = []
    try:
        mission_rows = (
            supabase.table("student_missions")
            .select("skill, status")
            .eq("user_id", caller)
            .in_("status", ["active", "in_progress"])
            .execute()
            .data
            or []
        )
        active_missions = mission_rows
    except Exception:
        pass

    recommendation = compute_next_action(
        mastery_profile=mastery_profile,
        active_plan_week=active_plan_week,
        coach_priority_skills=coach_priority_skills,
        pending_assignments=pending_assignments,
        active_missions=active_missions,
        tournament_date_days=None,
        recent_skill_scores={},
    )

    # Enrich with plan context
    result = dict(recommendation)
    if active_plan:
        result["active_plan"] = {
            "id": active_plan["id"],
            "current_week": active_plan.get("current_week", 1),
            "total_weeks": active_plan.get("total_weeks", 4),
        }
    if active_plan_week:
        result["plan_step"] = {
            "objective": active_plan_week.get("objective"),
            "estimated_hours": active_plan_week.get("estimated_hours"),
            "drill_description": active_plan_week.get("drill_description"),
        }

    return result


# ── Training session persistence ───────────────────────────────────────────────


@router.post("/sessions")
async def start_session(
    payload: dict,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """
    Start or resume a guided training session for a lesson.

    If an active session for this user+lesson already exists, return it
    (idempotent). Autosave semantics: client POSTs on every step transition.
    """
    supabase = get_supabase()
    lesson_id = payload.get("lesson_id", "")
    plan_id = payload.get("plan_id")

    if not lesson_id:
        raise HTTPException(status_code=422, detail="lesson_id is required")

    from app.event_packs.public_forum import get_lesson
    if not get_lesson(lesson_id):
        raise HTTPException(status_code=404, detail=f"Unknown lesson: {lesson_id}")

    now = _now()

    # Try to find an existing active session
    try:
        existing = (
            supabase.table("training_sessions")
            .select("*")
            .eq("user_id", caller)
            .eq("lesson_id", lesson_id)
            .eq("status", "active")
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            return existing[0]
    except Exception:
        pass

    # Create new session
    try:
        result = supabase.table("training_sessions").insert({
            "user_id": caller,
            "lesson_id": lesson_id,
            "plan_id": plan_id,
            "current_step": "lesson",
            "steps_completed": [],
            "status": "active",
            "started_at": now.isoformat(),
            "last_active_at": now.isoformat(),
        }).execute()
        return result.data[0] if result.data else {}
    except Exception as exc:
        logger.error("training_session create failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to start session") from exc


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    payload: dict,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """
    Advance a training session to the next step (autosave).

    Payload may include: current_step, steps_completed, speech_id, drill_id,
    rerecord_id, mastery_before, mastery_after, status.

    Optimistic concurrency: if the caller supplies ``expected_version``, the
    server compares it against the current ``version`` column.  A mismatch
    returns 409 Conflict with the current server state so the client can
    reconcile rather than silently overwrite progress from another tab.
    """
    supabase = get_supabase()
    now = _now()

    # Verify ownership and fetch current version
    try:
        session_rows = (
            supabase.table("training_sessions")
            .select("id, user_id, status, version")
            .eq("id", session_id)
            .eq("user_id", caller)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch session") from exc

    if not session_rows:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_rows[0]
    if session["status"] in ("completed", "abandoned"):
        raise HTTPException(status_code=409, detail="Session already finished")

    # Optimistic concurrency check
    expected_version = payload.pop("expected_version", None)
    current_version = session.get("version", 0)
    if expected_version is not None and int(expected_version) != int(current_version):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "version_conflict",
                "message": "Stale session state — another tab saved ahead of this one.",
                "server_version": current_version,
                "client_version": expected_version,
            },
        )

    allowed_fields = {
        "current_step", "steps_completed", "speech_id", "drill_id",
        "rerecord_id", "mastery_before", "mastery_after", "status",
    }
    update_data = {k: v for k, v in payload.items() if k in allowed_fields}
    update_data["last_active_at"] = now.isoformat()
    update_data["version"] = current_version + 1

    if update_data.get("status") == "completed":
        update_data["completed_at"] = now.isoformat()

    try:
        result = (
            supabase.table("training_sessions")
            .update(update_data)
            .eq("id", session_id)
            .execute()
        )
        return result.data[0] if result.data else {}
    except Exception as exc:
        logger.error("training_session update failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update session") from exc


@router.get("/sessions/active")
async def get_active_session(
    lesson_id: Optional[str] = None,
    caller: str = Depends(get_current_user_id),
) -> dict:
    """
    Return the most recent active session for the authenticated user.
    Optionally filter by lesson_id (for resume-after-refresh).
    """
    supabase = get_supabase()
    try:
        query = (
            supabase.table("training_sessions")
            .select("*")
            .eq("user_id", caller)
            .eq("status", "active")
            .order("last_active_at", desc=True)
            .limit(1)
        )
        if lesson_id:
            query = query.eq("lesson_id", lesson_id)
        rows = query.execute().data or []
        return rows[0] if rows else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch session") from exc


# ── Curriculum validation endpoint ────────────────────────────────────────────


@router.get("/curriculum/validate")
async def validate_curriculum() -> dict:
    """
    Validate the curriculum for consistency and completeness.
    Returns a structured report — no auth required (curriculum is public data).
    """
    from app.services.curriculum_validator import validate_curriculum as _validate
    return _validate()


@router.get("/curriculum/team-progress")
async def get_team_curriculum_progress(
    team_id: str,
    coach_id: Optional[str] = None,
    caller: str = Depends(get_current_user_id),
) -> list[dict]:
    """
    Return curriculum progress grouped by student for a coach's team.

    The coach_id query param is accepted for client compatibility but the
    caller identity is always derived from the verified JWT (auth.uid()).
    """
    supabase = get_supabase()
    _require_coach(supabase, team_id, caller)

    # All students on this team
    try:
        members = (
            supabase.table("team_members")
            .select("user_id")
            .eq("team_id", team_id)
            .eq("role", "student")
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch team members") from exc

    student_ids = [m["user_id"] for m in members]
    if not student_ids:
        return []

    # Curriculum progress for all students
    try:
        progress_rows = (
            supabase.table("curriculum_progress")
            .select("user_id,lesson_id,status,completed_at")
            .in_("user_id", student_ids)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch curriculum progress") from exc

    # Profile display names
    try:
        profiles = (
            supabase.table("profiles")
            .select("id,display_name")
            .in_("id", student_ids)
            .execute()
            .data
            or []
        )
    except Exception:
        profiles = []

    name_map = {p["id"]: p.get("display_name") for p in profiles}

    # Group progress by student
    by_student: dict[str, list[dict]] = {uid: [] for uid in student_ids}
    for row in progress_rows:
        uid = row["user_id"]
        if uid in by_student:
            by_student[uid].append({
                "lesson_id": row["lesson_id"],
                "status": row["status"],
                "completed_at": row.get("completed_at"),
            })

    return [
        {
            "student_id": uid,
            "student_name": name_map.get(uid),
            "progress": by_student[uid],
        }
        for uid in student_ids
    ]
