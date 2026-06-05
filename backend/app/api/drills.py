import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.drill import DrillAttemptCreate, DrillAttemptRow, DrillRow, DrillStatusUpdate
from app.services.drill_generation import DrillGenerationError, generate_drills
from app.services.supabase_client import get_supabase
from app.services.xp_ledger import award_xp

logger = logging.getLogger(__name__)

# Routes nested under /speeches for speech-scoped drill operations
speech_drills_router = APIRouter(prefix="/speeches", tags=["drills"])

# Routes at /drills for drill-level operations
drills_router = APIRouter(prefix="/drills", tags=["drills"])


# ── POST /speeches/{speech_id}/generate-drills ────────────────────────────────

@speech_drills_router.post("/{speech_id}/generate-drills", response_model=list[DrillRow])
async def generate_drills_for_speech(speech_id: str, user_id: str = Query(...)) -> list[DrillRow]:
    """Generate 3 personalized drills from the speech's feedback report."""
    supabase = get_supabase()
    logger.info("generate_drills: speech_id=%s", speech_id)

    # 1. Fetch speech and verify ownership
    try:
        speech_res = (
            supabase.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("generate_drills: fetch_speech failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not speech_res.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    speech = speech_res.data[0]

    # 2. Fetch feedback report — required
    try:
        fb_res = (
            supabase.table("feedback_reports")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("generate_drills: fetch_feedback failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch feedback report") from exc

    if not fb_res.data:
        raise HTTPException(
            status_code=400,
            detail="Feedback report not found. Generate feedback before generating drills.",
        )
    feedback = fb_res.data[0]

    # 3. Fetch transcript
    try:
        tx_res = (
            supabase.table("transcripts")
            .select("text, word_count")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("generate_drills: fetch_transcript failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch transcript") from exc

    transcript_text = tx_res.data[0]["text"] if tx_res.data else ""
    word_count = tx_res.data[0].get("word_count") or len(transcript_text.split())

    if word_count < 20:
        raise HTTPException(
            status_code=400,
            detail="Transcript is too short for useful drills. Record at least 30 seconds, then generate feedback again.",
        )

    # 4. Fetch argument map
    try:
        map_res = (
            supabase.table("argument_maps")
            .select("arguments")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("generate_drills: fetch_argmap failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch argument map") from exc

    arguments: list[dict] = map_res.data[0]["arguments"] if map_res.data else []

    # 5. Extract feedback context
    raw = feedback.get("raw_feedback") or {}
    weaknesses: list[str] = feedback.get("weaknesses") or []
    top_3_priorities: list[str] = raw.get("top_3_priorities") or []

    # 6. Generate drills via LLM
    try:
        drill_items = generate_drills(
            weaknesses=weaknesses,
            top_3_priorities=top_3_priorities,
            transcript_text=transcript_text,
            arguments=arguments,
            speech_type=speech.get("speech_type", ""),
            side=speech.get("side"),
            topic=speech.get("topic"),
            judge_type=speech.get("judge_type"),
        )
    except DrillGenerationError as exc:
        logger.error("generate_drills: generation failed | speech_id=%s", speech_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "generate_drills: unexpected error | exc_type=%s | speech_id=%s",
            type(exc).__name__,
            speech_id,
        )
        raise HTTPException(
            status_code=500, detail="Drill generation failed. Check backend logs."
        ) from exc

    # 7. Delete existing drills for this speech and upsert new ones
    try:
        supabase.table("drills").delete().eq("speech_id", speech_id).execute()
    except Exception as exc:
        logger.warning("generate_drills: could not delete old drills | %s", type(exc).__name__)

    rows = []
    for i, drill in enumerate(drill_items, start=1):
        row = {
            "speech_id": speech_id,
            "user_id": speech["user_id"],
            "title": drill.title,
            "description": drill.description,
            "skill_target": drill.skill_target,
            "prompt": drill.prompt,
            "order": i,
            "instructions": drill.instructions,
            "success_criteria": drill.success_criteria,
            "source_weakness": drill.source_weakness,
            "difficulty": drill.difficulty,
            "status": "assigned",
        }
        rows.append(row)

    try:
        result = supabase.table("drills").insert(rows).execute()
        logger.info("generate_drills: inserted %d drills | speech_id=%s", len(rows), speech_id)
        return result.data
    except Exception as exc:
        logger.error(
            "generate_drills: insert failed | exc_type=%s | exc=%s | speech_id=%s | row_count=%d",
            type(exc).__name__,
            str(exc),
            speech_id,
            len(rows),
        )
        # Log first row for debugging
        if rows:
            logger.error("generate_drills: sample row=%s", rows[0])

        error_detail = f"Failed to save drills: {str(exc)}"
        raise HTTPException(status_code=500, detail=error_detail) from exc


# ── GET /speeches/{speech_id}/drills ─────────────────────────────────────────

@speech_drills_router.get("/{speech_id}/drills", response_model=list[DrillRow])
async def get_drills(speech_id: str, user_id: str = Query(...)) -> list[DrillRow]:
    """Return saved drills for a speech, ordered by drill order."""
    supabase = get_supabase()

    # Verify speech ownership
    try:
        speech_res = (
            supabase.table("speeches")
            .select("id")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not speech_res.data:
            raise HTTPException(status_code=404, detail="Speech not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify speech ownership") from exc

    # Fetch drills
    try:
        result = (
            supabase.table("drills")
            .select("*")
            .eq("speech_id", speech_id)
            .order("order")
            .execute()
        )
        return result.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch drills") from exc


# ── PATCH /drills/{drill_id} ──────────────────────────────────────────────────

@drills_router.patch("/{drill_id}", response_model=DrillRow)
async def update_drill(drill_id: str, body: DrillStatusUpdate, user_id: str = Query(...)) -> DrillRow:
    """Update a drill's status or save a text response/attempt."""
    supabase = get_supabase()

    # Verify drill ownership
    try:
        drill_check = (
            supabase.table("drills")
            .select("id")
            .eq("id", drill_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not drill_check.data:
            raise HTTPException(status_code=404, detail="Drill not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify drill ownership") from exc

    update_data: dict = {}
    if body.status is not None:
        valid_statuses = {"assigned", "attempted", "completed"}
        if body.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(valid_statuses)}",
            )
        update_data["status"] = body.status
    if body.response is not None:
        update_data["response"] = body.response

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        result = (
            supabase.table("drills")
            .update(update_data)
            .eq("id", drill_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Drill not found")

        # Award XP for completing drill
        if body.status == "completed":
            try:
                award_xp(user_id, "drill_completed", f"drill_completed:{drill_id}")
            except Exception as xp_exc:
                logger.warning("update_drill: XP award failed | %s", type(xp_exc).__name__)

        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update drill") from exc


# ── GET /drills/{drill_id}/attempts ───────────────────────────────────────────

@drills_router.get("/{drill_id}/attempts", response_model=list[DrillAttemptRow])
async def get_drill_attempts(drill_id: str, user_id: str = Query(...)) -> list[DrillAttemptRow]:
    """Return all attempts for a given drill, newest first."""
    supabase = get_supabase()

    # Verify drill ownership
    try:
        drill_res = (
            supabase.table("drills")
            .select("id")
            .eq("id", drill_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("get_drill_attempts: drill fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch drill") from exc

    if not drill_res.data:
        raise HTTPException(status_code=404, detail="Drill not found")

    # Fetch attempts
    try:
        result = (
            supabase.table("drill_attempts")
            .select("*")
            .eq("drill_id", drill_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_drill_attempts: fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch drill attempts") from exc


# ── POST /drills/{drill_id}/attempts ──────────────────────────────────────────

@drills_router.post("/{drill_id}/attempts", response_model=DrillAttemptRow)
async def create_drill_attempt(drill_id: str, body: DrillAttemptCreate, user_id: str = Query(...)) -> DrillAttemptRow:
    """Create a new drill attempt with audio."""
    supabase = get_supabase()

    # 1. Fetch drill and verify ownership
    try:
        drill_res = (
            supabase.table("drills")
            .select("id, user_id")
            .eq("id", drill_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("create_drill_attempt: drill fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch drill") from exc

    if not drill_res.data:
        raise HTTPException(status_code=404, detail="Drill not found")

    drill = drill_res.data[0]

    # 2. Create attempt record
    attempt_row = {
        "drill_id": drill_id,
        "user_id": drill["user_id"],
        "audio_url": body.audio_url,
    }

    try:
        result = supabase.table("drill_attempts").insert(attempt_row).execute()
        attempt = result.data[0]
        logger.info("create_drill_attempt: created | drill_id=%s attempt_id=%s", drill_id, attempt["id"])

        # Award XP for drill attempt (first attempt gets more XP)
        # Check if this is first attempt for this drill
        try:
            previous_attempts = (
                supabase.table("drill_attempts")
                .select("id", count="exact")
                .eq("drill_id", drill_id)
                .eq("user_id", user_id)
                .execute()
            )
            is_first_attempt = (previous_attempts.count or 0) == 1  # Just created this one

            if is_first_attempt:
                award_xp(user_id, "drill_attempt_first", f"drill_attempt:{attempt['id']}")
            else:
                award_xp(user_id, "drill_attempt_repeat", f"drill_attempt:{attempt['id']}")
        except Exception as xp_exc:
            logger.warning("create_drill_attempt: XP award failed | %s", type(xp_exc).__name__)

        return attempt
    except Exception as exc:
        logger.error("create_drill_attempt: insert failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to save drill attempt") from exc
