"""
Shared coach report endpoints.

Privacy model:
  - Share links are private by default; created only on explicit user action.
  - GET /shared-reports/{token} is the only unauthenticated endpoint; it serves
    a sanitized payload with no user IDs, audio URLs, or storage paths.
  - Evidence document contents are never included; only a summary of support levels.
  - Share links can be revoked by the owner at any time.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.models.shared_report import (
    CreateShareRequest,
    SharedReportArgument,
    SharedReportComparison,
    SharedReportDelivery,
    SharedReportEvidenceSummary,
    SharedReportFeedback,
    SharedReportIncludeFlags,
    SharedReportPayload,
    ShareResponse,
    UpdateShareRequest,
)
from app.services.product_events import track_product_event
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shared_reports"])

_TOKEN_BYTES = 32  # 43 URL-safe characters — not guessable


def _make_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _row_to_share_response(row: dict) -> ShareResponse:
    return ShareResponse(
        id=row["id"],
        share_token=row["share_token"],
        include_transcript=row["include_transcript"],
        include_flow=row["include_flow"],
        include_feedback=row["include_feedback"],
        include_drills=row["include_drills"],
        include_delivery=row["include_delivery"],
        include_evidence_summary=row["include_evidence_summary"],
        include_improvement=row["include_improvement"],
        expires_at=row.get("expires_at"),
        revoked_at=row.get("revoked_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ── Owner endpoints ────────────────────────────────────────────────────────────

@router.post("/speeches/{speech_id}/share", response_model=ShareResponse, status_code=200)
async def create_or_update_share(speech_id: str, body: CreateShareRequest) -> ShareResponse:
    """Create a share link for a completed speech, or update settings on an existing one."""
    sb = get_supabase()

    # Verify ownership + completed status
    try:
        speech_res = (
            sb.table("speeches")
            .select("id, status")
            .eq("id", speech_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify speech") from exc

    if not speech_res.data:
        raise HTTPException(status_code=404, detail="Speech not found")
    if speech_res.data[0]["status"] != "done":
        raise HTTPException(status_code=400, detail="Speech must have a completed report before sharing")

    expires_at: Optional[str] = None
    if body.expires_in_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()

    include_payload = {
        "include_transcript": body.include_transcript,
        "include_flow": body.include_flow,
        "include_feedback": body.include_feedback,
        "include_drills": body.include_drills,
        "include_delivery": body.include_delivery,
        "include_evidence_summary": body.include_evidence_summary,
        "include_improvement": body.include_improvement,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Check for existing active (non-revoked) share
    try:
        existing_res = (
            sb.table("shared_reports")
            .select("*")
            .eq("speech_id", speech_id)
            .eq("user_id", body.user_id)
            .is_("revoked_at", "null")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to query existing share") from exc

    if existing_res.data:
        # Update settings on existing share
        try:
            result = (
                sb.table("shared_reports")
                .update(include_payload)
                .eq("id", existing_res.data[0]["id"])
                .execute()
            )
            row = result.data[0]
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to update share") from exc
    else:
        # Create a fresh share
        try:
            new_row = {
                "speech_id": speech_id,
                "user_id": body.user_id,
                "share_token": _make_token(),
                **include_payload,
            }
            new_row.pop("updated_at", None)  # not needed on insert
            result = sb.table("shared_reports").insert(new_row).execute()
            row = result.data[0]
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to create share") from exc

    track_product_event(
        user_id=body.user_id,
        event_name="share_report_created",
        speech_id=speech_id,
    )
    return _row_to_share_response(row)


@router.get("/speeches/{speech_id}/share", response_model=Optional[ShareResponse])
async def get_share(speech_id: str, user_id: str) -> Optional[ShareResponse]:
    """Return the active share settings for the owner, or null if none exists."""
    sb = get_supabase()

    try:
        speech_res = (
            sb.table("speeches")
            .select("id")
            .eq("id", speech_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to verify speech") from exc
    if not speech_res.data:
        raise HTTPException(status_code=404, detail="Speech not found")

    try:
        res = (
            sb.table("shared_reports")
            .select("*")
            .eq("speech_id", speech_id)
            .eq("user_id", user_id)
            .is_("revoked_at", "null")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to query share") from exc

    if not res.data:
        return None
    return _row_to_share_response(res.data[0])


@router.patch("/shared-reports/{share_id}", response_model=ShareResponse)
async def update_share(share_id: str, body: UpdateShareRequest) -> ShareResponse:
    """Owner updates include flags or expiration on an existing share."""
    sb = get_supabase()

    try:
        existing = (
            sb.table("shared_reports")
            .select("*")
            .eq("id", share_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch share") from exc
    if not existing.data:
        raise HTTPException(status_code=404, detail="Share not found")

    update: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.include_transcript is not None:
        update["include_transcript"] = body.include_transcript
    if body.include_flow is not None:
        update["include_flow"] = body.include_flow
    if body.include_feedback is not None:
        update["include_feedback"] = body.include_feedback
    if body.include_drills is not None:
        update["include_drills"] = body.include_drills
    if body.include_delivery is not None:
        update["include_delivery"] = body.include_delivery
    if body.include_evidence_summary is not None:
        update["include_evidence_summary"] = body.include_evidence_summary
    if body.include_improvement is not None:
        update["include_improvement"] = body.include_improvement
    if body.expires_in_days is not None:
        update["expires_at"] = (
            (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat()
            if body.expires_in_days > 0
            else None
        )

    try:
        result = sb.table("shared_reports").update(update).eq("id", share_id).execute()
        return _row_to_share_response(result.data[0])
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update share") from exc


@router.delete("/shared-reports/{share_id}", status_code=200)
async def revoke_share(share_id: str, user_id: str) -> dict:
    """Owner revokes a share link by setting revoked_at."""
    sb = get_supabase()

    try:
        existing = (
            sb.table("shared_reports")
            .select("id, speech_id")
            .eq("id", share_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch share") from exc
    if not existing.data:
        raise HTTPException(status_code=404, detail="Share not found")

    try:
        sb.table("shared_reports").update({
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", share_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to revoke share") from exc

    track_product_event(
        user_id=user_id,
        event_name="share_report_revoked",
        speech_id=existing.data[0].get("speech_id"),
    )
    return {"revoked": True}


# ── Public read endpoint ───────────────────────────────────────────────────────

@router.get("/shared-reports/{token}", response_model=SharedReportPayload)
async def get_shared_report(token: str) -> SharedReportPayload:
    """Public endpoint: return a sanitized coach report by share token.

    No authentication required. Returns 410 if revoked or expired.
    Never exposes user IDs, audio URLs, storage paths, or full evidence documents.
    """
    sb = get_supabase()

    # 1. Look up token
    try:
        share_res = (
            sb.table("shared_reports")
            .select("*")
            .eq("share_token", token)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to look up share token") from exc
    if not share_res.data:
        raise HTTPException(status_code=404, detail="Report not found")

    share = share_res.data[0]

    # 2. Check revoked
    if share.get("revoked_at"):
        raise HTTPException(status_code=410, detail="This report link has been revoked")

    # 3. Check expired
    if share.get("expires_at"):
        try:
            exp = datetime.fromisoformat(str(share["expires_at"]).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(status_code=410, detail="This report link has expired")
        except HTTPException:
            raise
        except Exception:
            pass  # malformed expiry — allow access rather than block

    speech_id: str = share["speech_id"]

    # 4. Load speech metadata (no audio_url, no user_id in response)
    try:
        speech_res = (
            sb.table("speeches")
            .select("speech_type, side, judge_type, topic, created_at, parent_speech_id, status")
            .eq("id", speech_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load speech") from exc
    if not speech_res.data:
        raise HTTPException(status_code=404, detail="Source speech no longer exists")

    speech = speech_res.data[0]

    # 5. Build flags
    flags = SharedReportIncludeFlags(
        transcript=share["include_transcript"],
        flow=share["include_flow"],
        feedback=share["include_feedback"],
        drills=share["include_drills"],
        delivery=share["include_delivery"],
        evidence_summary=share["include_evidence_summary"],
        improvement=share["include_improvement"],
    )

    # 6. Load each included section (best-effort — missing data returns None)
    feedback_data = _load_feedback(sb, speech_id) if flags.feedback else None
    arguments_data = _load_flow(sb, speech_id) if flags.flow else None
    drills_data = _load_drills(sb, speech_id) if flags.drills else None
    delivery_data = _load_delivery(sb, speech_id) if flags.delivery else None
    transcript_text = _load_transcript(sb, speech_id) if flags.transcript else None
    evidence_summary = _load_evidence_summary(sb, speech_id) if flags.evidence_summary else None
    comparison = (
        _load_comparison(sb, speech_id, speech.get("parent_speech_id"))
        if flags.improvement and speech.get("parent_speech_id")
        else None
    )

    track_product_event(
        user_id=share["user_id"],
        event_name="shared_report_opened",
        speech_id=speech_id,
    )

    return SharedReportPayload(
        token=token,
        speech_type=speech["speech_type"],
        side=speech.get("side"),
        judge_type=speech.get("judge_type"),
        topic=speech.get("topic"),
        created_at=str(speech["created_at"]),
        feedback=feedback_data,
        arguments=arguments_data,
        drills=drills_data,
        delivery=delivery_data,
        transcript_text=transcript_text,
        evidence_summary=evidence_summary,
        comparison=comparison,
        include_flags=flags,
    )


# ── Data loaders (sanitized — no private IDs or URLs) ─────────────────────────

def _load_feedback(sb, speech_id: str) -> Optional[SharedReportFeedback]:
    try:
        res = (
            sb.table("feedback_reports")
            .select("overall_score, scores, summary, strengths, weaknesses, raw_feedback")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        r = res.data[0]
        raw = r.get("raw_feedback") or {}
        return SharedReportFeedback(
            overall_score=r.get("overall_score"),
            scores=r.get("scores"),
            summary=r.get("summary"),
            strengths=r.get("strengths") or [],
            weaknesses=r.get("weaknesses") or [],
            top_3_priorities=raw.get("top_3_priorities"),
            structured_issues=raw.get("structured_issues"),
        )
    except Exception:
        logger.warning("_load_feedback: failed for speech_id=%s", speech_id)
        return None


def _load_flow(sb, speech_id: str) -> Optional[list[SharedReportArgument]]:
    try:
        res = (
            sb.table("argument_maps")
            .select("arguments")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        raw_args = res.data[0].get("arguments") or []
        return [
            SharedReportArgument(
                label=a.get("label", ""),
                claim=a.get("claim", ""),
                warrant=a.get("warrant") or "",
                evidence=a.get("evidence"),
                impact=a.get("impact") or "",
                argument_type=a.get("argument_type", "unclear"),
            )
            for a in raw_args
        ]
    except Exception:
        logger.warning("_load_flow: failed for speech_id=%s", speech_id)
        return None


def _load_drills(sb, speech_id: str) -> Optional[list]:
    from app.models.shared_report import SharedReportDrill
    try:
        res = (
            sb.table("drills")
            .select("title, description, skill_target, prompt, success_criteria, difficulty")
            .eq("speech_id", speech_id)
            .order("order", desc=False)
            .execute()
        )
        if not res.data:
            return None
        return [
            SharedReportDrill(
                title=d["title"],
                description=d.get("description"),
                skill_target=d["skill_target"],
                prompt=d["prompt"],
                success_criteria=d.get("success_criteria") or [],
                difficulty=d.get("difficulty", "beginner"),
            )
            for d in res.data
        ]
    except Exception:
        logger.warning("_load_drills: failed for speech_id=%s", speech_id)
        return None


def _load_delivery(sb, speech_id: str) -> Optional[SharedReportDelivery]:
    try:
        res = (
            sb.table("delivery_metrics")
            .select("words_per_minute, filler_word_count, delivery_score, pacing_band, repeated_phrases_json")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        d = res.data[0]
        return SharedReportDelivery(
            words_per_minute=d.get("words_per_minute"),
            filler_word_count=d.get("filler_word_count"),
            delivery_score=d.get("delivery_score"),
            pacing_band=d.get("pacing_band"),
            repeated_phrases_json=d.get("repeated_phrases_json"),
        )
    except Exception:
        logger.warning("_load_delivery: failed for speech_id=%s", speech_id)
        return None


def _load_transcript(sb, speech_id: str) -> Optional[str]:
    try:
        res = (
            sb.table("transcripts")
            .select("text")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return res.data[0].get("text")
    except Exception:
        logger.warning("_load_transcript: failed for speech_id=%s", speech_id)
        return None


def _load_evidence_summary(sb, speech_id: str) -> Optional[SharedReportEvidenceSummary]:
    try:
        res = (
            sb.table("claim_evidence_checks")
            .select("claim_text, support_level, explanation")
            .eq("speech_id", speech_id)
            .execute()
        )
        if not res.data:
            return None
        counts = {"supported": 0, "partially_supported": 0, "unsupported": 0, "unverifiable": 0}
        top_issues: list[dict] = []
        for row in res.data:
            lvl = row.get("support_level") or "unverifiable"
            counts[lvl] = counts.get(lvl, 0) + 1
            if lvl in ("unsupported", "partially_supported"):
                top_issues.append({
                    "claim_text": row.get("claim_text", ""),
                    "support_level": lvl,
                    "explanation": row.get("explanation"),
                })
        return SharedReportEvidenceSummary(
            supported_count=counts["supported"],
            partially_supported_count=counts["partially_supported"],
            unsupported_count=counts["unsupported"],
            unverifiable_count=counts["unverifiable"],
            top_issues=top_issues[:5],  # cap at 5 for brevity
        )
    except Exception:
        logger.warning("_load_evidence_summary: failed for speech_id=%s", speech_id)
        return None


def _load_comparison(
    sb, speech_id: str, parent_speech_id: str
) -> Optional[SharedReportComparison]:
    try:
        new_fb_res = (
            sb.table("feedback_reports")
            .select("overall_score")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        orig_fb_res = (
            sb.table("feedback_reports")
            .select("overall_score")
            .eq("speech_id", parent_speech_id)
            .limit(1)
            .execute()
        )
        new_dm_res = (
            sb.table("delivery_metrics")
            .select("delivery_score, words_per_minute, filler_word_count")
            .eq("speech_id", speech_id)
            .limit(1)
            .execute()
        )
        orig_dm_res = (
            sb.table("delivery_metrics")
            .select("delivery_score, words_per_minute, filler_word_count")
            .eq("speech_id", parent_speech_id)
            .limit(1)
            .execute()
        )

        new_score = new_fb_res.data[0]["overall_score"] if new_fb_res.data else None
        orig_score = orig_fb_res.data[0]["overall_score"] if orig_fb_res.data else None
        overall_delta = (new_score - orig_score) if new_score is not None and orig_score is not None else None

        new_dm = new_dm_res.data[0] if new_dm_res.data else {}
        orig_dm = orig_dm_res.data[0] if orig_dm_res.data else {}

        new_ds = new_dm.get("delivery_score")
        orig_ds = orig_dm.get("delivery_score")
        ds_delta = (new_ds - orig_ds) if new_ds is not None and orig_ds is not None else None

        new_wpm = new_dm.get("words_per_minute")
        orig_wpm = orig_dm.get("words_per_minute")
        wpm_delta = (new_wpm - orig_wpm) if new_wpm is not None and orig_wpm is not None else None

        new_fc = new_dm.get("filler_word_count")
        orig_fc = orig_dm.get("filler_word_count")
        fc_delta = (new_fc - orig_fc) if new_fc is not None and orig_fc is not None else None

        if overall_delta is None and ds_delta is None:
            return None

        # Build summary sentence
        if overall_delta is not None and overall_delta > 0:
            summary = f"Score improved by {overall_delta} point{'s' if overall_delta != 1 else ''} after practice."
        elif overall_delta is not None and overall_delta < 0:
            summary = f"Score dipped by {abs(overall_delta)} — technique refinement in progress."
        elif overall_delta == 0:
            summary = "Score held steady after practice."
        else:
            summary = "Improvement data available — compare across metrics."

        return SharedReportComparison(
            original_overall_score=orig_score,
            new_overall_score=new_score,
            overall_delta=overall_delta,
            original_delivery_score=orig_ds,
            new_delivery_score=new_ds,
            delivery_score_delta=ds_delta,
            original_wpm=orig_wpm,
            new_wpm=new_wpm,
            wpm_delta=round(wpm_delta, 1) if wpm_delta is not None else None,
            original_filler_count=orig_fc,
            new_filler_count=new_fc,
            filler_delta=fc_delta,
            summary=summary,
        )
    except Exception:
        logger.warning("_load_comparison: failed for speech_id=%s", speech_id)
        return None
