import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.models.feedback_report import FeedbackRatingUpdate, FeedbackReportRow
from app.services.feedback_generation import FeedbackGenerationError, generate_feedback
from app.services.pf_rubrics import calibrate_scores, get_rubric
from app.services.deterministic_scoring import (
    SCORING_VERSION,
    calculate_rubric_scores,
    compute_report_fingerprint,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["feedback_reports"])

# Regeneration cooldown in seconds
REGENERATE_COOLDOWN_SECONDS = 60


def _map_rubric_to_legacy_scores(calibrated: dict[str, int], speech_type: str) -> dict[str, int]:
    """Map calibrated rubric dimension scores to legacy 5-dimension schema.

    This ensures the scores displayed in the frontend add up to the overall_score.
    For constructive speeches, the mapping is:
    - case_structure → clash
    - warranting → judge_adaptation
    - evidence_use → drops
    - impact_development → weighing
    - judge_clarity → extensions
    """
    if speech_type == "constructive":
        return {
            "clash": calibrated.get("case_structure", 0),
            "weighing": calibrated.get("impact_development", 0),
            "extensions": calibrated.get("judge_clarity", 0),
            "drops": calibrated.get("evidence_use", 0),
            "judge_adaptation": calibrated.get("warranting", 0),
        }
    elif speech_type == "rebuttal":
        return {
            "clash": calibrated.get("clash_refutation", 0),
            "weighing": calibrated.get("weighing_setup", 0),
            "extensions": calibrated.get("response_quality", 0),
            "drops": calibrated.get("coverage_prioritization", 0),
            "judge_adaptation": calibrated.get("evidence_comparison", 0),
        }
    elif speech_type == "summary":
        return {
            "clash": calibrated.get("frontlining", 0),
            "weighing": calibrated.get("weighing", 0),
            "extensions": calibrated.get("extension_quality", 0),
            "drops": calibrated.get("collapse_strategy", 0),
            "judge_adaptation": calibrated.get("judge_clarity", 0),
        }
    elif speech_type == "final_focus":
        return {
            "clash": calibrated.get("crystallization", 0),
            "weighing": calibrated.get("comparative_weighing", 0),
            "extensions": calibrated.get("ballot_story", 0),
            "drops": calibrated.get("consistency", 0),
            "judge_adaptation": calibrated.get("judge_adaptation", 0),
        }
    else:
        # Default: return zeros if unknown speech type
        return {
            "clash": 0,
            "weighing": 0,
            "extensions": 0,
            "drops": 0,
            "judge_adaptation": 0,
        }


@router.post("/{speech_id}/generate-feedback", response_model=FeedbackReportRow)
async def generate_feedback_report(speech_id: str, user_id: str = Query(...)) -> FeedbackReportRow:
    supabase = get_supabase()
    logger.info("generate_feedback: START | speech_id=%s | user_id=%s", speech_id, user_id)

    # 1. Fetch speech and verify ownership
    logger.info("generate_feedback: stage=load_speech | speech_id=%s", speech_id)
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
        logger.error("generate_feedback: fetch_speech failed | exc_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc

    if not speech_result.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    speech = speech_result.data[0]
    logger.info("generate_feedback: speech loaded | speech_type=%s | word_count=%s", speech.get("speech_type"), speech.get("word_count"))

    # 2. Fetch transcript — required before feedback
    logger.info("generate_feedback: stage=load_transcript | speech_id=%s", speech_id)
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
    logger.info("generate_feedback: transcript loaded | word_count_calc=%d", len(transcript_text.split()))

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
    logger.info("generate_feedback: stage=load_argument_map | speech_id=%s", speech_id)
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
        "generate_feedback: argument map loaded | num_arguments=%d | speech_id=%s",
        len(arguments),
        speech_id,
    )

    # 3.5. Compute report fingerprint for deterministic scoring
    logger.info("generate_feedback: stage=compute_fingerprint | speech_id=%s", speech_id)
    report_fingerprint = compute_report_fingerprint(
        transcript_text=transcript_text,
        speech_type=speech.get("speech_type", ""),
        argument_map=arguments,
    )

    # Check if report already exists and is current
    try:
        existing_report = (
            supabase.table("feedback_reports")
            .select("id, report_input_hash, scoring_version, last_regenerated_at")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )

        if existing_report.data:
            existing = existing_report.data[0]

            # Check if report is current (same inputs + same scoring version)
            if (
                existing.get("report_input_hash") == report_fingerprint
                and existing.get("scoring_version") == SCORING_VERSION
            ):
                # Report is current - check cooldown
                last_regen = existing.get("last_regenerated_at")
                if last_regen:
                    try:
                        last_regen_dt = datetime.fromisoformat(last_regen.replace("Z", "+00:00"))
                        elapsed = (datetime.now(timezone.utc) - last_regen_dt).total_seconds()
                        if elapsed < REGENERATE_COOLDOWN_SECONDS:
                            raise HTTPException(
                                status_code=429,
                                detail=f"Report was regenerated {int(elapsed)}s ago. Please wait {REGENERATE_COOLDOWN_SECONDS - int(elapsed)}s before regenerating again.",
                            )
                    except (ValueError, TypeError):
                        pass  # Invalid timestamp, allow regeneration

                logger.info(
                    "generate_feedback: report is current but regenerating explanation | speech_id=%s",
                    speech_id,
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "generate_feedback: existing report check failed | exc_type=%s", type(exc).__name__
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
    logger.info("generate_feedback: stage=generate_llm_feedback | speech_id=%s", speech_id)
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

    # 6. Calculate deterministic scores (LLM explains; rubric engine scores)
    try:
        logger.info("generate_feedback: stage=calculate_deterministic_scores | speech_id=%s", speech_id)
        # Use deterministic scoring engine instead of trusting LLM scores
        # This prevents score-shopping via repeated regeneration
        deterministic_scores = calculate_rubric_scores(
            speech_type=speech.get("speech_type", ""),
            transcript_text=transcript_text,
            argument_map=arguments,
            word_count=word_count,
        )

        # Log if LLM scores differ significantly from deterministic scores
        llm_score_sum = sum(
            expl.score for expl in output.score_explanations
        ) if output.score_explanations else 0
        deterministic_score_sum = sum(deterministic_scores.values())

        if abs(llm_score_sum - deterministic_score_sum) > 15:
            logger.warning(
                "generate_feedback: LLM score (%d) differs from deterministic (%d) by %d | speech_id=%s",
                llm_score_sum,
                deterministic_score_sum,
                abs(llm_score_sum - deterministic_score_sum),
                speech_id,
            )

        # Overall score is computed from deterministic rubric dimensions, not from the LLM.
        # This ensures the overall score is stable across regenerations.
        derived_score = deterministic_score_sum

        logger.info("generate_feedback: stage=map_legacy_scores | speech_id=%s", speech_id)
        # Map deterministic rubric dimensions to legacy 5-dimension schema for backward compatibility
        # This ensures the frontend displays the correct scores that add up to overall_score
        legacy_scores = _map_rubric_to_legacy_scores(deterministic_scores, speech.get("speech_type", ""))

        logger.info("generate_feedback: stage=build_report_payload | speech_id=%s", speech_id)
        # Store deterministic scores and metadata in raw_feedback
        raw = output.model_dump()
        raw["overall_score"] = derived_score
        raw["deterministic_scores"] = deterministic_scores
        raw["scoring_version"] = SCORING_VERSION
        raw["report_input_hash"] = report_fingerprint

        # Build base feedback data payload
        feedback_data = {
            "speech_id": speech_id,
            "overall_score": derived_score,
            "scores": legacy_scores,  # Legacy 5-dimension schema mapped from deterministic scores
            "summary": output.summary,
            "strengths": output.strengths,
            "weaknesses": output.weaknesses,
            "raw_feedback": raw,
        }

        logger.info("generate_feedback: stage=save_feedback_report | speech_id=%s", speech_id)
        # Try to save with new fields first (if migration applied)
        try:
            feedback_data_with_new_fields = {
                **feedback_data,
                "scoring_version": SCORING_VERSION,
                "report_input_hash": report_fingerprint,
                "last_regenerated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z",
            }
            result = (
                supabase.table("feedback_reports")
                .upsert(feedback_data_with_new_fields, on_conflict="speech_id")
                .execute()
            )
            logger.info("generate_feedback: saved with new fields | speech_id=%s", speech_id)
        except Exception as schema_exc:
            # If new fields don't exist, fall back to base payload
            logger.warning(
                "generate_feedback: new columns not in schema, using base payload | exc=%s | speech_id=%s",
                str(schema_exc),
                speech_id,
            )
            logger.warning(
                "generate_feedback: Apply migration 20260604000000_add_xp_ledger.sql to enable deterministic scoring features"
            )
            result = (
                supabase.table("feedback_reports")
                .upsert(feedback_data, on_conflict="speech_id")
                .execute()
            )
            logger.info("generate_feedback: saved with base payload | speech_id=%s", speech_id)

        logger.info("generate_feedback: stage=update_speech_status | speech_id=%s", speech_id)
        supabase.table("speeches").update({"status": "done"}).eq("id", speech_id).execute()

        logger.info("generate_feedback: done | speech_id=%s overall_score=%d", speech_id, derived_score)
        return result.data[0]
    except Exception as exc:
        logger.error(
            "generate_feedback: stage=upsert_failed | exc_type=%s | exc_msg=%s | speech_id=%s",
            type(exc).__name__,
            str(exc),
            speech_id,
            exc_info=True,
        )
        _set_error_status()
        raise HTTPException(
            status_code=500,
            detail=f"Feedback generation failed at save stage. Error: {type(exc).__name__}"
        ) from exc


@router.get("/{speech_id}/feedback", response_model=FeedbackReportRow)
async def get_feedback(speech_id: str, user_id: str = Query(...)) -> FeedbackReportRow:
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

    # Fetch feedback report
    try:
        result = (
            supabase.table("feedback_reports")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=404, detail="No feedback report found for this speech"
            )

        # Defensively recompute overall_score from stored scores to ensure consistency
        report = result.data[0]
        if report.get("scores"):
            scores = report["scores"]
            recomputed_overall = (
                scores.get("clash", 0)
                + scores.get("weighing", 0)
                + scores.get("extensions", 0)
                + scores.get("drops", 0)
                + scores.get("judge_adaptation", 0)
            )
            # If stored overall_score doesn't match, use recomputed value
            if report.get("overall_score") != recomputed_overall:
                logger.warning(
                    "get_feedback: overall_score mismatch | speech_id=%s stored=%s recomputed=%s",
                    speech_id,
                    report.get("overall_score"),
                    recomputed_overall,
                )
                report["overall_score"] = recomputed_overall

        return report
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch feedback report") from exc


@router.patch("/{speech_id}/feedback/rating", response_model=FeedbackReportRow)
async def update_feedback_rating(
    speech_id: str, body: FeedbackRatingUpdate, user_id: str = Query(...)
) -> FeedbackReportRow:
    """Update the helpful_rating for a feedback report.

    Only the speech owner can rate their own feedback.
    """
    supabase = get_supabase()

    # 1. Verify speech ownership
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

    # 2. Update feedback rating
    valid_ratings = {"helpful", "not_helpful"}
    if body.helpful_rating not in valid_ratings:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating. Must be one of: {', '.join(valid_ratings)}",
        )

    try:
        result = (
            supabase.table("feedback_reports")
            .update({"helpful_rating": body.helpful_rating})
            .eq("speech_id", speech_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Feedback report not found")
        logger.info(
            "update_feedback_rating: success | speech_id=%s rating=%s",
            speech_id,
            body.helpful_rating,
        )
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "update_feedback_rating: failed | exc_type=%s", type(exc).__name__
        )
        raise HTTPException(status_code=500, detail="Failed to update feedback rating") from exc
