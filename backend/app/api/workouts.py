"""Workout endpoints — Tournament Prep Workout Mode."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.workout import GenerateWorkoutRequest, UpdateWorkoutRequest, WorkoutRow
from app.services.supabase_client import get_supabase
from app.services.workout_generation import generate_tournament_workout

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workouts"])

_WORKOUT_TITLE: dict[str, str] = {
    "constructive": "Constructive Repair Workout",
    "rebuttal":     "Rebuttal Coverage Workout",
    "summary":      "Summary Collapse Workout",
    "final_focus":  "Final Focus Ballot Workout",
}


def _row_to_workout(row: dict) -> WorkoutRow:
    return WorkoutRow(**row)


# ── POST /speeches/{speech_id}/workout ────────────────────────────────────────

@router.post("/speeches/{speech_id}/workout", response_model=WorkoutRow)
async def generate_workout(speech_id: str, body: GenerateWorkoutRequest) -> WorkoutRow:
    """Generate (or return existing) tournament prep workout for a completed speech."""
    sb = get_supabase()

    # Verify ownership + completed status
    try:
        speech_res = (
            sb.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not speech_res.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    speech = speech_res.data[0]
    if speech.get("status") != "done":
        raise HTTPException(status_code=400, detail="Speech must have a completed report before generating a workout")

    # Return existing unless force_regenerate
    if not body.force_regenerate:
        try:
            existing_res = (
                sb.table("workouts")
                .select("*")
                .eq("speech_id", speech_id)
                .eq("user_id", body.user_id)
                .limit(1)
                .execute()
            )
            if existing_res.data:
                return _row_to_workout(existing_res.data[0])
        except Exception:
            pass  # fall through to generate

    # Load supporting data
    try:
        fb_res = (
            sb.table("feedback_reports")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load feedback report") from exc

    if not fb_res.data:
        raise HTTPException(status_code=400, detail="Feedback report not found. Analyze the speech first.")
    feedback = fb_res.data[0]

    argument_map: Optional[dict] = None
    try:
        am_res = (
            sb.table("argument_maps")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if am_res.data:
            argument_map = am_res.data[0]
    except Exception:
        pass

    drills: list[dict] = []
    try:
        dr_res = (
            sb.table("drills")
            .select("*")
            .eq("speech_id", speech_id)
            .order("order")
            .execute()
        )
        drills = dr_res.data or []
    except Exception:
        pass

    delivery_metrics: Optional[dict] = None
    try:
        dm_res = (
            sb.table("delivery_metrics")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if dm_res.data:
            delivery_metrics = dm_res.data[0]
    except Exception:
        pass

    evidence_checks: Optional[list[dict]] = None
    try:
        ec_res = (
            sb.table("claim_evidence_checks")
            .select("*")
            .eq("speech_id", speech_id)
            .execute()
        )
        if ec_res.data:
            evidence_checks = ec_res.data
    except Exception:
        pass

    block_coverage_checks: Optional[list[dict]] = None
    try:
        bcc_res = (
            sb.table("block_coverage_checks")
            .select("*")
            .eq("speech_id", speech_id)
            .execute()
        )
        if bcc_res.data:
            block_coverage_checks = bcc_res.data
    except Exception:
        pass

    # Generate workout plan
    try:
        plan = generate_tournament_workout(
            speech=speech,
            feedback_report=feedback,
            argument_map=argument_map,
            drills=drills,
            delivery_metrics=delivery_metrics,
            evidence_checks=evidence_checks,
            block_coverage_checks=block_coverage_checks,
        )
    except Exception as exc:
        logger.error("workout_generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate workout") from exc

    now = datetime.now(timezone.utc).isoformat()
    speech_type = speech.get("speech_type") or "constructive"
    title = _WORKOUT_TITLE.get(speech_type, "Tournament Prep Workout")

    upsert_payload: dict = {
        "user_id": body.user_id,
        "speech_id": speech_id,
        "title": title,
        "estimated_minutes": plan["estimated_minutes"],
        "workout_type": "tournament_prep",
        "focus_area": plan["focus_area"],
        "workout_json": {
            "steps": plan["steps"],
            "re_record_goal": plan["re_record_goal"],
            "coach_note": plan["coach_note"],
            "generated_from": plan["generated_from"],
        },
        "updated_at": now,
    }

    # Check existing to decide insert vs update
    try:
        check_res = (
            sb.table("workouts")
            .select("id, status")
            .eq("speech_id", speech_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
        if check_res.data:
            existing_id = check_res.data[0]["id"]
            # Preserve existing status on regeneration
            upsert_payload["status"] = check_res.data[0].get("status", "not_started")
            sb.table("workouts").update(upsert_payload).eq("id", existing_id).execute()
            result_res = (
                sb.table("workouts")
                .select("*")
                .eq("id", existing_id)
                .limit(1)
                .execute()
            )
        else:
            upsert_payload["status"] = "not_started"
            upsert_payload["created_at"] = now
            result_res = sb.table("workouts").insert(upsert_payload).execute()
    except Exception as exc:
        logger.error("workout db write failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save workout") from exc

    return _row_to_workout(result_res.data[0])


# ── GET /speeches/{speech_id}/workout ─────────────────────────────────────────

@router.get("/speeches/{speech_id}/workout", response_model=Optional[WorkoutRow])
async def get_workout(
    speech_id: str,
    user_id: str = Query(...),
) -> Optional[WorkoutRow]:
    """Return the current workout for a speech, or null if none exists."""
    sb = get_supabase()
    try:
        res = (
            sb.table("workouts")
            .select("*")
            .eq("speech_id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load workout") from exc
    if not res.data:
        return None
    return _row_to_workout(res.data[0])


# ── PATCH /workouts/{workout_id} ──────────────────────────────────────────────

@router.patch("/workouts/{workout_id}", response_model=WorkoutRow)
async def update_workout(workout_id: str, body: UpdateWorkoutRequest) -> WorkoutRow:
    """Mark steps complete or update workout status."""
    sb = get_supabase()
    try:
        res = (
            sb.table("workouts")
            .select("*")
            .eq("id", workout_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load workout") from exc

    if not res.data:
        raise HTTPException(status_code=404, detail="Workout not found")

    row = res.data[0]
    workout_json: dict = dict(row.get("workout_json") or {})
    steps: list[dict] = list(workout_json.get("steps") or [])
    now = datetime.now(timezone.utc).isoformat()

    # Mark completed step IDs
    if body.completed_step_ids:
        id_set = set(body.completed_step_ids)
        for step in steps:
            if step.get("id") in id_set:
                step["completed"] = True
    workout_json["steps"] = steps

    # Derive new status
    non_rerecord = [s for s in steps if s.get("category") != "rerecord"]
    any_done = any(s.get("completed") for s in steps)
    all_done = all(s.get("completed") for s in steps)

    current_status = row.get("status", "not_started")
    new_status = body.status or current_status

    if any_done and new_status == "not_started":
        new_status = "in_progress"
    if all_done:
        new_status = "completed"

    completed_at = row.get("completed_at")
    if new_status == "completed" and not completed_at:
        completed_at = now

    patch: dict = {
        "workout_json": workout_json,
        "status": new_status,
        "completed_at": completed_at,
        "updated_at": now,
    }
    try:
        sb.table("workouts").update(patch).eq("id", workout_id).execute()
        updated_res = (
            sb.table("workouts")
            .select("*")
            .eq("id", workout_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update workout") from exc

    result_row = _row_to_workout(updated_res.data[0])

    # Emit mastery evidence when workout is completed (best-effort, non-fatal)
    if new_status == "completed" and current_status != "completed":
        try:
            from app.services.mastery_integration import emit_from_workout
            # Build skill_scores from completed steps that have a skill_target
            skill_scores: dict[str, float] = {}
            for step in steps:
                if step.get("completed") and step.get("skill_target"):
                    # Use score_pct if present; default to 70 for completed steps
                    skill_scores[step["skill_target"]] = float(step.get("score_pct", 70))
            if skill_scores:
                emit_from_workout(
                    supabase=sb,
                    user_id=body.user_id,
                    workout_id=workout_id,
                    skill_scores=skill_scores,
                )
        except Exception:
            pass

    return result_row


# ── GET /workouts ─────────────────────────────────────────────────────────────

@router.get("/workouts", response_model=list[WorkoutRow])
async def list_workouts(user_id: str = Query(...)) -> list[WorkoutRow]:
    """List the most recent workouts for a user (for dashboard)."""
    sb = get_supabase()
    try:
        res = (
            sb.table("workouts")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load workouts") from exc
    return [_row_to_workout(r) for r in (res.data or [])]
