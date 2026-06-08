import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.speech import SpeechCreateRequest, SpeechRow, SpeechUpdateRequest
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
        summary=_build_comparison_summary(overall_delta, source_drill_skill, skill_delta),
        still_needs_work=still_needs_work,
        next_action=_derive_next_action(overall_delta),
    )
