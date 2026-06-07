import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.speech import SpeechCreateRequest, SpeechRow, SpeechUpdateRequest
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["speeches"])


@router.post("", response_model=SpeechRow, status_code=201)
async def create_speech(body: SpeechCreateRequest) -> SpeechRow:
    try:
        result = (
            get_supabase()
            .table("speeches")
            .insert(
                {
                    "user_id": body.user_id,
                    "title": body.title,
                    "speech_type": body.speech_type,
                    "side": body.side,
                    "judge_type": body.judge_type,
                    "topic": body.topic,
                    "status": "pending",
                }
            )
            .execute()
        )
        return result.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create speech") from exc


@router.get("", response_model=list[SpeechRow])
async def list_speeches(user_id: str = Query(...)) -> list[SpeechRow]:
    try:
        result = (
            get_supabase()
            .table("speeches")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speeches") from exc


@router.get("/{speech_id}", response_model=SpeechRow)
async def get_speech(speech_id: str, user_id: str = Query(...)) -> SpeechRow:
    try:
        result = (
            get_supabase()
            .table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Speech not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc


@router.patch("/{speech_id}", response_model=SpeechRow)
async def update_speech_audio(speech_id: str, body: SpeechUpdateRequest, user_id: str = Query(...)) -> SpeechRow:
    update_fields: dict = {"audio_url": body.audio_url}
    if body.duration_seconds is not None:
        # Clamp to sane range: 5s–3600s
        update_fields["duration_seconds"] = max(5, min(3600, body.duration_seconds))
    try:
        result = (
            get_supabase()
            .table("speeches")
            .update(update_fields)
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Speech not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update speech") from exc


@router.delete("/{speech_id}", status_code=200)
async def delete_speech(speech_id: str, user_id: str = Query(...)) -> dict:
    supabase = get_supabase()

    # 1. Fetch speech to verify ownership and get audio_url
    try:
        result = (
            supabase.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not result.data:
        raise HTTPException(status_code=404, detail="Speech not found")

    audio_url = result.data[0].get("audio_url")

    # 2. Cascade delete dependent records
    try:
        supabase.table("feedback_reports").delete().eq("speech_id", speech_id).execute()
        supabase.table("argument_maps").delete().eq("speech_id", speech_id).execute()
        supabase.table("transcripts").delete().eq("speech_id", speech_id).execute()
        supabase.table("speeches").delete().eq("id", speech_id).execute()
    except Exception as exc:
        logger.error("delete_speech: cascade delete failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to delete speech") from exc

    # 3. Delete audio from storage (best-effort — don't fail the request if storage errors)
    if audio_url:
        try:
            supabase.storage.from_("audio").remove([audio_url])
        except Exception:
            logger.warning("delete_speech: storage delete failed for %s", audio_url)

    return {"deleted": True}


@router.post("/{speech_id}/reset-audio", response_model=SpeechRow)
async def reset_audio(speech_id: str, user_id: str = Query(...)) -> SpeechRow:
    supabase = get_supabase()

    # 1. Fetch speech and verify ownership
    try:
        result = (
            supabase.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not result.data:
        raise HTTPException(status_code=404, detail="Speech not found")

    audio_url = result.data[0].get("audio_url")

    # 2. Delete audio from storage if present (best-effort)
    if audio_url:
        try:
            supabase.storage.from_("audio").remove([audio_url])
        except Exception:
            logger.warning("reset_audio: storage delete failed for %s", audio_url)

    # 3. Cascade delete transcript, argument map, and feedback report
    try:
        supabase.table("feedback_reports").delete().eq("speech_id", speech_id).execute()
        supabase.table("argument_maps").delete().eq("speech_id", speech_id).execute()
        supabase.table("transcripts").delete().eq("speech_id", speech_id).execute()
    except Exception as exc:
        logger.error("reset_audio: cascade delete failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to reset audio") from exc

    # 4. Reset speech record
    try:
        updated = (
            supabase.table("speeches")
            .update({"audio_url": None, "status": "pending"})
            .eq("id", speech_id)
            .execute()
        )
        return updated.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update speech") from exc
