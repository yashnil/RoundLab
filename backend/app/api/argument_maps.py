import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.argument_map import ArgumentMapRow
from app.services.argument_extraction import ArgumentExtractionError, extract_arguments
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["argument_maps"])


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
        # Assign stable index-based IDs so issues can reference specific arguments
        for idx, item in enumerate(items):
            item.id = f"arg_{idx + 1}"
        arguments_json = [item.model_dump() for item in items]
        map_result = (
            supabase.table("argument_maps")
            .upsert(
                {"speech_id": speech_id, "arguments": arguments_json},
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


@router.get("/{speech_id}/argument-map", response_model=ArgumentMapRow)
async def get_argument_map(speech_id: str, user_id: str = Query(...)) -> ArgumentMapRow:
    supabase = get_supabase()

    # Verify speech ownership
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

    # Fetch argument map
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
