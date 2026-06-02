import logging

from fastapi import APIRouter, HTTPException

from app.models.feedback_report import FeedbackReportRow
from app.services.feedback_generation import FeedbackGenerationError, generate_feedback
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["feedback_reports"])


@router.post("/{speech_id}/generate-feedback", response_model=FeedbackReportRow)
async def generate_feedback_report(speech_id: str) -> FeedbackReportRow:
    supabase = get_supabase()
    logger.info("generate_feedback: speech_id=%s", speech_id)

    # 1. Fetch speech
    try:
        speech_result = (
            supabase.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("generate_feedback: fetch_speech failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not speech_result.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    speech = speech_result.data[0]

    # 2. Fetch transcript — required before feedback
    try:
        transcript_result = (
            supabase.table("transcripts")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "generate_feedback: fetch_transcript failed | exc_type=%s", type(exc).__name__
        )
        raise HTTPException(status_code=500, detail="Failed to fetch transcript") from exc

    if not transcript_result.data:
        raise HTTPException(
            status_code=400,
            detail="Transcript not found. Transcribe the speech before generating feedback.",
        )
    transcript_text: str = transcript_result.data[0]["text"]

    word_count = len(transcript_text.split())
    if word_count < 20:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transcript is too short ({word_count} words). "
                "Record at least 30 seconds for meaningful feedback."
            ),
        )

    # 3. Fetch argument map — required before feedback
    try:
        map_result = (
            supabase.table("argument_maps")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "generate_feedback: fetch_argument_map failed | exc_type=%s", type(exc).__name__
        )
        raise HTTPException(status_code=500, detail="Failed to fetch argument map") from exc

    if not map_result.data:
        raise HTTPException(
            status_code=400,
            detail="Argument map not found. Generate the flow before generating feedback.",
        )
    arguments: list[dict] = map_result.data[0]["arguments"]
    logger.info(
        "generate_feedback: transcript and argument map found | speech_id=%s", speech_id
    )

    # 4. Mark analyzing (best-effort)
    try:
        supabase.table("speeches").update({"status": "analyzing"}).eq("id", speech_id).execute()
        logger.info("generate_feedback: status set to analyzing")
    except Exception:
        logger.warning("generate_feedback: could not set status to analyzing")

    def _set_error_status() -> None:
        try:
            supabase.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
        except Exception:
            pass

    # 5. Generate feedback
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
        logger.info(
            "generate_feedback: generation succeeded | overall_score=%d | speech_id=%s",
            output.overall_score,
            speech_id,
        )
    except FeedbackGenerationError as exc:
        logger.error("generate_feedback: generation failed | speech_id=%s", speech_id)
        _set_error_status()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "generate_feedback: unexpected error | exc_type=%s | speech_id=%s",
            type(exc).__name__,
            speech_id,
        )
        _set_error_status()
        raise HTTPException(
            status_code=500, detail="Feedback generation failed. Check backend logs."
        ) from exc

    # 6. Persist and mark done
    try:
        # Derive overall_score from category sum — never trust the LLM's self-report.
        derived_score = (
            output.scores.clash
            + output.scores.weighing
            + output.scores.extensions
            + output.scores.drops
            + output.scores.judge_adaptation
        )
        raw = output.model_dump()
        raw["overall_score"] = derived_score  # Keep raw_feedback consistent too.
        feedback_data = {
            "speech_id": speech_id,
            "overall_score": derived_score,
            "scores": output.scores.model_dump(),
            "summary": output.summary,
            "strengths": output.strengths,
            "weaknesses": output.weaknesses,
            "raw_feedback": raw,
        }
        result = (
            supabase.table("feedback_reports")
            .upsert(feedback_data, on_conflict="speech_id")
            .execute()
        )
        supabase.table("speeches").update({"status": "done"}).eq("id", speech_id).execute()
        logger.info("generate_feedback: done | speech_id=%s", speech_id)
        return result.data[0]
    except Exception as exc:
        logger.error(
            "generate_feedback: upsert failed | exc_type=%s",
            type(exc).__name__,
        )
        _set_error_status()
        raise HTTPException(
            status_code=500, detail="Feedback generation failed. Check backend logs."
        ) from exc


@router.get("/{speech_id}/feedback", response_model=FeedbackReportRow)
async def get_feedback(speech_id: str) -> FeedbackReportRow:
    try:
        result = (
            get_supabase()
            .table("feedback_reports")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=404, detail="No feedback report found for this speech"
            )
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch feedback report") from exc
