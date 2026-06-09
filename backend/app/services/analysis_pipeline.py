"""
Speech analysis background pipeline.

run_speech_analysis_pipeline() is called as a FastAPI BackgroundTask after
POST /speeches/{id}/analyze returns the job_id to the client.

Steps (with progress milestones):
  10 %  transcribing
  25 %  delivery_analysis  (non-fatal: failure does not block the pipeline)
  35 %  extracting_flow
  60 %  generating_feedback
  82 %  generating_drills
  95 %  finalizing
  100%  done (job succeeded)

Partial-artifact tolerance:
  Each step checks whether its artifact already exists in the DB before
  running. This makes retries safe: a retry after a feedback failure will
  reuse the existing transcript + argument map.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def run_speech_analysis_pipeline(
    job_id: str,
    speech_id: str,
    user_id: str,
) -> None:
    """Full speech analysis pipeline — run as a FastAPI BackgroundTask."""
    # Local imports keep startup fast and avoid circular-import risks
    from app.services.jobs import (
        start_job,
        update_job_progress,
        complete_job,
        fail_job,
    )
    from app.services.supabase_client import get_supabase
    from app.services.transcription import (
        transcribe_speech,
        StorageDownloadError,
        AudioTooLargeError,
        OpenAITranscriptionError,
    )
    from app.services.argument_extraction import extract_arguments, ArgumentExtractionError
    from app.services.feedback_generation import generate_feedback, FeedbackGenerationError
    from app.services.drill_generation import generate_drills, DrillGenerationError
    from app.services.deterministic_scoring import (
        SCORING_VERSION,
        calculate_rubric_scores,
        compute_report_fingerprint,
        map_rubric_to_legacy_scores,
    )

    sb = get_supabase()
    start_job(sb, job_id)
    logger.info(
        "analysis_pipeline: START | job_id=%s speech_id=%s", job_id, speech_id
    )

    try:
        # ── Load speech ──────────────────────────────────────────────────────
        speech_res = (
            sb.table("speeches")
            .select("*")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not speech_res.data:
            fail_job(sb, job_id, "Speech not found.", "speech_not_found")
            return
        speech = speech_res.data[0]

        # ── Step 1: Transcription ────────────────────────────────────────────
        update_job_progress(sb, job_id, "transcribing", 10)

        tx_res = (
            sb.table("transcripts")
            .select("text, word_count")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if tx_res.data:
            transcript_text = tx_res.data[0]["text"]
            logger.info(
                "analysis_pipeline: transcript exists, skipping | speech_id=%s", speech_id
            )
        else:
            audio_url = speech.get("audio_url")
            if not audio_url:
                fail_job(
                    sb, job_id,
                    "No audio uploaded for this speech. Upload audio before running analysis.",
                    "no_audio",
                )
                return

            sb.table("speeches").update({"status": "transcribing"}).eq("id", speech_id).execute()
            try:
                text, word_count = transcribe_speech(audio_url)
            except (StorageDownloadError, AudioTooLargeError, OpenAITranscriptionError) as exc:
                fail_job(sb, job_id, str(exc), "transcription_failed")
                sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
                return
            except Exception as exc:
                logger.error(
                    "analysis_pipeline: transcription unexpected error | %s | speech_id=%s",
                    type(exc).__name__, speech_id,
                )
                fail_job(
                    sb, job_id,
                    "Transcription failed due to an unexpected error. Please try again.",
                    "transcription_failed",
                )
                sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
                return

            sb.table("transcripts").upsert(
                {"speech_id": speech_id, "text": text, "word_count": word_count},
                on_conflict="speech_id",
            ).execute()
            transcript_text = text
            logger.info(
                "analysis_pipeline: transcript saved | word_count=%d | speech_id=%s",
                word_count, speech_id,
            )

        word_count = len(transcript_text.split())
        if word_count < 20:
            fail_job(
                sb, job_id,
                f"Transcript is too short ({word_count} words). Record at least 30 seconds for analysis.",
                "transcript_too_short",
            )
            return

        # ── Step 1.5: Delivery analysis (non-fatal) ──────────────────────────
        update_job_progress(sb, job_id, "delivery_analysis", 25)
        try:
            from app.services.delivery_analysis import analyze_delivery

            dm_res = (
                sb.table("delivery_metrics")
                .select("id")
                .eq("speech_id", speech_id)
                .limit(1)
                .execute()
            )
            if not dm_res.data:
                dur = speech.get("duration_seconds")
                dm = analyze_delivery(transcript_text, duration_seconds=dur)
                sb.table("delivery_metrics").insert({
                    "speech_id": speech_id,
                    "user_id": user_id,
                    **dm.model_dump(),
                }).execute()
                logger.info(
                    "analysis_pipeline: delivery metrics saved | score=%d | speech_id=%s",
                    dm.delivery_score, speech_id,
                )
            else:
                logger.info(
                    "analysis_pipeline: delivery metrics exist, skipping | speech_id=%s", speech_id
                )
        except Exception as exc:
            logger.warning(
                "analysis_pipeline: delivery analysis failed (non-fatal) | %s | speech_id=%s",
                type(exc).__name__, speech_id,
            )

        # ── Step 2: Argument extraction ──────────────────────────────────────
        update_job_progress(sb, job_id, "extracting_flow", 35)

        map_res = (
            sb.table("argument_maps")
            .select("arguments")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if map_res.data:
            arguments: list[dict] = map_res.data[0]["arguments"]
            logger.info(
                "analysis_pipeline: argument map exists, skipping | speech_id=%s", speech_id
            )
        else:
            sb.table("speeches").update({"status": "analyzing"}).eq("id", speech_id).execute()
            try:
                items = extract_arguments(
                    text=transcript_text,
                    speech_type=speech.get("speech_type", ""),
                    side=speech.get("side"),
                    topic=speech.get("topic"),
                    judge_type=speech.get("judge_type"),
                )
            except ArgumentExtractionError as exc:
                fail_job(sb, job_id, str(exc), "extraction_failed")
                sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
                return
            except Exception as exc:
                logger.error(
                    "analysis_pipeline: extraction unexpected error | %s | speech_id=%s",
                    type(exc).__name__, speech_id,
                )
                fail_job(
                    sb, job_id,
                    "Argument extraction failed. Please try again.",
                    "extraction_failed",
                )
                sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
                return

            for idx, item in enumerate(items):
                item.id = f"arg_{idx + 1}"
            arguments = [item.model_dump() for item in items]
            sb.table("argument_maps").upsert(
                {"speech_id": speech_id, "arguments": arguments},
                on_conflict="speech_id",
            ).execute()
            logger.info(
                "analysis_pipeline: argument map saved | args=%d | speech_id=%s",
                len(arguments), speech_id,
            )

        # ── Step 3: Feedback generation ──────────────────────────────────────
        update_job_progress(sb, job_id, "generating_feedback", 60)

        fb_res = (
            sb.table("feedback_reports")
            .select("id")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if fb_res.data:
            logger.info(
                "analysis_pipeline: feedback exists, skipping | speech_id=%s", speech_id
            )
            # Still need feedback for drill generation
            fb_full = (
                sb.table("feedback_reports")
                .select("*")
                .eq("speech_id", speech_id)
                .limit(1)
                .execute()
            )
            feedback_row: dict[str, Any] = fb_full.data[0] if fb_full.data else {}
        else:
            sb.table("speeches").update({"status": "analyzing"}).eq("id", speech_id).execute()
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
                fail_job(sb, job_id, str(exc), "feedback_failed")
                sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
                return
            except Exception as exc:
                logger.error(
                    "analysis_pipeline: feedback unexpected error | %s | speech_id=%s",
                    type(exc).__name__, speech_id,
                )
                fail_job(
                    sb, job_id,
                    "Feedback generation failed. Please try again.",
                    "feedback_failed",
                )
                sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
                return

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
            raw = output.model_dump()
            raw.update({
                "overall_score": derived_score,
                "deterministic_scores": det_scores,
                "scoring_version": SCORING_VERSION,
                "report_input_hash": fingerprint,
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
                "last_regenerated_at": (
                    datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
                ),
            }
            try:
                result = (
                    sb.table("feedback_reports")
                    .upsert(feedback_data, on_conflict="speech_id")
                    .execute()
                )
            except Exception:
                # If new columns aren't in schema yet, fall back to base fields
                base: dict[str, Any] = {
                    k: v
                    for k, v in feedback_data.items()
                    if k not in ("scoring_version", "report_input_hash", "last_regenerated_at")
                }
                result = (
                    sb.table("feedback_reports")
                    .upsert(base, on_conflict="speech_id")
                    .execute()
                )
            feedback_row = result.data[0] if result.data else feedback_data
            logger.info(
                "analysis_pipeline: feedback saved | score=%d | speech_id=%s",
                derived_score, speech_id,
            )

        # ── Step 4: Drill generation (skip if drills exist) ──────────────────
        update_job_progress(sb, job_id, "generating_drills", 82)

        drills_res = (
            sb.table("drills")
            .select("id")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not drills_res.data:
            raw_fb: dict = feedback_row.get("raw_feedback") or {}
            weaknesses: list[str] = feedback_row.get("weaknesses") or []
            top_3 = raw_fb.get("top_3_priorities") or []

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
            except (DrillGenerationError, Exception) as exc:
                # Drill generation failure is non-fatal — the report is still valuable
                logger.warning(
                    "analysis_pipeline: drill generation failed (non-fatal) | %s | speech_id=%s",
                    type(exc).__name__, speech_id,
                )
                drill_items = []

            if drill_items:
                # Attempt to append one delivery drill if delivery metrics exist and no delivery drill yet
                try:
                    from app.services.drill_generation import make_delivery_drill
                    dm_check = (
                        sb.table("delivery_metrics")
                        .select("clarity_flags_json, words_per_minute, filler_word_count, word_count")
                        .eq("speech_id", speech_id)
                        .limit(1)
                        .execute()
                    )
                    already_has_delivery = any(
                        getattr(d, "skill_target", "").startswith(("pacing", "filler", "clarity", "concise", "pause"))
                        for d in drill_items
                    )
                    if dm_check.data and not already_has_delivery:
                        dm_row = dm_check.data[0]
                        delivery_drill = make_delivery_drill(
                            clarity_flags=dm_row.get("clarity_flags_json") or [],
                            wpm=dm_row.get("words_per_minute"),
                            filler_count=dm_row.get("filler_word_count") or 0,
                            word_count=dm_row.get("word_count") or 1,
                        )
                        if delivery_drill:
                            drill_items.append(delivery_drill)
                            logger.info(
                                "analysis_pipeline: delivery drill appended | skill=%s | speech_id=%s",
                                delivery_drill.skill_target, speech_id,
                            )
                except Exception as exc:
                    logger.warning(
                        "analysis_pipeline: delivery drill generation failed (non-fatal) | %s | speech_id=%s",
                        type(exc).__name__, speech_id,
                    )

                try:
                    sb.table("drills").delete().eq("speech_id", speech_id).execute()
                    rows = []
                    for i, d in enumerate(drill_items, start=1):
                        tls = getattr(d, "time_limit_seconds", None)
                        if tls is not None:
                            tls = max(30, min(300, int(tls)))
                        rows.append({
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
                    sb.table("drills").insert(rows).execute()
                    logger.info(
                        "analysis_pipeline: drills saved | count=%d | speech_id=%s",
                        len(rows), speech_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "analysis_pipeline: drill insert failed (non-fatal) | %s | speech_id=%s",
                        type(exc).__name__, speech_id,
                    )
        else:
            logger.info(
                "analysis_pipeline: drills exist, skipping | speech_id=%s", speech_id
            )

        # ── Step 5: Finalize ─────────────────────────────────────────────────
        update_job_progress(sb, job_id, "finalizing", 95)
        sb.table("speeches").update({"status": "done"}).eq("id", speech_id).execute()
        complete_job(sb, job_id)
        logger.info(
            "analysis_pipeline: DONE | job_id=%s speech_id=%s", job_id, speech_id
        )

    except Exception as exc:
        logger.error(
            "analysis_pipeline: unexpected top-level error | job_id=%s | %s",
            job_id, type(exc).__name__, exc_info=True,
        )
        try:
            fail_job(
                sb, job_id,
                "Analysis failed due to an unexpected error. Please try again.",
                "unexpected_error",
            )
            sb.table("speeches").update({"status": "error"}).eq("id", speech_id).execute()
        except Exception:
            pass
