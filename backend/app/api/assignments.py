"""Team assignments API.

Coaches create assignments for their team; students submit work against them;
coaches review submissions. The backend uses the service-role Supabase client
(which bypasses RLS), so every endpoint enforces team-role permissions IN CODE
via `_member_role` — RLS in the migration is defense-in-depth.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assignments"])


# ── Models ────────────────────────────────────────────────────────────────────


class AssignmentCreate(BaseModel):
    team_id: str
    created_by: str
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
    status: str
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


class SubmitRequest(BaseModel):
    user_id: str
    speech_id: str


class ReviewRequest(BaseModel):
    user_id: str
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


# ── Permission helpers ─────────────────────────────────────────────────────────


VALID_KINDS = {"speech", "drill", "rerecord"}
VALID_ACTIONS = {"reviewed", "revision_requested"}


def _member_role(supabase, team_id: str, user_id: str) -> str | None:
    """Return the user's role in the team, or None if not a member."""
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/assignments", response_model=Assignment, status_code=201)
async def create_assignment(body: AssignmentCreate) -> Assignment:
    """Create an assignment (coach-only) and recipient rows for each student."""
    supabase = get_supabase()
    _require_coach(supabase, body.team_id, body.created_by)

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
                    "created_by": body.created_by,
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

    # Insert recipient rows (de-duplicated).
    rows = [
        {"assignment_id": assignment["id"], "user_id": uid}
        for uid in dict.fromkeys(body.recipient_user_ids)
    ]
    recipients: list[RecipientStatus] = []
    try:
        rec_result = supabase.table("assignment_recipients").insert(rows).execute()
        recipients = [
            RecipientStatus(
                id=r["id"], user_id=r["user_id"], status=r.get("status", "assigned"),
            )
            for r in (rec_result.data or [])
        ]
    except Exception as exc:
        logger.error("create_assignment: recipients insert failed | %s", type(exc).__name__)

    return Assignment(**assignment, recipients=recipients)


@router.get("/teams/{team_id}/assignments", response_model=list[Assignment])
async def list_assignments(team_id: str, user_id: str) -> list[Assignment]:
    """List a team's assignments. Coaches see all recipients; students see only
    their own recipient row."""
    supabase = get_supabase()
    role = _require_member(supabase, team_id, user_id)

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
            rec_query = rec_query.eq("user_id", user_id)
        recipients = rec_query.execute().data or []
    except Exception as exc:
        logger.error("list_assignments: recipients fetch failed | %s", type(exc).__name__)
        recipients = []

    by_assignment: dict[str, list[RecipientStatus]] = {}
    for r in recipients:
        name = r.get("profiles", {}).get("display_name") if r.get("profiles") else None
        by_assignment.setdefault(r["assignment_id"], []).append(
            RecipientStatus(
                id=r["id"], user_id=r["user_id"], display_name=name,
                status=r["status"], submission_speech_id=r.get("submission_speech_id"),
                coach_feedback=r.get("coach_feedback"), submitted_at=r.get("submitted_at"),
                reviewed_at=r.get("reviewed_at"),
            )
        )

    out = [Assignment(**a, recipients=by_assignment.get(a["id"], [])) for a in assignments]
    # Students only see assignments they're a recipient of.
    if role != "coach":
        out = [a for a in out if a.recipients]
    return out


@router.post("/assignments/recipients/{recipient_id}/submit", response_model=RecipientStatus)
async def submit_assignment(recipient_id: str, body: SubmitRequest) -> RecipientStatus:
    """Student marks their assignment recipient row as submitted with a speech."""
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
    if recipient["user_id"] != body.user_id:
        raise HTTPException(status_code=403, detail="This assignment isn't yours")

    try:
        updated = (
            supabase.table("assignment_recipients")
            .update(
                {
                    "status": "submitted",
                    "submission_speech_id": body.speech_id,
                    "submitted_at": _now(),
                }
            )
            .eq("id", recipient_id)
            .execute()
        )
        r = updated.data[0]
        return RecipientStatus(
            id=r["id"], user_id=r["user_id"], status=r["status"],
            submission_speech_id=r.get("submission_speech_id"), submitted_at=r.get("submitted_at"),
        )
    except Exception as exc:
        logger.error("submit_assignment: update failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to submit") from exc


@router.post("/assignments/recipients/{recipient_id}/review", response_model=RecipientStatus)
async def review_assignment(recipient_id: str, body: ReviewRequest) -> RecipientStatus:
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

    _require_coach(supabase, team_id, body.user_id)

    try:
        updated = (
            supabase.table("assignment_recipients")
            .update(
                {
                    "status": body.action,
                    "coach_feedback": body.coach_feedback,
                    "reviewed_at": _now(),
                }
            )
            .eq("id", recipient_id)
            .execute()
        )
        r = updated.data[0]
        return RecipientStatus(
            id=r["id"], user_id=r["user_id"], status=r["status"],
            submission_speech_id=r.get("submission_speech_id"),
            coach_feedback=r.get("coach_feedback"), reviewed_at=r.get("reviewed_at"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("review_assignment: update failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to review") from exc


@router.get("/teams/{team_id}/review-queue", response_model=list[ReviewQueueItem])
async def review_queue(team_id: str, user_id: str) -> list[ReviewQueueItem]:
    """Coach-only: submissions awaiting review for this team."""
    supabase = get_supabase()
    _require_coach(supabase, team_id, user_id)

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
            .eq("status", "submitted")
            .order("submitted_at", desc=False)
            .execute()
        ).data or []
    except Exception as exc:
        logger.error("review_queue: recipients fetch failed | %s", type(exc).__name__)
        recs = []

    return [
        ReviewQueueItem(
            recipient_id=r["id"],
            assignment_id=r["assignment_id"],
            assignment_title=assignments.get(r["assignment_id"], "Assignment"),
            student_id=r["user_id"],
            student_name=(r.get("profiles", {}).get("display_name") if r.get("profiles") else None),
            status=r["status"],
            submission_speech_id=r.get("submission_speech_id"),
            submitted_at=r.get("submitted_at"),
        )
        for r in recs
    ]


@router.get("/teams/{team_id}/students/{student_id}")
async def student_profile(team_id: str, student_id: str, user_id: str) -> dict:
    """Coach-only: a single student's practice profile within the team."""
    supabase = get_supabase()
    _require_coach(supabase, team_id, user_id)

    # Confirm the target is actually a member of this team.
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

    # The student's assignment recipient rows on this team.
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
        assignments = [
            {
                "recipient_id": r["id"],
                "title": (r.get("assignments", {}).get("title") if r.get("assignments") else "Assignment"),
                "status": r["status"],
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
async def team_readiness(team_id: str, user_id: str) -> dict:
    """Coach-only: practical readiness derived from real assignment data."""
    supabase = get_supabase()
    _require_coach(supabase, team_id, user_id)

    try:
        a_result = supabase.table("assignments").select("id").eq("team_id", team_id).execute()
        assignment_ids = [a["id"] for a in (a_result.data or [])]
    except Exception:
        assignment_ids = []

    statuses: list[str] = []
    if assignment_ids:
        try:
            recs = (
                supabase.table("assignment_recipients")
                .select("status")
                .in_("assignment_id", assignment_ids)
                .execute()
            ).data or []
            statuses = [r["status"] for r in recs]
        except Exception:
            statuses = []

    total = len(statuses)
    submitted = sum(1 for s in statuses if s == "submitted")
    reviewed = sum(1 for s in statuses if s == "reviewed")
    revision = sum(1 for s in statuses if s == "revision_requested")
    assigned = sum(1 for s in statuses if s == "assigned")
    completed = reviewed + revision

    return {
        "team_id": team_id,
        "assignment_count": len(assignment_ids),
        "recipient_total": total,
        "assigned": assigned,
        "submitted": submitted,
        "reviewed": reviewed,
        "revision_requested": revision,
        "review_backlog": submitted,
        "completion_rate": round(completed / total, 2) if total else None,
    }
