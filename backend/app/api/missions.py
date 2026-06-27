"""Missions API — Next Mission coaching loop."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.mission import (
    CompleteMissionRequest,
    CreateAttemptRequest,
    MissionAttemptRow,
    MissionRow,
    PauseMissionRequest,
    StartMissionRequest,
)
from app.services.mission_recommender import ISSUE_TO_SKILL, recommend_mission
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["missions"])

# Statuses that count as "active" — at most one may exist per user (enforced by
# the partial unique index idx_student_missions_one_active_per_user).
_ACTIVE_STATUSES = ["ready", "in_progress", "paused"]


def _row_to_mission(row: dict) -> MissionRow:
    return MissionRow(**row)


def _row_to_attempt(row: dict) -> MissionAttemptRow:
    return MissionAttemptRow(**row)


# ── GET /missions/next ─────────────────────────────────────────────────────────

@router.get("/missions/next", response_model=Optional[MissionRow])
async def get_next_mission(user_id: str = Query(...)) -> Optional[MissionRow]:
    """
    Return the student's current active mission (ready | in_progress | paused),
    or compute a new one.  Idempotent.
    """
    sb = get_supabase()

    try:
        active_res = (
            sb.table("student_missions")
            .select("*")
            .eq("user_id", user_id)
            .in_("status", _ACTIVE_STATUSES)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if active_res.data:
            return _row_to_mission(active_res.data[0])
    except Exception as exc:
        logger.warning("mission_active_check failed: %s", exc)

    # ── Load data to compute a new recommendation ──────────────────────────────
    try:
        speech_res = (
            sb.table("speeches")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "done")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load speeches") from exc

    speeches = speech_res.data or []
    if not speeches:
        return None

    speech_ids = [s["id"] for s in speeches]

    try:
        fb_res = (
            sb.table("feedback_reports")
            .select("*")
            .in_("speech_id", speech_ids)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load feedback") from exc

    feedback_reports = fb_res.data or []
    if not feedback_reports:
        return None

    drills: list[dict] = []
    try:
        dr_res = (
            sb.table("drills")
            .select("*")
            .in_("speech_id", speech_ids)
            .neq("status", "completed")
            .order("order")
            .execute()
        )
        drills = dr_res.data or []
    except Exception:
        pass

    delivery_metrics_map: dict[str, dict] = {}
    try:
        dm_res = (
            sb.table("delivery_metrics")
            .select("*")
            .eq("speech_id", speeches[0]["id"])
            .limit(1)
            .execute()
        )
        if dm_res.data:
            delivery_metrics_map[speeches[0]["id"]] = dm_res.data[0]
    except Exception:
        pass

    coach_assignments: list[dict] = []
    try:
        tm_res = (
            sb.table("team_members")
            .select("team_id")
            .eq("user_id", user_id)
            .execute()
        )
        team_ids = [r["team_id"] for r in (tm_res.data or [])]
        if team_ids:
            assign_res = (
                sb.table("assignments")
                .select("*")
                .in_("team_id", team_ids)
                .execute()
            )
            coach_assignments = assign_res.data or []
    except Exception:
        pass

    recent_missions: list[dict] = []
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_res = (
            sb.table("student_missions")
            .select("skill")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .gte("completed_at", cutoff)
            .execute()
        )
        recent_missions = recent_res.data or []
    except Exception:
        pass

    recommendation = recommend_mission(
        user_id=user_id,
        speeches=speeches,
        feedback_reports=feedback_reports,
        drills=drills,
        delivery_metrics_map=delivery_metrics_map,
        coach_assignments=coach_assignments,
        recent_missions=recent_missions,
    )

    if not recommendation:
        return None

    now = datetime.now(timezone.utc).isoformat()
    payload = {**recommendation, "created_at": now, "updated_at": now}

    try:
        result = sb.table("student_missions").insert(payload).execute()
        if result.data:
            return _row_to_mission(result.data[0])
    except Exception as exc:
        logger.error("mission_insert failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save mission") from exc

    return None


# ── GET /missions ──────────────────────────────────────────────────────────────

@router.get("/missions", response_model=list[MissionRow])
async def list_missions(user_id: str = Query(...)) -> list[MissionRow]:
    """Return mission history (most recent first, up to 20). Includes all statuses."""
    sb = get_supabase()
    try:
        res = (
            sb.table("student_missions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load missions") from exc
    return [_row_to_mission(r) for r in (res.data or [])]


# ── GET /missions/{mission_id} ─────────────────────────────────────────────────

@router.get("/missions/{mission_id}", response_model=MissionRow)
async def get_mission(mission_id: str, user_id: str = Query(...)) -> MissionRow:
    """Return a single mission by ID."""
    sb = get_supabase()
    try:
        res = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load mission") from exc
    if not res.data:
        raise HTTPException(status_code=404, detail="Mission not found")
    return _row_to_mission(res.data[0])


# ── POST /missions/{mission_id}/start ──────────────────────────────────────────

@router.post("/missions/{mission_id}/start", response_model=MissionRow)
async def start_mission(mission_id: str, body: StartMissionRequest) -> MissionRow:
    """Mark a mission as in_progress (also resumes a paused mission)."""
    sb = get_supabase()
    try:
        res = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load mission") from exc

    if not res.data:
        raise HTTPException(status_code=404, detail="Mission not found")

    row = res.data[0]
    if row.get("status") not in ("ready", "in_progress", "paused"):
        raise HTTPException(status_code=400, detail="Mission is already completed or expired")

    now = datetime.now(timezone.utc).isoformat()
    try:
        sb.table("student_missions").update(
            {"status": "in_progress", "updated_at": now}
        ).eq("id", mission_id).execute()
        updated = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to update mission") from exc

    return _row_to_mission(updated.data[0])


# ── POST /missions/{mission_id}/attempts ───────────────────────────────────────

@router.post("/missions/{mission_id}/attempts", response_model=MissionAttemptRow)
async def create_attempt(mission_id: str, body: CreateAttemptRequest) -> MissionAttemptRow:
    """Log a drill or re-record attempt. Client submits record IDs only."""
    sb = get_supabase()

    try:
        res = (
            sb.table("student_missions")
            .select("id, user_id, status, skill, success_criteria, before_score")
            .eq("id", mission_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load mission") from exc

    if not res.data:
        raise HTTPException(status_code=404, detail="Mission not found")
    if res.data[0].get("status") == "completed":
        raise HTTPException(status_code=400, detail="Mission is already completed")

    mission_row = res.data[0]

    # Transition ready/paused → in_progress
    if mission_row.get("status") in ("ready", "paused"):
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            sb.table("student_missions").update(
                {"status": "in_progress", "updated_at": now_str}
            ).eq("id", mission_id).execute()
        except Exception:
            pass

    # Compute score_snapshot server-side from referenced drill attempt
    score_snapshot: Optional[dict] = None
    criteria_met: list[str] = []

    if body.drill_attempt_id:
        try:
            da_res = (
                sb.table("drill_attempts")
                .select("*")
                .eq("id", body.drill_attempt_id)
                .eq("user_id", body.user_id)
                .limit(1)
                .execute()
            )
            if da_res.data:
                da = da_res.data[0]
                skill = mission_row.get("skill", "")
                all_criteria = mission_row.get("success_criteria") or []
                response_text = da.get("response") or ""
                criteria_met = _evaluate_criteria_from_text(skill, response_text, all_criteria)
                if da.get("score") is not None:
                    dim = _SKILL_TO_DIM.get(skill)
                    if dim:
                        score_snapshot = {dim: round(da["score"] / 5.0, 1)}
        except Exception:
            pass

    now = datetime.now(timezone.utc).isoformat()
    payload: dict = {
        "mission_id":       mission_id,
        "user_id":          body.user_id,
        "attempt_type":     body.attempt_type,
        "drill_attempt_id": body.drill_attempt_id,
        "speech_id":        body.speech_id,
        "score_snapshot":   score_snapshot,
        "criteria_met":     criteria_met,
        "result":           "incomplete",
        "notes":            body.notes,
        "created_at":       now,
    }

    try:
        result = sb.table("mission_attempts").insert(payload).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to save attempt") from exc

    if not result.data:
        raise HTTPException(status_code=500, detail="Attempt insert returned no data")
    return _row_to_attempt(result.data[0])


# ── POST /missions/{mission_id}/complete ───────────────────────────────────────

@router.post("/missions/{mission_id}/complete", response_model=MissionRow)
async def complete_mission(mission_id: str, body: CompleteMissionRequest) -> MissionRow:
    """
    Evaluate and mark a mission complete.

    Accepts drill_id (backend finds + validates the latest qualifying attempt) OR
    rerecord_speech_id (backend validates the re-recorded speech and its report).
    All scores and outcomes are derived server-side from authoritative records.
    The request model's extra='forbid' rejects forged fields at 422.
    """
    sb = get_supabase()

    try:
        res = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load mission") from exc

    if not res.data:
        raise HTTPException(status_code=404, detail="Mission not found")

    row = res.data[0]
    if row.get("status") == "completed":
        return _row_to_mission(row)

    if not body.drill_id and not body.rerecord_speech_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide drill_id or rerecord_speech_id — "
                "completion requires evidence of a qualifying attempt."
            ),
        )

    skill = row.get("skill", "")
    # before_score is stored in rubric 0-20 scale
    before_score: dict = row.get("before_score") or {}
    all_criteria: list[str] = row.get("success_criteria") or []
    mission_created_at: str = str(row.get("created_at", ""))

    # after_score stored in same rubric 0-20 scale as before_score for display
    after_score: dict = {}
    # score_delta stored as percentage points (0-100) for normalised display
    score_delta: dict = {}
    criteria_met: list[str] = []
    completion_result = "completed"
    new_report_ref: Optional[dict] = None
    qualifying_da: Optional[dict] = None

    # ── Path 1: Drill-based completion ─────────────────────────────────────────
    if body.drill_id:
        # 1. Load latest attempt for this drill that belongs to the owner
        try:
            da_res = (
                sb.table("drill_attempts")
                .select("*")
                .eq("drill_id", body.drill_id)
                .eq("user_id", body.user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to load drill attempts") from exc

        if not da_res.data:
            raise HTTPException(
                status_code=400,
                detail="No attempt found for the specified drill — complete the drill before marking this mission done.",
            )

        qualifying_da = da_res.data[0]
        attempt_created_at: str = str(qualifying_da.get("created_at", ""))

        # 2. Verify attempt occurred after the mission was created
        if mission_created_at and attempt_created_at and attempt_created_at < mission_created_at:
            raise HTTPException(
                status_code=400,
                detail="Drill attempt predates this mission. Complete the drill after the mission was assigned.",
            )

        # 3. Verify attempt contains authoritative evidence (score, response, or audio)
        has_evidence = (
            qualifying_da.get("score") is not None
            or bool((qualifying_da.get("response") or "").strip())
            or qualifying_da.get("audio_url")
        )
        if not has_evidence:
            raise HTTPException(
                status_code=400,
                detail="Drill attempt contains no recorded response, audio, or score — complete the drill fully first.",
            )

        # 4. Verify the drill targets the mission's skill
        try:
            drill_res = (
                sb.table("drills")
                .select("skill_target")
                .eq("id", body.drill_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to load drill") from exc

        if drill_res.data:
            drill_skill = drill_res.data[0].get("skill_target", "")
            if drill_skill and drill_skill != skill:
                raise HTTPException(
                    status_code=400,
                    detail=f"Drill targets '{drill_skill}' but this mission focuses on '{skill}'.",
                )

        # 5. Verify this attempt hasn't already been used to complete another mission
        try:
            reuse_res = (
                sb.table("mission_attempts")
                .select("mission_id")
                .eq("drill_attempt_id", qualifying_da["id"])
                .neq("mission_id", mission_id)
                .execute()
            )
            if reuse_res.data:
                raise HTTPException(
                    status_code=400,
                    detail="This drill attempt has already been used to complete a different mission.",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # Non-fatal: skip reuse check if DB unavailable

        # 6. Evaluate criteria and derive after_score
        response_text = qualifying_da.get("response") or ""
        drill_score = qualifying_da.get("score")

        criteria_met = _evaluate_criteria_from_text(skill, response_text, all_criteria)

        dim = _SKILL_TO_DIM.get(skill)
        if drill_score is not None and dim:
            # Normalise drill score (0-100) to rubric scale (0-20)
            after_score[dim] = round(drill_score / 5.0, 1)

        # Compute score_delta as percentage points (0-100 scale)
        if dim and after_score.get(dim) is not None and before_score.get(dim) is not None:
            delta_pct = _to_pct(after_score[dim]) - _to_pct(before_score[dim])
            score_delta[dim] = round(delta_pct, 1)
            completion_result = _derive_completion_result(skill, before_score, after_score)
        elif criteria_met:
            fraction = len(criteria_met) / max(len(all_criteria), 1)
            completion_result = "improved" if fraction >= 0.6 else "completed"

    # ── Path 2: Re-record based completion ─────────────────────────────────────
    elif body.rerecord_speech_id:
        # 1. Load the re-recorded speech (owner check via eq user_id)
        try:
            sp_res = (
                sb.table("speeches")
                .select("id, user_id, status, created_at, parent_speech_id, speech_type")
                .eq("id", body.rerecord_speech_id)
                .eq("user_id", body.user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to load speech") from exc

        if not sp_res.data:
            raise HTTPException(status_code=400, detail="Re-recorded speech not found or does not belong to this user")

        rerecord_speech = sp_res.data[0]

        # 2. Check timing: re-record must post-date mission creation
        sp_created: str = str(rerecord_speech.get("created_at", ""))
        if mission_created_at and sp_created and sp_created < mission_created_at:
            raise HTTPException(
                status_code=400,
                detail="Re-recorded speech predates this mission — record a new speech after the mission was assigned.",
            )

        # 3. Validate it references the mission's source speech
        parent_id = rerecord_speech.get("parent_speech_id")
        source_id = row.get("source_speech_id")
        if source_id and parent_id and parent_id != source_id:
            raise HTTPException(
                status_code=400,
                detail="Re-recorded speech does not reference this mission's source speech.",
            )

        if rerecord_speech.get("status") != "done":
            raise HTTPException(
                status_code=400,
                detail="Re-recorded speech has not been analyzed yet — check back once the report is ready.",
            )

        # 4. Load feedback report
        try:
            fb_res = (
                sb.table("feedback_reports")
                .select("*")
                .eq("speech_id", body.rerecord_speech_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to load feedback report") from exc

        if not fb_res.data:
            raise HTTPException(
                status_code=400,
                detail="No feedback report found for the re-recorded speech.",
            )

        new_report_ref = fb_res.data[0]
        new_scores = new_report_ref.get("scores") or {}
        # Rubric scores are 0-20; store directly for display parity with before_score
        after_score = dict(new_scores)

        # Delivery: augment from delivery_metrics
        if skill == "delivery":
            try:
                dm_res = (
                    sb.table("delivery_metrics")
                    .select("*")
                    .eq("speech_id", body.rerecord_speech_id)
                    .limit(1)
                    .execute()
                )
                if dm_res.data:
                    dm = dm_res.data[0]
                    after_score["delivery_score"] = dm.get("delivery_score")
                    after_score["words_per_minute"] = dm.get("words_per_minute")
                    after_score["filler_word_count"] = dm.get("filler_word_count")
            except Exception:
                pass

        criteria_met = _evaluate_criteria_from_report(skill, new_report_ref, all_criteria)

        # Evaluate completion from rubric delta; normalise delta to pct
        completion_result = _derive_completion_result(skill, before_score, after_score)
        dim = _SKILL_TO_DIM.get(skill)
        if dim and after_score.get(dim) is not None and before_score.get(dim) is not None:
            score_delta[dim] = round(_to_pct(after_score[dim]) - _to_pct(before_score[dim]), 1)
        elif skill == "delivery":
            b_filler = before_score.get("filler_word_count")
            a_filler = after_score.get("filler_word_count")
            if b_filler is not None and a_filler is not None:
                score_delta["filler_word_count"] = a_filler - b_filler

    # ── Remaining issue ─────────────────────────────────────────────────────────
    remaining_issue = _compute_remaining_issue(
        skill=skill,
        new_report=new_report_ref,
        criteria_met=criteria_met,
        all_criteria=all_criteria,
    )

    now = datetime.now(timezone.utc).isoformat()

    # Record attempt (non-fatal)
    attempt_payload: dict = {
        "mission_id":       mission_id,
        "user_id":          body.user_id,
        "attempt_type":     "drill" if body.drill_id else "rerecord",
        "drill_attempt_id": qualifying_da["id"] if qualifying_da else None,
        "speech_id":        body.rerecord_speech_id,
        "score_snapshot":   after_score or None,
        "criteria_met":     criteria_met,
        "result":           "passed" if completion_result == "improved" else "incomplete",
        "notes":            None,
        "created_at":       now,
    }
    try:
        sb.table("mission_attempts").insert(attempt_payload).execute()
    except Exception:
        pass

    # Persist completion — all authoritative fields computed server-side
    patch: dict = {
        "status":            "completed",
        "completion_result": completion_result,
        "after_score":       after_score or None,
        "score_delta":       score_delta or None,
        "remaining_issue":   remaining_issue,
        "completed_at":      now,
        "updated_at":        now,
    }

    try:
        sb.table("student_missions").update(patch).eq("id", mission_id).execute()
        updated = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to complete mission") from exc

    # Emit mastery evidence for the completed mission (best-effort, non-fatal)
    try:
        from app.services.mastery_integration import emit_from_mission_completion
        dim = _SKILL_TO_DIM.get(skill, skill)
        after_raw = float((after_score or {}).get(dim, 0))
        delta_raw = float((score_delta or {}).get(dim, 0))
        emit_from_mission_completion(
            supabase=sb,
            user_id=body.user_id,
            mission_id=mission_id,
            skill=skill,
            score_delta_pct=delta_raw,
            after_score_raw=after_raw,
        )
    except Exception:
        pass

    return _row_to_mission(updated.data[0])


# ── POST /missions/{mission_id}/pause ──────────────────────────────────────────

@router.post("/missions/{mission_id}/pause", response_model=MissionRow)
async def pause_mission(mission_id: str, body: PauseMissionRequest) -> MissionRow:
    """
    Save progress without completing.  Sets status to 'paused' (included in the
    partial unique index, so the student still cannot start a second active mission).
    A 'progress_save' attempt is logged for the audit trail.
    """
    sb = get_supabase()

    try:
        res = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load mission") from exc

    if not res.data:
        raise HTTPException(status_code=404, detail="Mission not found")

    row = res.data[0]
    if row.get("status") == "completed":
        return _row_to_mission(row)

    now = datetime.now(timezone.utc).isoformat()

    # Log progress_save attempt
    attempt_payload: dict = {
        "mission_id":   mission_id,
        "user_id":      body.user_id,
        "attempt_type": "progress_save",
        "result":       "incomplete",
        "criteria_met": [],
        "created_at":   now,
    }
    if body.note:
        attempt_payload["notes"] = body.note

    try:
        sb.table("mission_attempts").insert(attempt_payload).execute()
    except Exception:
        pass

    # Set status to 'paused' (still counts as active in unique index)
    try:
        sb.table("student_missions").update(
            {"status": "paused", "updated_at": now}
        ).eq("id", mission_id).execute()
    except Exception:
        pass

    try:
        updated = (
            sb.table("student_missions")
            .select("*")
            .eq("id", mission_id)
            .limit(1)
            .execute()
        )
        if updated.data:
            return _row_to_mission(updated.data[0])
    except Exception:
        pass

    return _row_to_mission(row)


# ── Helpers ────────────────────────────────────────────────────────────────────

# Rubric dimension scores are 0-20; drill scores arrive as 0-100.
# before_score / after_score are stored in rubric 0-20 scale.
# score_delta is stored as percentage points (0-100) for normalised display.
_SKILL_TO_DIM: dict[str, str] = {
    "weighing":         "weighing",
    "extensions":       "extensions",
    "drops":            "drops",
    "clash":            "clash",
    "judge_adaptation": "judge_adaptation",
}

_SKILL_CRITERIA_SIGNALS: dict[str, list[str]] = {
    "warranting":     ["because", "this means", "which means", "therefore",
                       "causes", "leads to", "results in", "mechanism"],
    "weighing":       ["outweigh", "bigger", "larger", "more likely", "faster",
                       "magnitude", "timeframe", "probability", "reversib", "vote"],
    "extensions":     ["extend", "their response", "even if", "warrant",
                       "impact", "off their"],
    "drops":          ["their", "they say", "they argue", "off their",
                       "response", "no warrant", "deny"],
    "evidence_use":   ["according to", "card", "source", "cite",
                       "evidence", "proves", "demonstrates"],
    "clash":          ["they say", "they argue", "their argument",
                       "turn", "deny", "reject", "even if", "no link"],
    "organization":   ["first", "second", "third", "next",
                       "finally", "off their", "number"],
}

_FAILURE_ISSUE_MAP: dict[str, set[str]] = {
    "warranting":     {"missing_warrant"},
    "weighing":       {"no_weighing", "unclear_impact"},
    "extensions":     {"weak_extension"},
    "drops":          {"dropped_argument"},
    "evidence_use":   {"weak_evidence"},
    "clash":          {"no_clash"},
    "organization":   {"organization"},
}


def _to_pct(val: float, max_val: float = 20.0) -> float:
    """Convert a rubric 0-20 dimension score to percentage points (0-100)."""
    return round(val * 100.0 / max_val, 1)


def _evaluate_criteria_from_text(
    skill: str,
    response: str,
    all_criteria: list[str],
) -> list[str]:
    """
    Deterministic text-based criteria evaluation.
    Counts signal keyword matches; maps match density to criteria fraction.
    Empty / whitespace response → empty list.
    """
    if not response.strip():
        return []
    text = response.lower()
    signals = _SKILL_CRITERIA_SIGNALS.get(skill, [])
    if not signals:
        return all_criteria[:1] if all_criteria else []
    match_count = sum(1 for s in signals if s in text)
    fraction = match_count / max(len(signals), 1)
    n_met = round(fraction * len(all_criteria))
    return all_criteria[:n_met]


def _evaluate_criteria_from_report(
    skill: str,
    new_report: dict,
    all_criteria: list[str],
) -> list[str]:
    """Check which success criteria appear satisfied in a new feedback report."""
    raw = new_report.get("raw_feedback") or {}
    issue_types = {i.get("issue_type") for i in (raw.get("structured_issues") or [])}
    failure_issues = _FAILURE_ISSUE_MAP.get(skill, set())
    still_failing = issue_types & failure_issues
    n_met = max(0, len(all_criteria) - len(still_failing))
    return all_criteria[:n_met]


def _compute_remaining_issue(
    skill: str,
    new_report: Optional[dict],
    criteria_met: list[str],
    all_criteria: list[str],
) -> Optional[str]:
    """Return the most important remaining issue description, or None."""
    unmet = [c for c in all_criteria if c not in criteria_met]
    if not unmet:
        return None
    if new_report:
        raw = new_report.get("raw_feedback") or {}
        for issue in (raw.get("structured_issues") or []):
            issue_skill = ISSUE_TO_SKILL.get(issue.get("issue_type", ""), "")
            if issue_skill == skill:
                rec = issue.get("recommendation") or issue.get("explanation")
                if rec:
                    return rec
    return unmet[0]


def _derive_completion_result(skill: str, before: dict, after: dict) -> str:
    """
    Return 'improved', 'unchanged', or 'regressed' from rubric 0-20 score dicts.
    Threshold: >=2 points delta on 0-20 scale (=10 ppt on 0-100 normalised scale).
    """
    dim = _SKILL_TO_DIM.get(skill)
    if dim:
        b_val = before.get(dim)
        a_val = after.get(dim)
        if b_val is not None and a_val is not None:
            delta = a_val - b_val
            if delta >= 2:
                return "improved"
            if delta <= -2:
                return "regressed"
            return "unchanged"

    if skill == "delivery":
        b_filler = before.get("filler_word_count")
        a_filler = after.get("filler_word_count")
        if b_filler and a_filler:
            if a_filler < b_filler * 0.5:
                return "improved"
            if a_filler > b_filler * 1.2:
                return "regressed"
            return "unchanged"

    return "completed"
