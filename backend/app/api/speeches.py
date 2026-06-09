import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.models.job import AnalyzeResponse
from app.models.speech import SpeechCreateRequest, SpeechRow, SpeechUpdateRequest
from app.services.jobs import create_job, list_jobs_for_speech
from app.services.product_events import track_product_event
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["speeches"])


@router.post("", response_model=SpeechRow, status_code=201)
async def create_speech(body: SpeechCreateRequest) -> SpeechRow:
    try:
        row: dict = {
            "user_id": body.user_id,
            "title": body.title,
            "speech_type": body.speech_type,
            "side": body.side,
            "judge_type": body.judge_type,
            "topic": body.topic,
            "status": "pending",
        }
        if body.parent_speech_id:
            row["parent_speech_id"] = body.parent_speech_id
        if body.source_drill_id:
            row["source_drill_id"] = body.source_drill_id
        result = (
            get_supabase()
            .table("speeches")
            .insert(row)
            .execute()
        )
        speech = result.data[0]
        is_rerecord = bool(body.parent_speech_id)
        track_product_event(
            user_id=body.user_id,
            event_name="rerecord_started" if is_rerecord else "speech_created",
            speech_id=speech["id"],
            metadata={"is_rerecord": is_rerecord},
        )
        return speech
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


# ── Unified analysis endpoint (job-backed) ────────────────────────────────────

@router.post("/{speech_id}/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze_speech(
    speech_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Query(...),
) -> AnalyzeResponse:
    """
    Kick off the full speech analysis pipeline as a background job.

    Returns {job_id, status} immediately so the client can start polling
    GET /jobs/{job_id}. The pipeline runs: transcribe → extract flow →
    generate feedback → generate drills.

    If a queued or running job already exists for this speech it is returned
    instead of creating a duplicate.
    """
    from app.services.analysis_pipeline import run_speech_analysis_pipeline

    supabase = get_supabase()

    # Verify speech ownership
    try:
        speech_res = (
            supabase.table("speeches")
            .select("id, audio_url")
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

    # Check whether there's already a transcript (paste flow) or audio
    has_audio = bool(speech.get("audio_url"))
    tx_check = (
        supabase.table("transcripts")
        .select("id")
        .eq("speech_id", speech_id)
        .limit(1)
        .execute()
    )
    has_transcript = bool(tx_check.data)

    if not has_audio and not has_transcript:
        raise HTTPException(
            status_code=400,
            detail="Upload audio or paste a transcript before running analysis.",
        )

    # Return existing active job if one is already in flight
    try:
        existing = list_jobs_for_speech(supabase, speech_id, user_id, limit=1)
        for j in existing:
            if j["status"] in ("queued", "running"):
                return AnalyzeResponse(job_id=j["id"], status=j["status"])
    except Exception:
        pass  # Best-effort dedup; proceed to create a new job

    # Create job and enqueue background task
    try:
        job = create_job(
            supabase,
            user_id=user_id,
            job_type="speech_analysis",
            speech_id=speech_id,
        )
    except Exception as exc:
        logger.error(
            "analyze_speech: create_job failed | exc_type=%s | speech_id=%s",
            type(exc).__name__, speech_id,
        )
        raise HTTPException(status_code=500, detail="Failed to create analysis job") from exc

    background_tasks.add_task(
        run_speech_analysis_pipeline,
        job["id"],
        speech_id,
        user_id,
    )
    logger.info(
        "analyze_speech: job queued | job_id=%s speech_id=%s", job["id"], speech_id
    )
    return AnalyzeResponse(job_id=job["id"], status="queued")


# ── Speech comparison (re-record improvement) ─────────────────────────────────

class SpeechComparisonResponse(BaseModel):
    has_parent: bool
    parent_speech_id: Optional[str] = None
    source_drill_id: Optional[str] = None
    source_drill_skill: Optional[str] = None
    original_overall_score: Optional[int] = None
    new_overall_score: Optional[int] = None
    overall_delta: Optional[int] = None
    original_skill_score: Optional[int] = None
    new_skill_score: Optional[int] = None
    skill_delta: Optional[int] = None
    # Delivery deltas — optional, only present when both speeches have delivery metrics
    original_delivery_score: Optional[int] = None
    new_delivery_score: Optional[int] = None
    delivery_score_delta: Optional[int] = None
    original_wpm: Optional[float] = None
    new_wpm: Optional[float] = None
    wpm_delta: Optional[float] = None
    original_filler_count: Optional[int] = None
    new_filler_count: Optional[int] = None
    filler_delta: Optional[int] = None
    summary: str
    still_needs_work: Optional[str] = None
    next_action: str


# Maps drill skill_target → the feedback_report scores field it most directly affects
_SKILL_TO_SCORE_FIELD: dict[str, str] = {
    "weighing": "weighing",
    "warranting": "clash",
    "drops": "drops",
    "extensions": "extensions",
    "evidence": "drops",
    "clash": "clash",
    "judge_adaptation": "judge_adaptation",
    "collapse": "extensions",
    "line_by_line": "drops",
}


def _build_comparison_summary(
    overall_delta: int | None,
    skill: str | None,
    skill_delta: int | None,
) -> str:
    parts: list[str] = []
    if overall_delta is not None:
        if overall_delta > 5:
            parts.append(f"Strong improvement — overall score up {overall_delta} points after the drill.")
        elif overall_delta > 0:
            parts.append(f"Score improved by {overall_delta} point{'s' if overall_delta != 1 else ''} after the drill.")
        elif overall_delta == 0:
            parts.append("Score held steady — your drill work is consolidating.")
        else:
            parts.append(f"Score dipped by {abs(overall_delta)} — that can happen while internalizing new technique.")
    if skill and skill_delta is not None and overall_delta is not None:
        skill_label = skill.replace("_", " ")
        if skill_delta > 0:
            parts.append(f"Your {skill_label} score also improved by {skill_delta}.")
        elif skill_delta < 0:
            parts.append(f"Your {skill_label} score slipped — focus there next.")
    elif skill and skill_delta is not None:
        direction = "improved" if skill_delta > 0 else ("held steady" if skill_delta == 0 else "dipped")
        parts.append(f"Your {skill.replace('_', ' ')} {direction} after the drill.")
    return " ".join(parts) if parts else "Report comparison is ready — compare the two to see what changed."


def _derive_next_action(overall_delta: int | None) -> str:
    if overall_delta is not None and overall_delta >= 5:
        return "Great progress — consider moving to the next skill drill."
    if overall_delta is not None and overall_delta > 0:
        return "Keep practicing — one more rep of this drill will reinforce the skill."
    return "Record another drill rep, then re-record the speech to track improvement."


@router.get("/{speech_id}/comparison", response_model=SpeechComparisonResponse)
async def get_speech_comparison(speech_id: str, user_id: str = Query(...)) -> SpeechComparisonResponse:
    """Return a deterministic score comparison between a re-recorded speech and its parent."""
    supabase = get_supabase()

    # Fetch the re-recorded speech (verify ownership)
    try:
        speech_res = (
            supabase.table("speeches")
            .select("parent_speech_id, source_drill_id")
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
    parent_speech_id: str | None = speech.get("parent_speech_id")
    source_drill_id: str | None = speech.get("source_drill_id")

    if not parent_speech_id:
        return SpeechComparisonResponse(
            has_parent=False,
            summary="This speech has no original to compare against.",
            next_action="Record a speech and complete a drill to begin the improvement loop.",
        )

    # Fetch both feedback reports — best-effort, don't 500 on missing data
    new_fb: dict | None = None
    orig_fb: dict | None = None
    try:
        r = (
            supabase.table("feedback_reports")
            .select("overall_score, scores, weaknesses")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        new_fb = r.data[0] if r.data else None
    except Exception:
        pass

    try:
        r = (
            supabase.table("feedback_reports")
            .select("overall_score, scores, weaknesses")
            .eq("speech_id", parent_speech_id)
            .limit(1)
            .execute()
        )
        orig_fb = r.data[0] if r.data else None
    except Exception:
        pass

    # Fetch source drill skill — best-effort
    source_drill_skill: str | None = None
    try:
        if source_drill_id:
            r = (
                supabase.table("drills")
                .select("skill_target")
                .eq("id", source_drill_id)
                .limit(1)
                .execute()
            )
            if r.data:
                source_drill_skill = r.data[0].get("skill_target")
    except Exception:
        pass

    # Compute overall deltas
    orig_score: int | None = (orig_fb or {}).get("overall_score")
    new_score: int | None = (new_fb or {}).get("overall_score")
    overall_delta = (new_score - orig_score) if orig_score is not None and new_score is not None else None

    # Compute targeted-skill delta
    score_field = _SKILL_TO_SCORE_FIELD.get(source_drill_skill or "")
    orig_skill_score: int | None = None
    new_skill_score: int | None = None
    skill_delta: int | None = None
    if score_field:
        orig_scores: dict = (orig_fb or {}).get("scores") or {}
        new_scores: dict = (new_fb or {}).get("scores") or {}
        orig_skill_score = orig_scores.get(score_field)
        new_skill_score = new_scores.get(score_field)
        if orig_skill_score is not None and new_skill_score is not None:
            skill_delta = new_skill_score - orig_skill_score

    new_weaknesses: list = (new_fb or {}).get("weaknesses") or []
    still_needs_work = new_weaknesses[0] if new_weaknesses else None

    # Fetch delivery metric deltas — best-effort, non-blocking
    orig_delivery_score: int | None = None
    new_delivery_score: int | None = None
    delivery_score_delta: int | None = None
    orig_wpm: float | None = None
    new_wpm: float | None = None
    wpm_delta: float | None = None
    orig_filler_count: int | None = None
    new_filler_count: int | None = None
    filler_delta: int | None = None

    try:
        dm_new_res = (
            supabase.table("delivery_metrics")
            .select("delivery_score, words_per_minute, filler_word_count")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if dm_new_res.data:
            dm_new = dm_new_res.data[0]
            new_delivery_score = dm_new.get("delivery_score")
            new_wpm = dm_new.get("words_per_minute")
            new_filler_count = dm_new.get("filler_word_count")

        dm_orig_res = (
            supabase.table("delivery_metrics")
            .select("delivery_score, words_per_minute, filler_word_count")
            .eq("speech_id", parent_speech_id)
            .limit(1)
            .execute()
        )
        if dm_orig_res.data:
            dm_orig = dm_orig_res.data[0]
            orig_delivery_score = dm_orig.get("delivery_score")
            orig_wpm = dm_orig.get("words_per_minute")
            orig_filler_count = dm_orig.get("filler_word_count")

        if orig_delivery_score is not None and new_delivery_score is not None:
            delivery_score_delta = new_delivery_score - orig_delivery_score
        if orig_wpm is not None and new_wpm is not None:
            wpm_delta = round(new_wpm - orig_wpm, 1)
        if orig_filler_count is not None and new_filler_count is not None:
            filler_delta = new_filler_count - orig_filler_count
    except Exception:
        pass

    return SpeechComparisonResponse(
        has_parent=True,
        parent_speech_id=parent_speech_id,
        source_drill_id=source_drill_id,
        source_drill_skill=source_drill_skill,
        original_overall_score=orig_score,
        new_overall_score=new_score,
        overall_delta=overall_delta,
        original_skill_score=orig_skill_score,
        new_skill_score=new_skill_score,
        skill_delta=skill_delta,
        original_delivery_score=orig_delivery_score,
        new_delivery_score=new_delivery_score,
        delivery_score_delta=delivery_score_delta,
        original_wpm=orig_wpm,
        new_wpm=new_wpm,
        wpm_delta=wpm_delta,
        original_filler_count=orig_filler_count,
        new_filler_count=new_filler_count,
        filler_delta=filler_delta,
        summary=_build_comparison_summary(overall_delta, source_drill_skill, skill_delta),
        still_needs_work=still_needs_work,
        next_action=_derive_next_action(overall_delta),
    )


# ── Delivery metrics ───────────────────────────────────────────────────────────

class DeliveryMetricsRow(BaseModel):
    id: Optional[str] = None
    speech_id: str
    user_id: str
    word_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    words_per_minute: Optional[float] = None
    filler_word_count: Optional[int] = None
    filler_words_json: Optional[dict] = None
    repeated_phrases_json: Optional[list] = None
    long_sentence_count: Optional[int] = None
    average_sentence_words: Optional[float] = None
    delivery_score: Optional[int] = None
    pacing_band: Optional[str] = None
    clarity_flags_json: Optional[list] = None
    timeline_json: Optional[list] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/{speech_id}/delivery-metrics", response_model=DeliveryMetricsRow)
async def get_delivery_metrics(
    speech_id: str,
    user_id: str = Query(...),
) -> DeliveryMetricsRow:
    """Fetch delivery metrics for a speech. Returns 404 if not yet computed."""
    supabase = get_supabase()

    # Verify ownership
    try:
        sp = (
            supabase.table("speeches")
            .select("id")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc
    if not sp.data:
        raise HTTPException(status_code=404, detail="Speech not found")

    try:
        res = (
            supabase.table("delivery_metrics")
            .select("*")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch delivery metrics") from exc

    if not res.data:
        raise HTTPException(status_code=404, detail="Delivery metrics not yet available")

    return DeliveryMetricsRow(**res.data[0])


@router.post("/{speech_id}/delivery-metrics/recompute", response_model=DeliveryMetricsRow)
async def recompute_delivery_metrics(
    speech_id: str,
    user_id: str = Query(...),
) -> DeliveryMetricsRow:
    """Recompute delivery metrics from the stored transcript and speech duration."""
    from app.services.delivery_analysis import analyze_delivery

    supabase = get_supabase()

    # Verify ownership and fetch speech
    try:
        sp_res = (
            supabase.table("speeches")
            .select("id, duration_seconds")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch speech") from exc
    if not sp_res.data:
        raise HTTPException(status_code=404, detail="Speech not found")

    speech = sp_res.data[0]

    # Fetch transcript
    try:
        tx_res = (
            supabase.table("transcripts")
            .select("text")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch transcript") from exc
    if not tx_res.data:
        raise HTTPException(status_code=404, detail="Transcript not yet available")

    transcript_text = tx_res.data[0]["text"]
    duration = speech.get("duration_seconds")

    try:
        dm = analyze_delivery(transcript_text, duration_seconds=duration)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Delivery analysis failed") from exc

    payload = {
        "speech_id": speech_id,
        "user_id": user_id,
        **dm.model_dump(),
    }

    try:
        result = (
            supabase.table("delivery_metrics")
            .upsert(payload, on_conflict="speech_id")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to save delivery metrics") from exc

    return DeliveryMetricsRow(**result.data[0])
