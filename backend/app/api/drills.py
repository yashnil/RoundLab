import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.drill import DrillAttemptCreate, DrillAttemptRow, DrillRow, DrillStatusUpdate
from app.services.drill_attempt_scoring import DrillScoringError, score_drill_attempt
from app.services.drill_generation import DrillGenerationError, generate_drills
from app.services.product_events import track_product_event
from app.services.supabase_client import get_supabase
from app.services.transcription import (
    AudioTooLargeError,
    OpenAITranscriptionError,
    StorageDownloadError,
    transcribe_speech,
)
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
        # Clamp time_limit_seconds to sane range (30–300s) in case LLM goes out of range
        tls = getattr(drill, "time_limit_seconds", None)
        if tls is not None:
            tls = max(30, min(300, int(tls)))
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
            "time_limit_seconds": tls,
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


# ── GET /drills/{drill_id} ────────────────────────────────────────────────────

@drills_router.get("/{drill_id}", response_model=DrillRow)
async def get_drill(drill_id: str, user_id: str = Query(...)) -> DrillRow:
    """Fetch a single drill by ID with ownership check."""
    supabase = get_supabase()
    try:
        result = (
            supabase.table("drills")
            .select("*")
            .eq("id", drill_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("get_drill: fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch drill") from exc

    if not result.data:
        raise HTTPException(status_code=404, detail="Drill not found")
    return result.data[0]


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
            # Emit mastery evidence (best-effort, non-fatal)
            try:
                from app.services.mastery_integration import emit_from_drill_attempt
                drill_row = result.data[0]
                skill_target = drill_row.get("skill_target") or ""
                score_pct = float(drill_row.get("score_pct") or 0)
                emit_from_drill_attempt(
                    supabase=supabase,
                    user_id=user_id,
                    drill_id=drill_id,
                    skill_target=skill_target,
                    score_pct=score_pct,
                )
            except Exception:
                pass

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
    """Create a new drill attempt: upload → transcribe → score (best-effort) → persist."""
    supabase = get_supabase()

    # 1. Fetch full drill and verify ownership
    try:
        drill_res = (
            supabase.table("drills")
            .select("*")
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

    # 2. Transcribe audio (best-effort — failure does not block saving)
    transcript: str | None = None
    try:
        text, _ = transcribe_speech(body.audio_url)
        transcript = text or None
    except (StorageDownloadError, AudioTooLargeError, OpenAITranscriptionError) as exc:
        logger.warning("create_drill_attempt: transcription failed | %s | drill_id=%s", type(exc).__name__, drill_id)
    except Exception as exc:
        logger.warning("create_drill_attempt: transcription unexpected | %s | drill_id=%s", type(exc).__name__, drill_id)

    # 3. Score attempt if transcript available (best-effort)
    score: int | None = None
    feedback_dict: dict | None = None
    if transcript:
        try:
            fb = score_drill_attempt(
                drill_title=drill["title"],
                skill_target=drill["skill_target"],
                instructions=drill.get("instructions"),
                success_criteria=drill.get("success_criteria") or [],
                source_weakness=drill.get("source_weakness"),
                time_limit_seconds=drill.get("time_limit_seconds"),
                difficulty=drill.get("difficulty", "beginner"),
                transcript=transcript,
            )
            score = fb.score
            feedback_dict = fb.model_dump(exclude={"score"})
        except DrillScoringError as exc:
            logger.warning("create_drill_attempt: scoring failed | %s | drill_id=%s", exc, drill_id)
        except Exception as exc:
            logger.warning("create_drill_attempt: scoring unexpected | %s | drill_id=%s", type(exc).__name__, drill_id)

    # 4. Build attempt row (only include scored fields if present)
    attempt_row: dict = {
        "drill_id": drill_id,
        "user_id": drill["user_id"],
        "audio_url": body.audio_url,
    }
    if transcript is not None:
        attempt_row["response"] = transcript
    if score is not None:
        attempt_row["score"] = score
    if feedback_dict is not None:
        attempt_row["feedback"] = feedback_dict

    # 5. Insert attempt
    try:
        result = supabase.table("drill_attempts").insert(attempt_row).execute()
        attempt = result.data[0]
        logger.info(
            "create_drill_attempt: saved | drill_id=%s attempt_id=%s score=%s has_transcript=%s",
            drill_id, attempt["id"], score, transcript is not None,
        )

        # Award XP
        try:
            previous_attempts = (
                supabase.table("drill_attempts")
                .select("id", count="exact")
                .eq("drill_id", drill_id)
                .eq("user_id", user_id)
                .execute()
            )
            is_first_attempt = (previous_attempts.count or 0) == 1
            if is_first_attempt:
                award_xp(user_id, "drill_attempt_first", f"drill_attempt:{attempt['id']}")
            else:
                award_xp(user_id, "drill_attempt_repeat", f"drill_attempt:{attempt['id']}")
        except Exception as xp_exc:
            logger.warning("create_drill_attempt: XP award failed | %s", type(xp_exc).__name__)

        # Track analytics event (best-effort)
        track_product_event(
            user_id=user_id,
            event_name="drill_attempt_saved",
            drill_id=drill_id,
            metadata={"has_transcript": transcript is not None, "has_score": score is not None},
        )
        if score is not None:
            track_product_event(
                user_id=user_id,
                event_name="drill_attempt_scored",
                drill_id=drill_id,
                metadata={"score": score},
            )

        return attempt
    except Exception as exc:
        logger.error("create_drill_attempt: insert failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to save drill attempt") from exc


# ── Drill rating models ────────────────────────────────────────────────────────

class DrillRatingCreate(BaseModel):
    rating: str  # helpful | somewhat | not_helpful
    comment: Optional[str] = None
    drill_attempt_id: Optional[str] = None


class DrillRatingRow(BaseModel):
    id: str
    user_id: str
    drill_id: str
    drill_attempt_id: Optional[str] = None
    rating: str
    comment: Optional[str] = None
    created_at: str


# ── POST /drills/{drill_id}/rating ────────────────────────────────────────────

@drills_router.post("/{drill_id}/rating", response_model=DrillRatingRow)
async def rate_drill(drill_id: str, body: DrillRatingCreate, user_id: str = Query(...)) -> DrillRatingRow:
    """Submit or update a helpfulness rating for a drill."""
    supabase = get_supabase()

    valid_ratings = {"helpful", "somewhat", "not_helpful"}
    if body.rating not in valid_ratings:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}",
        )

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

    row: dict = {
        "user_id": user_id,
        "drill_id": drill_id,
        "rating": body.rating,
    }
    if body.comment:
        row["comment"] = body.comment
    if body.drill_attempt_id:
        row["drill_attempt_id"] = body.drill_attempt_id

    try:
        result = (
            supabase.table("drill_ratings")
            .upsert(row, on_conflict="user_id,drill_id")
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save drill rating")

        track_product_event(
            user_id=user_id,
            event_name="drill_rated",
            drill_id=drill_id,
            metadata={"rating": body.rating},
        )
        logger.info("rate_drill: success | drill_id=%s rating=%s", drill_id, body.rating)
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("rate_drill: failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to save drill rating") from exc


# ── GET /drills/{drill_id}/rating ─────────────────────────────────────────────

@drills_router.get("/{drill_id}/rating", response_model=Optional[DrillRatingRow])
async def get_drill_rating(drill_id: str, user_id: str = Query(...)) -> Optional[DrillRatingRow]:
    """Fetch the current user's rating for a drill, or null if not yet rated."""
    supabase = get_supabase()
    try:
        result = (
            supabase.table("drill_ratings")
            .select("*")
            .eq("drill_id", drill_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as exc:
        logger.error("get_drill_rating: failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch drill rating") from exc
