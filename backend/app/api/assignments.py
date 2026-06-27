"""Team assignments API.

Authorization is derived from the verified Supabase JWT (see services/auth.py),
never from a client-supplied user_id. The backend uses the service-role client
(which bypasses RLS), so every endpoint also enforces team-role permissions in
code via `_require_coach` / `_require_member`.

Lifecycle (per recipient):
    assigned → started → reviewed | revision_requested
The *effective* status shown to users is derived from the linked speech's real
analysis state: started+processing, started+done → ready_for_review, started+error
→ failed. Work only reaches the coach's review queue once it's genuinely usable.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth import get_current_user_id
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assignments"])


# ── Models ────────────────────────────────────────────────────────────────────


class AssignmentCreate(BaseModel):
    team_id: str
    title: str
    kind: str = "speech"  # speech | drill | rerecord
    speech_type: str | None = None
    side: str | None = None
    judge_type: str | None = None
    topic: str | None = None
    goal: str | None = None
    success_criteria: list[str] = []
    due_date: str | None = None
    recipient_user_ids: list[str] = []


class RecipientStatus(BaseModel):
    id: str
    user_id: str
    display_name: str | None = None
    status: str  # effective status
    base_status: str = "assigned"
    submission_speech_id: str | None = None
    coach_feedback: str | None = None
    submitted_at: str | None = None
    reviewed_at: str | None = None


class Assignment(BaseModel):
    id: str
    team_id: str
    created_by: str
    title: str
    kind: str
    speech_type: str | None = None
    side: str | None = None
    judge_type: str | None = None
    topic: str | None = None
    goal: str | None = None
    success_criteria: list[str] = []
    due_date: str | None = None
    created_at: str
    recipients: list[RecipientStatus] = []


class StartRequest(BaseModel):
    speech_id: str


class ReviewRequest(BaseModel):
    action: str  # reviewed | revision_requested
    coach_feedback: str | None = None


class ReviewQueueItem(BaseModel):
    recipient_id: str
    assignment_id: str
    assignment_title: str
    student_id: str
    student_name: str | None = None
    status: str
    submission_speech_id: str | None = None
    submitted_at: str | None = None


# ── Constants / pure helpers ────────────────────────────────────────────────────


VALID_KINDS = {"speech", "drill", "rerecord"}
VALID_ACTIONS = {"reviewed", "revision_requested"}

# Coarse speech states the analysis pipeline exposes.
_PROCESSING_SPEECH = {"pending", "transcribing", "analyzing"}

# Order used to sort a coach's review surface (most actionable first).
EFFECTIVE_STATUS_ORDER = [
    "ready_for_review",
    "revision_requested",
    "processing",
    "started",
    "failed",
    "assigned",
    "reviewed",
]


def effective_status(base_status: str, speech_status: str | None) -> str:
    """Derive the truthful status from the base lifecycle + real speech state."""
    if base_status in ("reviewed", "revision_requested"):
        return base_status
    if base_status == "assigned":
        return "assigned"
    # base_status == "started": work has begun and a speech is linked.
    if speech_status is None:
        return "started"
    if speech_status == "done":
        return "ready_for_review"
    if speech_status == "error":
        return "failed"
    if speech_status in _PROCESSING_SPEECH:
        return "processing"
    return "started"


def status_rank(status: str) -> int:
    try:
        return EFFECTIVE_STATUS_ORDER.index(status)
    except ValueError:
        return len(EFFECTIVE_STATUS_ORDER)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Permission helpers (in-code, service-role bypasses RLS) ──────────────────────


def _member_role(supabase, team_id: str, user_id: str) -> str | None:
    res = (
        supabase.table("team_members")
        .select("role")
        .eq("team_id", team_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return res.data[0]["role"] if res.data else None


def _require_coach(supabase, team_id: str, user_id: str) -> None:
    role = _member_role(supabase, team_id, user_id)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    if role != "coach":
        raise HTTPException(status_code=403, detail="Only team coaches can do this")


def _require_member(supabase, team_id: str, user_id: str) -> str:
    role = _member_role(supabase, team_id, user_id)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    return role


def _speech_status_map(supabase, speech_ids: list[str]) -> dict[str, str]:
    ids = [s for s in speech_ids if s]
    if not ids:
        return {}
    try:
        rows = supabase.table("speeches").select("id, status").in_("id", ids).execute().data or []
        return {r["id"]: r["status"] for r in rows}
    except Exception:
        return {}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/assignments", response_model=Assignment, status_code=201)
async def create_assignment(
    body: AssignmentCreate, caller: str = Depends(get_current_user_id)
) -> Assignment:
    """Create an assignment (coach-only) and recipient rows for each student."""
    supabase = get_supabase()
    _require_coach(supabase, body.team_id, caller)

    if body.kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {body.kind}")
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Assignment title is required")
    if not body.recipient_user_ids:
        raise HTTPException(status_code=400, detail="Select at least one recipient")

    try:
        result = (
            supabase.table("assignments")
            .insert(
                {
                    "team_id": body.team_id,
                    "created_by": caller,
                    "title": body.title.strip(),
                    "kind": body.kind,
                    "speech_type": body.speech_type,
                    "side": body.side,
                    "judge_type": body.judge_type,
                    "topic": body.topic,
                    "goal": body.goal,
                    "success_criteria": body.success_criteria,
                    "due_date": body.due_date,
                }
            )
            .execute()
        )
        assignment = result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_assignment: insert failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to create assignment") from exc

    rows = [
        {"assignment_id": assignment["id"], "user_id": uid}
        for uid in dict.fromkeys(body.recipient_user_ids)
    ]
    recipients: list[RecipientStatus] = []
    try:
        rec_result = supabase.table("assignment_recipients").insert(rows).execute()
        recipients = [
            RecipientStatus(
                id=r["id"], user_id=r["user_id"], status="assigned",
                base_status=r.get("status", "assigned"),
            )
            for r in (rec_result.data or [])
        ]
    except Exception as exc:
        logger.error("create_assignment: recipients insert failed | %s", type(exc).__name__)

    return Assignment(**assignment, recipients=recipients)


@router.get("/teams/{team_id}/assignments", response_model=list[Assignment])
async def list_assignments(team_id: str, caller: str = Depends(get_current_user_id)) -> list[Assignment]:
    """List a team's assignments. Coaches see all recipients; students see only
    their own recipient row. Effective status reflects real analysis state."""
    supabase = get_supabase()
    role = _require_member(supabase, team_id, caller)

    try:
        a_result = (
            supabase.table("assignments")
            .select("*")
            .eq("team_id", team_id)
            .order("created_at", desc=True)
            .execute()
        )
        assignments = a_result.data or []
    except Exception as exc:
        logger.error("list_assignments: fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch assignments") from exc

    if not assignments:
        return []

    assignment_ids = [a["id"] for a in assignments]
    try:
        rec_query = (
            supabase.table("assignment_recipients")
            .select("*, profiles(display_name)")
            .in_("assignment_id", assignment_ids)
        )
        if role != "coach":
            rec_query = rec_query.eq("user_id", caller)
        recipients = rec_query.execute().data or []
    except Exception as exc:
        logger.error("list_assignments: recipients fetch failed | %s", type(exc).__name__)
        recipients = []

    speech_status = _speech_status_map(supabase, [r.get("submission_speech_id") for r in recipients])

    by_assignment: dict[str, list[RecipientStatus]] = {}
    for r in recipients:
        name = r.get("profiles", {}).get("display_name") if r.get("profiles") else None
        eff = effective_status(r["status"], speech_status.get(r.get("submission_speech_id")))
        by_assignment.setdefault(r["assignment_id"], []).append(
            RecipientStatus(
                id=r["id"], user_id=r["user_id"], display_name=name,
                status=eff, base_status=r["status"],
                submission_speech_id=r.get("submission_speech_id"),
                coach_feedback=r.get("coach_feedback"), submitted_at=r.get("submitted_at"),
                reviewed_at=r.get("reviewed_at"),
            )
        )

    out = [Assignment(**a, recipients=by_assignment.get(a["id"], [])) for a in assignments]
    if role != "coach":
        out = [a for a in out if a.recipients]
    return out


@router.post("/assignments/recipients/{recipient_id}/start", response_model=RecipientStatus)
async def start_assignment(
    recipient_id: str, body: StartRequest, caller: str = Depends(get_current_user_id)
) -> RecipientStatus:
    """Student begins their assignment with a speech. Marks it `started`; it
    becomes `ready_for_review` only once that speech's analysis completes."""
    supabase = get_supabase()

    rec = (
        supabase.table("assignment_recipients")
        .select("*")
        .eq("id", recipient_id)
        .limit(1)
        .execute()
    )
    if not rec.data:
        raise HTTPException(status_code=404, detail="Assignment not found")
    recipient = rec.data[0]
    if recipient["user_id"] != caller:
        raise HTTPException(status_code=403, detail="This assignment isn't yours")

    try:
        updated = (
            supabase.table("assignment_recipients")
            .update(
                {
                    "status": "started",
                    "submission_speech_id": body.speech_id,
                    "submitted_at": _now(),
                    # A fresh attempt clears the stale review verdict.
                    "reviewed_at": None,
                }
            )
            .eq("id", recipient_id)
            .execute()
        )
        r = updated.data[0]
        return RecipientStatus(
            id=r["id"], user_id=r["user_id"], status=effective_status(r["status"], None),
            base_status=r["status"], submission_speech_id=r.get("submission_speech_id"),
            submitted_at=r.get("submitted_at"),
        )
    except Exception as exc:
        logger.error("start_assignment: update failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to start assignment") from exc


@router.post("/assignments/recipients/{recipient_id}/review", response_model=RecipientStatus)
async def review_assignment(
    recipient_id: str, body: ReviewRequest, caller: str = Depends(get_current_user_id)
) -> RecipientStatus:
    """Coach reviews a submission: mark reviewed or request a revision."""
    supabase = get_supabase()

    if body.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid action: {body.action}")

    rec = (
        supabase.table("assignment_recipients")
        .select("*, assignments(team_id)")
        .eq("id", recipient_id)
        .limit(1)
        .execute()
    )
    if not rec.data:
        raise HTTPException(status_code=404, detail="Submission not found")
    recipient = rec.data[0]
    team_id = recipient.get("assignments", {}).get("team_id") if recipient.get("assignments") else None
    if not team_id:
        raise HTTPException(status_code=404, detail="Assignment not found")

    _require_coach(supabase, team_id, caller)

    try:
        updated = (
            supabase.table("assignment_recipients")
            .update(
                {"status": body.action, "coach_feedback": body.coach_feedback, "reviewed_at": _now()}
            )
            .eq("id", recipient_id)
            .execute()
        )
        r = updated.data[0]
        result_row = RecipientStatus(
            id=r["id"], user_id=r["user_id"], status=effective_status(r["status"], None),
            base_status=r["status"], submission_speech_id=r.get("submission_speech_id"),
            coach_feedback=r.get("coach_feedback"), reviewed_at=r.get("reviewed_at"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("review_assignment: update failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to review") from exc

    # Emit mastery evidence when coach approves a submission (best-effort, non-fatal).
    # This is a coach_performance_review — the coach observed the student's actual
    # assignment submission, so an artifact_id (the recipient_id) is present.
    if body.action == "reviewed":
        try:
            assignment_row = recipient.get("assignments") or {}
            skill_focus = assignment_row.get("skill_focus") or assignment_row.get("skill_target")
            if skill_focus:
                from app.services.mastery_integration import emit_from_coach_performance_review
                emit_from_coach_performance_review(
                    supabase=supabase,
                    coach_id=caller,
                    student_id=result_row.user_id,
                    review_id=f"assignment_review:{recipient_id}",
                    skill=skill_focus,
                    score_pct=75.0,  # default passing score for reviewed assignment
                    artifact_id=recipient_id,   # the assignment submission ID
                    note=body.coach_feedback or "Assignment reviewed and approved",
                )
        except Exception:
            pass

    return result_row


@router.get("/teams/{team_id}/review-queue", response_model=list[ReviewQueueItem])
async def review_queue(team_id: str, caller: str = Depends(get_current_user_id)) -> list[ReviewQueueItem]:
    """Coach-only: submissions whose analysis is complete and awaiting review."""
    supabase = get_supabase()
    _require_coach(supabase, team_id, caller)

    try:
        a_result = supabase.table("assignments").select("id, title").eq("team_id", team_id).execute()
        assignments = {a["id"]: a["title"] for a in (a_result.data or [])}
    except Exception as exc:
        logger.error("review_queue: assignments fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to load queue") from exc

    if not assignments:
        return []

    try:
        recs = (
            supabase.table("assignment_recipients")
            .select("*, profiles(display_name)")
            .in_("assignment_id", list(assignments.keys()))
            .eq("status", "started")
            .order("submitted_at", desc=False)
            .execute()
        ).data or []
    except Exception as exc:
        logger.error("review_queue: recipients fetch failed | %s", type(exc).__name__)
        recs = []

    speech_status = _speech_status_map(supabase, [r.get("submission_speech_id") for r in recs])

    items: list[ReviewQueueItem] = []
    for r in recs:
        eff = effective_status(r["status"], speech_status.get(r.get("submission_speech_id")))
        # Only genuinely-usable work belongs in the review queue.
        if eff != "ready_for_review":
            continue
        items.append(
            ReviewQueueItem(
                recipient_id=r["id"], assignment_id=r["assignment_id"],
                assignment_title=assignments.get(r["assignment_id"], "Assignment"),
                student_id=r["user_id"],
                student_name=(r.get("profiles", {}).get("display_name") if r.get("profiles") else None),
                status=eff, submission_speech_id=r.get("submission_speech_id"),
                submitted_at=r.get("submitted_at"),
            )
        )
    return items


@router.get("/assignments/for-speech/{speech_id}")
async def assignment_for_speech(speech_id: str, caller: str = Depends(get_current_user_id)) -> dict:
    """Return the assignment + recipient tied to a speech, IF the caller is the
    student who owns it or a coach of that assignment's team. Powers the report
    review rail. Returns {assignment: null} when there's no linked assignment."""
    supabase = get_supabase()

    rec_res = (
        supabase.table("assignment_recipients")
        .select("*, assignments(*)")
        .eq("submission_speech_id", speech_id)
        .limit(1)
        .execute()
    )
    if not rec_res.data:
        return {"assignment": None}
    recipient = rec_res.data[0]
    assignment = recipient.get("assignments")
    if not assignment:
        return {"assignment": None}

    is_owner = recipient["user_id"] == caller
    role = _member_role(supabase, assignment["team_id"], caller)
    is_coach = role == "coach"
    if not is_owner and not is_coach:
        raise HTTPException(status_code=403, detail="You can't view this assignment")

    speech_status = _speech_status_map(supabase, [speech_id]).get(speech_id)
    eff = effective_status(recipient["status"], speech_status)

    return {
        "viewer_is_coach": is_coach,
        "recipient": {
            "id": recipient["id"],
            "user_id": recipient["user_id"],
            "status": eff,
            "base_status": recipient["status"],
            "coach_feedback": recipient.get("coach_feedback"),
            "submission_speech_id": speech_id,
        },
        "assignment": {
            "id": assignment["id"],
            "title": assignment["title"],
            "kind": assignment["kind"],
            "goal": assignment.get("goal"),
            "success_criteria": assignment.get("success_criteria", []),
            "due_date": assignment.get("due_date"),
            "team_id": assignment["team_id"],
        },
    }


@router.get("/teams/{team_id}/students/{student_id}")
async def student_profile(team_id: str, student_id: str, caller: str = Depends(get_current_user_id)) -> dict:
    """Coach-only: a single student's practice profile within the team."""
    supabase = get_supabase()
    _require_coach(supabase, team_id, caller)

    if _member_role(supabase, team_id, student_id) is None:
        raise HTTPException(status_code=404, detail="Student is not on this team")

    try:
        name_res = (
            supabase.table("profiles").select("display_name").eq("id", student_id).limit(1).execute()
        )
        display_name = name_res.data[0]["display_name"] if name_res.data else None
    except Exception:
        display_name = None

    try:
        speeches = (
            supabase.table("speeches")
            .select("id, title, speech_type, status, created_at")
            .eq("user_id", student_id)
            .order("created_at", desc=True)
            .execute()
        ).data or []
    except Exception:
        speeches = []

    try:
        a_ids = [
            a["id"]
            for a in (supabase.table("assignments").select("id").eq("team_id", team_id).execute().data or [])
        ]
        recs = []
        if a_ids:
            recs = (
                supabase.table("assignment_recipients")
                .select("*, assignments(title)")
                .in_("assignment_id", a_ids)
                .eq("user_id", student_id)
                .execute()
            ).data or []
        rec_speech_status = _speech_status_map(supabase, [r.get("submission_speech_id") for r in recs])
        assignments = [
            {
                "recipient_id": r["id"],
                "title": (r.get("assignments", {}).get("title") if r.get("assignments") else "Assignment"),
                "status": effective_status(r["status"], rec_speech_status.get(r.get("submission_speech_id"))),
                "submission_speech_id": r.get("submission_speech_id"),
            }
            for r in recs
        ]
    except Exception:
        assignments = []

    return {
        "student_id": student_id,
        "display_name": display_name,
        "speech_count": len(speeches),
        "feedback_ready_count": sum(1 for s in speeches if s["status"] == "done"),
        "speeches": speeches[:10],
        "assignments": assignments,
    }


@router.get("/teams/{team_id}/readiness")
async def team_readiness(team_id: str, caller: str = Depends(get_current_user_id)) -> dict:
    """Coach-only: practical readiness derived from real assignment data."""
    supabase = get_supabase()
    _require_coach(supabase, team_id, caller)

    try:
        a_result = supabase.table("assignments").select("id").eq("team_id", team_id).execute()
        assignment_ids = [a["id"] for a in (a_result.data or [])]
    except Exception:
        assignment_ids = []

    recs: list[dict] = []
    if assignment_ids:
        try:
            recs = (
                supabase.table("assignment_recipients")
                .select("status, submission_speech_id")
                .in_("assignment_id", assignment_ids)
                .execute()
            ).data or []
        except Exception:
            recs = []

    speech_status = _speech_status_map(supabase, [r.get("submission_speech_id") for r in recs])
    eff = [effective_status(r["status"], speech_status.get(r.get("submission_speech_id"))) for r in recs]

    total = len(eff)
    counts = {s: eff.count(s) for s in set(eff)}
    reviewed = counts.get("reviewed", 0)
    revision = counts.get("revision_requested", 0)
    completed = reviewed + revision

    return {
        "team_id": team_id,
        "assignment_count": len(assignment_ids),
        "recipient_total": total,
        "assigned": counts.get("assigned", 0),
        "in_progress": counts.get("started", 0) + counts.get("processing", 0),
        "ready_for_review": counts.get("ready_for_review", 0),
        "failed": counts.get("failed", 0),
        "reviewed": reviewed,
        "revision_requested": revision,
        "review_backlog": counts.get("ready_for_review", 0),
        "completion_rate": round(completed / total, 2) if total else None,
    }
