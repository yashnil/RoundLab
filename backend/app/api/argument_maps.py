import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.argument_map import ArgumentItem, ArgumentMapCorrectionRequest, ArgumentMapRow
from app.models.feedback_report import FeedbackReportRow
from app.models.drill import DrillRow
from app.services.argument_extraction import ArgumentExtractionError, extract_arguments
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["argument_maps"])


# ── Response model for regeneration ──────────────────────────────────────────

class RegenerateFromFlowResponse(BaseModel):
    feedback: FeedbackReportRow
    drills: list[DrillRow]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assign_missing_ids(args: list[ArgumentItem]) -> list[ArgumentItem]:
    """Assign stable arg_N IDs to any items that don't have one."""
    max_n = 0
    for a in args:
        if a.id and a.id.startswith("arg_"):
            try:
                max_n = max(max_n, int(a.id[4:]))
            except ValueError:
                pass
    next_n = max_n + 1
    for a in args:
        if not a.id:
            a.id = f"arg_{next_n}"
            next_n += 1
    return args


# ── POST /speeches/{speech_id}/extract-arguments ─────────────────────────────

@router.post("/{speech_id}/extract-arguments", response_model=ArgumentMapRow)
async def extract(speech_id: str, user_id: str = Query(...)) -> ArgumentMapRow:
    supabase = get_supabase()
    logger.info("extract_arguments: speech_id=%s", speech_id)

    # 1. Fetch speech and verify ownership
    try:
        speech_result = (
            supabase.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("extract_arguments: fetch_speech failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not speech_result.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    speech = speech_result.data[0]

    # 2. Fetch transcript — required before extraction
    try:
        transcript_result = (
            supabase.table("transcripts")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("extract_arguments: fetch_transcript failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch transcript") from exc

    if not transcript_result.data:
        raise HTTPException(
            status_code=400,
            detail="Transcript not found. Transcribe the speech before generating the flow.",
        )
    transcript_text: str = transcript_result.data[0]["text"]

    word_count = len(transcript_text.split())
    if word_count < 20:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transcript is too short ({word_count} words). "
                "Record at least 30 seconds for a meaningful flow."
            ),
        )

    logger.info("extract_arguments: transcript found | speech_id=%s", speech_id)

    # 3. Mark analyzing (best-effort)
    try:
        supabase.table("speeches").update({"status": "analyzing"}).eq("id", speech_id).execute()
        logger.info("extract_arguments: status set to analyzing")
    except Exception:
        logger.warning("extract_arguments: could not set status to analyzing")

    def _set_error_status() -> None:
        try:
            supabase.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
        except Exception:
            pass

    # 4. Extract arguments
    try:
        items = extract_arguments(
            text=transcript_text,
            speech_type=speech.get("speech_type", ""),
            side=speech.get("side"),
            topic=speech.get("topic"),
            judge_type=speech.get("judge_type"),
        )
        logger.info(
            "extract_arguments: extraction succeeded | argument_count=%d | speech_id=%s",
            len(items),
            speech_id,
        )
    except ArgumentExtractionError as exc:
        logger.error("extract_arguments: extraction failed | speech_id=%s", speech_id)
        _set_error_status()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "extract_arguments: unexpected error | exc_type=%s | speech_id=%s",
            type(exc).__name__,
            speech_id,
        )
        _set_error_status()
        raise HTTPException(
            status_code=500, detail="Argument extraction failed. Check backend logs."
        ) from exc

    # 5. Persist and mark done
    try:
        for idx, item in enumerate(items):
            item.id = f"arg_{idx + 1}"
        arguments_json = [item.model_dump() for item in items]
        map_result = (
            supabase.table("argument_maps")
            .upsert(
                {
                    "speech_id": speech_id,
                    "arguments": arguments_json,
                    "source_type": "ai",
                    "original_arguments": None,
                    "user_corrected_at": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="speech_id",
            )
            .execute()
        )
        supabase.table("speeches").update({"status": "done"}).eq("id", speech_id).execute()
        logger.info("extract_arguments: done | speech_id=%s", speech_id)
        return map_result.data[0]
    except Exception as exc:
        logger.error(
            "extract_arguments: upsert or update_status failed | exc_type=%s",
            type(exc).__name__,
        )
        _set_error_status()
        raise HTTPException(
            status_code=500, detail="Argument extraction failed. Check backend logs."
        ) from exc


# ── GET /speeches/{speech_id}/argument-map ────────────────────────────────────

@router.get("/{speech_id}/argument-map", response_model=ArgumentMapRow)
async def get_argument_map(speech_id: str, user_id: str = Query(...)) -> ArgumentMapRow:
    supabase = get_supabase()

    try:
        speech_check = (
            supabase.table("speeches")
            .select("id")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not speech_check.data:
            raise HTTPException(status_code=404, detail="Speech not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify speech ownership") from exc

    try:
        result = (
            supabase.table("argument_maps")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=404, detail="No argument map found for this speech"
            )
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch argument map") from exc


# ── PATCH /speeches/{speech_id}/argument-map ─────────────────────────────────

@router.patch("/{speech_id}/argument-map", response_model=ArgumentMapRow)
async def save_argument_map_correction(
    speech_id: str,
    body: ArgumentMapCorrectionRequest,
    user_id: str = Query(...),
) -> ArgumentMapRow:
    """Save a user-corrected argument map. Preserves the original AI draft."""
    supabase = get_supabase()
    logger.info("save_correction: speech_id=%s user_id=%s", speech_id, user_id)

    # 1. Verify ownership
    try:
        speech_check = (
            supabase.table("speeches")
            .select("id")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify speech ownership") from exc
    if not speech_check.data:
        raise HTTPException(status_code=404, detail="Speech not found")

    # 2. Load existing argument map — must exist before correcting
    try:
        existing = (
            supabase.table("argument_maps")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch argument map") from exc
    if not existing.data:
        raise HTTPException(
            status_code=404,
            detail="No argument map found. Generate the flow first, then correct it.",
        )
    current = existing.data[0]

    # 3. Assign stable IDs to any new arguments
    corrected_items = _assign_missing_ids(list(body.arguments))
    corrected_json = [item.model_dump() for item in corrected_items]

    # 4. Preserve original AI arguments on first correction
    original_to_store: Optional[list] = current.get("original_arguments")
    if current.get("source_type", "ai") == "ai":
        # First time user is correcting — snapshot the AI output
        original_to_store = current.get("arguments")

    now_ts = datetime.now(timezone.utc).isoformat()

    # 5. Persist correction
    update_payload: dict[str, Any] = {
        "arguments": corrected_json,
        "source_type": "user_corrected",
        "user_corrected_at": now_ts,
        "updated_at": now_ts,
    }
    if original_to_store is not None:
        update_payload["original_arguments"] = original_to_store
    if body.correction_notes is not None:
        update_payload["correction_notes"] = body.correction_notes

    try:
        result = (
            supabase.table("argument_maps")
            .update(update_payload)
            .eq("speech_id", speech_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save correction")
        logger.info(
            "save_correction: saved | args=%d speech_id=%s",
            len(corrected_json),
            speech_id,
        )
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "save_correction: update failed | exc_type=%s | speech_id=%s",
            type(exc).__name__,
            speech_id,
        )
        raise HTTPException(status_code=500, detail="Failed to save flow correction") from exc


# ── POST /speeches/{speech_id}/regenerate-from-flow ──────────────────────────

@router.post("/{speech_id}/regenerate-from-flow", response_model=RegenerateFromFlowResponse)
async def regenerate_from_corrected_flow(
    speech_id: str,
    user_id: str = Query(...),
) -> RegenerateFromFlowResponse:
    """
    Regenerate coaching feedback and drills from the corrected argument map.

    Does NOT re-run transcription. Uses the latest (possibly user-corrected) argument map
    as the source of truth for argument structure.
    """
    # Local imports to avoid circular deps and keep startup fast
    from app.services.feedback_generation import FeedbackGenerationError, generate_feedback
    from app.services.drill_generation import DrillGenerationError, generate_drills
    from app.services.deterministic_scoring import (
        SCORING_VERSION,
        calculate_rubric_scores,
        compute_report_fingerprint,
        map_rubric_to_legacy_scores,
    )

    supabase = get_supabase()
    logger.info("regenerate_from_flow: START | speech_id=%s", speech_id)

    # 1. Verify ownership and load speech
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
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc
    if not speech_res.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    speech = speech_res.data[0]

    # 2. Load transcript — required, do NOT re-run transcription
    try:
        tx_res = (
            supabase.table("transcripts")
            .select("text, word_count")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch transcript") from exc
    if not tx_res.data:
        raise HTTPException(
            status_code=400,
            detail="Transcript not found. The speech must be transcribed before regenerating coaching.",
        )
    transcript_text: str = tx_res.data[0]["text"]
    word_count: int = tx_res.data[0].get("word_count") or len(transcript_text.split())

    # 3. Load argument map — use latest (corrected if available)
    try:
        map_res = (
            supabase.table("argument_maps")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch argument map") from exc
    if not map_res.data:
        raise HTTPException(
            status_code=400,
            detail="No argument map found. Generate the flow before regenerating coaching.",
        )
    arg_map_row = map_res.data[0]
    arguments: list[dict] = arg_map_row.get("arguments") or []
    is_corrected = arg_map_row.get("source_type") == "user_corrected"

    logger.info(
        "regenerate_from_flow: source_type=%s args=%d speech_id=%s",
        arg_map_row.get("source_type"),
        len(arguments),
        speech_id,
    )

    # 4. Generate feedback from corrected argument map
    try:
        output = generate_feedback(
            text=transcript_text,
            arguments=arguments,
            speech_type=speech.get("speech_type", ""),
            side=speech.get("side"),
            topic=speech.get("topic"),
            judge_type=speech.get("judge_type"),
            word_count=word_count,
        )
    except FeedbackGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "regenerate_from_flow: feedback failed | exc_type=%s | speech_id=%s",
            type(exc).__name__,
            speech_id,
        )
        raise HTTPException(status_code=500, detail="Feedback generation failed. Please try again.") from exc

    # 5. Deterministic scoring + fingerprint
    det_scores = calculate_rubric_scores(
        speech_type=speech.get("speech_type", ""),
        transcript_text=transcript_text,
        argument_map=arguments,
        word_count=word_count,
    )
    derived_score = sum(det_scores.values())
    legacy_scores = map_rubric_to_legacy_scores(det_scores, speech.get("speech_type", ""))
    fingerprint = compute_report_fingerprint(
        transcript_text=transcript_text,
        speech_type=speech.get("speech_type", ""),
        argument_map=arguments,
    )

    now_ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

    raw: dict[str, Any] = output.model_dump()
    raw.update({
        "overall_score": derived_score,
        "deterministic_scores": det_scores,
        "scoring_version": SCORING_VERSION,
        "report_input_hash": fingerprint,
        "regenerated_from_correction": is_corrected,
        "flow_correction_regenerated_at": now_ts,
    })

    feedback_data: dict[str, Any] = {
        "speech_id": speech_id,
        "overall_score": derived_score,
        "scores": legacy_scores,
        "summary": output.summary,
        "strengths": output.strengths,
        "weaknesses": output.weaknesses,
        "raw_feedback": raw,
        "scoring_version": SCORING_VERSION,
        "report_input_hash": fingerprint,
        "last_regenerated_at": now_ts,
    }

    try:
        fb_result = (
            supabase.table("feedback_reports")
            .upsert(feedback_data, on_conflict="speech_id")
            .execute()
        )
    except Exception:
        # Fall back to base payload if new columns not yet migrated
        base_data = {k: v for k, v in feedback_data.items()
                     if k not in ("scoring_version", "report_input_hash", "last_regenerated_at")}
        fb_result = (
            supabase.table("feedback_reports")
            .upsert(base_data, on_conflict="speech_id")
            .execute()
        )

    feedback_row = fb_result.data[0] if fb_result.data else feedback_data

    # 6. Regenerate drills — preserve completed/attempted, replace assigned
    try:
        existing_drills_res = (
            supabase.table("drills")
            .select("id, status, order")
            .eq("speech_id", speech_id)
            .execute()
        )
        existing_drills = existing_drills_res.data or []
    except Exception:
        existing_drills = []

    preserved = [d for d in existing_drills if d.get("status") not in ("assigned",)]
    max_order = max((d.get("order", 0) for d in preserved), default=0)

    try:
        supabase.table("drills").delete().eq("speech_id", speech_id).eq("status", "assigned").execute()
    except Exception as exc:
        logger.warning("regenerate_from_flow: drill delete failed (non-fatal) | %s", type(exc).__name__)

    # Generate new drills
    weaknesses: list[str] = output.weaknesses or []
    top_3: list[str] = raw.get("top_3_priorities") or []
    new_drill_rows: list[dict] = []
    try:
        drill_items = generate_drills(
            weaknesses=weaknesses,
            top_3_priorities=top_3,
            transcript_text=transcript_text,
            arguments=arguments,
            speech_type=speech.get("speech_type", ""),
            side=speech.get("side"),
            topic=speech.get("topic"),
            judge_type=speech.get("judge_type"),
        )
        for i, d in enumerate(drill_items, start=max_order + 1):
            tls = getattr(d, "time_limit_seconds", None)
            if tls is not None:
                tls = max(30, min(300, int(tls)))
            new_drill_rows.append({
                "speech_id": speech_id,
                "user_id": user_id,
                "title": d.title,
                "description": d.description,
                "skill_target": d.skill_target,
                "prompt": d.prompt,
                "order": i,
                "instructions": d.instructions,
                "success_criteria": d.success_criteria,
                "source_weakness": d.source_weakness,
                "difficulty": d.difficulty,
                "status": "assigned",
                "time_limit_seconds": tls,
            })
        if new_drill_rows:
            drill_insert_res = supabase.table("drills").insert(new_drill_rows).execute()
            new_drills = drill_insert_res.data or []
        else:
            new_drills = []
    except (DrillGenerationError, Exception) as exc:
        logger.warning(
            "regenerate_from_flow: drill generation failed (non-fatal) | %s", type(exc).__name__
        )
        new_drills = []

    # 7. Mark speech done
    try:
        supabase.table("speeches").update({"status": "done"}).eq("id", speech_id).execute()
    except Exception:
        pass

    logger.info(
        "regenerate_from_flow: DONE | score=%d new_drills=%d speech_id=%s",
        derived_score,
        len(new_drills),
        speech_id,
    )
    return RegenerateFromFlowResponse(
        feedback=feedback_row,
        drills=new_drills,
    )
