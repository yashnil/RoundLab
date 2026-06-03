"""
Dev-only endpoints for testing and calibration.
Only available when ENVIRONMENT != "production".
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.models.speech import SpeechRow
from app.models.transcript import TranscriptRow
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/demo-speech", response_model=dict)
async def create_demo_speech(user_id: str = Query(...)) -> dict:
    """
    Create a demo speech with a golden high-quality PF summary transcript.

    This endpoint is only available in development/staging environments.
    Use it to test what a 90-100 score looks like and calibrate the rubric.

    Returns:
        dict with speech_id and transcript_id
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Demo endpoint is disabled in production",
        )

    # Load golden transcript
    golden_path = Path(__file__).parent.parent / "examples" / "golden_pf_summary.txt"
    try:
        golden_text = golden_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Golden sample not found. Check backend/app/examples/golden_pf_summary.txt",
        )

    supabase = get_supabase()

    # 1. Create speech
    try:
        speech_result = (
            supabase.table("speeches")
            .insert({
                "user_id": user_id,
                "title": "Demo: High-Quality PF Summary",
                "speech_type": "summary",
                "side": "pro",
                "judge_type": "flow",
                "topic": "Resolved: The United States should substantially increase its renewable energy incentives",
                "status": "pending",
                "audio_url": None,
            })
            .execute()
        )
    except Exception as exc:
        logger.error("create_demo_speech: failed to create speech | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create demo speech") from exc

    speech: SpeechRow = speech_result.data[0]

    # 2. Create transcript
    word_count = len(golden_text.split())
    try:
        transcript_result = (
            supabase.table("transcripts")
            .insert({
                "speech_id": speech["id"],
                "text": golden_text,
                "word_count": word_count,
            })
            .execute()
        )
    except Exception as exc:
        logger.error("create_demo_speech: failed to create transcript | %s", exc)
        # Clean up speech
        try:
            supabase.table("speeches").delete().eq("id", speech["id"]).execute()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to create demo transcript") from exc

    transcript: TranscriptRow = transcript_result.data[0]

    logger.info(
        "create_demo_speech: success | speech_id=%s user_id=%s word_count=%d",
        speech["id"],
        user_id,
        word_count,
    )

    return {
        "speech_id": speech["id"],
        "transcript_id": transcript["id"],
        "message": (
            "Demo speech created. Now generate flow → feedback → drills to see what a "
            "high-quality performance looks like. Expected score: 85-95/100."
        ),
    }
