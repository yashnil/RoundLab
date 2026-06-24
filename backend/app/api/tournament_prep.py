"""Pass 14 — Tournament Prep API.

All endpoints are under /prep prefix.
Ownership: user_id passed in body or query params; service layer enforces ownership.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.tournament_prep import (
    GeneratePrepPlanRequest,
    GenerateReadinessReportRequest,
    NewerEvidenceSearchRequest,
    PrepPlan,
    PrepReadinessReport,
    PrepTaskCreate,
    PrepTaskRow,
    PrepTaskUpdate,
    PrepWorkoutCreate,
    PrepWorkoutRow,
    PrepWorkspaceCreate,
    PrepWorkspaceRow,
    PrepWorkspaceUpdate,
    WorkspaceOverviewResponse,
)
from app.services.gap_workout_generator import generate_workouts_for_report
from app.services.prep_plan_service import (
    build_prep_plan,
    generate_tasks_from_report,
    get_workspace_tasks,
    save_tasks,
    update_task_status,
)
from app.services.product_events import track_product_event
from app.services.supabase_client import get_supabase
from app.services.tournament_prep_service import generate_readiness_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prep", tags=["tournament_prep"])

_NOW = lambda: datetime.utcnow().isoformat()


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


# ── Workspace CRUD ─────────────────────────────────────────────────────────────

@router.post("/workspaces", response_model=PrepWorkspaceRow)
def create_workspace(body: PrepWorkspaceCreate) -> PrepWorkspaceRow:
    """Create or upsert a prep workspace for a resolution."""
    sb = get_supabase()
    now = _NOW()
    payload: dict = {
        "user_id": body.user_id,
        "resolution_id": body.resolution_id,
        "side": body.side,
    }
    for opt in ["tournament_date", "judge_emphasis", "team_id"]:
        val = getattr(body, opt, None)
        if val is not None:
            payload[opt] = str(val) if hasattr(val, "isoformat") else val

    try:
        result = sb.table("prep_workspaces").insert(payload).execute()
        if not result.data:
            raise ValueError("Insert returned no data")
        row = result.data[0]
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        return PrepWorkspaceRow(**row)
    except Exception as exc:
        logger.error("create_workspace: %s", exc)
        raise _http(exc) from exc


@router.get("/workspaces/{workspace_id}", response_model=PrepWorkspaceRow)
def get_workspace(workspace_id: str, user_id: str = Query(...)) -> PrepWorkspaceRow:
    sb = get_supabase()
    result = (
        sb.table("prep_workspaces").select("*")
        .eq("id", workspace_id).limit(1).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Workspace not found")
    row = result.data[0]
    if row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return PrepWorkspaceRow(**row)


@router.get("/workspaces", response_model=list[PrepWorkspaceRow])
def list_workspaces(user_id: str = Query(...)) -> list[PrepWorkspaceRow]:
    sb = get_supabase()
    result = (
        sb.table("prep_workspaces").select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return [PrepWorkspaceRow(**r) for r in (result.data or [])]


@router.patch("/workspaces/{workspace_id}", response_model=PrepWorkspaceRow)
def update_workspace(workspace_id: str, body: PrepWorkspaceUpdate) -> PrepWorkspaceRow:
    sb = get_supabase()
    # Verify ownership
    existing = sb.table("prep_workspaces").select("user_id").eq("id", workspace_id).limit(1).execute()
    if not existing.data or existing.data[0]["user_id"] != body.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updates: dict = {}
    if body.side is not None:
        updates["side"] = body.side
    if body.tournament_date is not None:
        updates["tournament_date"] = str(body.tournament_date)
    if body.judge_emphasis is not None:
        updates["judge_emphasis"] = body.judge_emphasis
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = sb.table("prep_workspaces").update(updates).eq("id", workspace_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return PrepWorkspaceRow(**result.data[0])


# ── Readiness Report ──────────────────────────────────────────────────────────

@router.post("/readiness-report", response_model=PrepReadinessReport)
def generate_report(body: GenerateReadinessReportRequest) -> PrepReadinessReport:
    """Generate (or refresh) a readiness report for a workspace."""
    sb = get_supabase()
    # Load workspace
    ws_result = (
        sb.table("prep_workspaces").select("*")
        .eq("id", body.workspace_id).limit(1).execute()
    )
    if not ws_result.data:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws_row = ws_result.data[0]
    if ws_row["user_id"] != body.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check cache (skip if force_refresh)
    if not body.force_refresh:
        cached = (
            sb.table("prep_readiness_reports").select("report_json")
            .eq("workspace_id", body.workspace_id)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        if cached.data and cached.data[0].get("report_json"):
            try:
                return PrepReadinessReport(**cached.data[0]["report_json"])
            except Exception:
                pass  # fall through to regenerate

    # Fix optional date field
    ws_row.setdefault("created_at", _NOW())
    ws_row.setdefault("updated_at", _NOW())
    # Convert tournament_date string to date if present
    from datetime import date
    td = ws_row.get("tournament_date")
    if isinstance(td, str):
        try:
            ws_row["tournament_date"] = date.fromisoformat(td)
        except Exception:
            ws_row["tournament_date"] = None

    workspace = PrepWorkspaceRow(**ws_row)

    try:
        report = generate_readiness_report(workspace)
    except Exception as exc:
        logger.error("generate_report: %s", exc)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc

    # Persist report
    try:
        report_payload = {
            "workspace_id": body.workspace_id,
            "user_id": body.user_id,
            "resolution_id": workspace.resolution_id,
            "side": workspace.side,
            "tournament_date": str(workspace.tournament_date) if workspace.tournament_date else None,
            "gap_count": len(report.gaps),
            "stale_card_count": len(report.stale_cards),
            "unsafe_card_count": len(report.unsafe_cards),
            "composite_score": report.composite_score,
            "report_json": report.model_dump(),
        }
        insert_result = sb.table("prep_readiness_reports").insert(report_payload).execute()
        if insert_result.data:
            report.id = insert_result.data[0].get("id")
    except Exception as exc:
        logger.warning("generate_report: failed to persist: %s", exc)

    # Observability
    track_product_event(
        body.user_id,
        "readiness_reports_generated",
        metadata={
            "workspace_id": body.workspace_id,
            "gap_count": len(report.gaps),
            "composite_score": report.composite_score,
        },
    )

    return report


# ── Prep Plan ─────────────────────────────────────────────────────────────────

@router.post("/prep-plan", response_model=PrepPlan)
def generate_prep_plan(body: GeneratePrepPlanRequest) -> PrepPlan:
    """Generate a prioritized prep plan from a readiness report."""
    sb = get_supabase()
    # Load the report
    report_result = (
        sb.table("prep_readiness_reports").select("*")
        .eq("id", body.report_id).limit(1).execute()
    )
    if not report_result.data:
        raise HTTPException(status_code=404, detail="Report not found")
    report_row = report_result.data[0]
    if report_row["user_id"] != body.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        report = PrepReadinessReport(**report_row["report_json"])
        report.id = body.report_id
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse report: {exc}") from exc

    task_creates = generate_tasks_from_report(report, body.workspace_id)
    saved_tasks = save_tasks(task_creates)

    plan = build_prep_plan(body.workspace_id, body.user_id, report)
    plan.tasks = saved_tasks

    # Generate workouts
    cards: dict = {}
    for gap in report.gaps:
        if gap.card_id:
            cards[gap.card_id] = {"id": gap.card_id, "tag": gap.title, "body_text": ""}

    workout_creates = generate_workouts_for_report(
        report, cards, body.workspace_id, body.user_id
    )
    saved_workouts = save_workouts(workout_creates)
    plan.workouts = saved_workouts

    track_product_event(
        body.user_id,
        "prep_tasks_created",
        metadata={"task_count": len(saved_tasks), "workout_count": len(saved_workouts)},
    )

    return plan


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/tasks", response_model=list[PrepTaskRow])
def list_tasks(workspace_id: str, user_id: str = Query(...)) -> list[PrepTaskRow]:
    return get_workspace_tasks(workspace_id, user_id)


@router.post("/tasks", response_model=PrepTaskRow)
def create_task(body: PrepTaskCreate) -> PrepTaskRow:
    """Create a manual prep task."""
    tasks = save_tasks([body])
    if not tasks:
        raise HTTPException(status_code=500, detail="Task creation failed")
    return tasks[0]


@router.patch("/tasks/{task_id}", response_model=PrepTaskRow)
def update_task(task_id: str, body: PrepTaskUpdate) -> PrepTaskRow:
    row = update_task_status(
        task_id, body.user_id,
        body.status or "pending",
        body.completion_notes,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found or not authorized")
    if body.status == "completed":
        track_product_event(body.user_id, "prep_tasks_completed", metadata={"task_id": task_id})
    return row


# ── Workouts ──────────────────────────────────────────────────────────────────

def save_workouts(creates: list[PrepWorkoutCreate]) -> list[PrepWorkoutRow]:
    """Persist workout rows. Non-raising."""
    sb = get_supabase()
    rows: list[PrepWorkoutRow] = []
    now = _NOW()
    for wo in creates:
        payload: dict = {
            "workspace_id": wo.workspace_id,
            "user_id": wo.user_id,
            "workout_type": wo.workout_type,
            "title": wo.title,
            "description": wo.description,
            "prompt": wo.prompt,
            "instructions": wo.instructions,
            "success_criteria": wo.success_criteria,
            "time_limit_seconds": wo.time_limit_seconds,
            "status": "not_started",
        }
        for opt in ["gap_id", "task_id", "source_card_id", "source_card_tag"]:
            val = getattr(wo, opt, None)
            if val is not None:
                payload[opt] = val
        # source_card_body stored truncated (first 1000 chars)
        body_text = wo.source_card_body
        if body_text:
            payload["source_card_body"] = body_text[:1000]

        try:
            result = sb.table("prep_workouts").insert(payload).execute()
            if result.data:
                row = result.data[0]
                row.setdefault("created_at", now)
                row.setdefault("updated_at", now)
                row.setdefault("success_criteria", [])
                rows.append(PrepWorkoutRow(**row))
        except Exception as exc:
            logger.warning("save_workouts: skip row: %s", exc)
    return rows


@router.get("/workspaces/{workspace_id}/workouts", response_model=list[PrepWorkoutRow])
def list_workouts(workspace_id: str, user_id: str = Query(...)) -> list[PrepWorkoutRow]:
    sb = get_supabase()
    result = (
        sb.table("prep_workouts").select("*")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user_id)
        .neq("status", "skipped")
        .order("created_at", desc=False)
        .execute()
    )
    rows: list[PrepWorkoutRow] = []
    for r in result.data or []:
        r.setdefault("success_criteria", [])
        try:
            rows.append(PrepWorkoutRow(**r))
        except Exception as exc:
            logger.warning("list_workouts: skip row: %s", exc)
    return rows


@router.patch("/workouts/{workout_id}/complete")
def complete_workout(workout_id: str, user_id: str = Query(...)) -> dict:
    sb = get_supabase()
    existing = sb.table("prep_workouts").select("user_id,gap_id").eq("id", workout_id).limit(1).execute()
    if not existing.data or existing.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workout not found or not authorized")
    result = sb.table("prep_workouts").update({
        "status": "completed",
        "completed_at": _NOW(),
    }).eq("id", workout_id).execute()
    track_product_event(user_id, "workouts_completed", metadata={"workout_id": workout_id})
    return {"ok": True, "note": "Gap still requires research evidence. Workout completion does not resolve missing-evidence gaps."}


# ── Freshness check ───────────────────────────────────────────────────────────

@router.get("/freshness/{card_id}")
def check_card_freshness(card_id: str, user_id: str = Query(...)) -> dict:
    """Assess freshness for a single card."""
    from app.services.evidence_freshness import assess_freshness
    sb = get_supabase()
    card_result = sb.table("evidence_cards").select("*").eq("id", card_id).limit(1).execute()
    if not card_result.data:
        raise HTTPException(status_code=404, detail="Card not found")
    card = card_result.data[0]
    if card.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    assessment = assess_freshness(card)
    return assessment.model_dump()


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/overview", response_model=WorkspaceOverviewResponse)
def get_overview(workspace_id: str, user_id: str = Query(...)) -> WorkspaceOverviewResponse:
    """Return workspace + latest report + pending tasks + active workouts."""
    sb = get_supabase()
    now = _NOW()

    ws = sb.table("prep_workspaces").select("*").eq("id", workspace_id).limit(1).execute()
    if not ws.data or ws.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Workspace not found or not authorized")
    ws_row = ws.data[0]
    ws_row.setdefault("created_at", now)
    ws_row.setdefault("updated_at", now)
    workspace = PrepWorkspaceRow(**ws_row)

    # Latest report
    latest_report: Optional[PrepReadinessReport] = None
    report_res = (
        sb.table("prep_readiness_reports").select("report_json")
        .eq("workspace_id", workspace_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if report_res.data and report_res.data[0].get("report_json"):
        try:
            latest_report = PrepReadinessReport(**report_res.data[0]["report_json"])
        except Exception:
            pass

    # Pending tasks
    tasks = get_workspace_tasks(workspace_id, user_id)
    pending = [t for t in tasks if t.status == "pending"][:10]

    # Active workouts
    wo_res = (
        sb.table("prep_workouts").select("*")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user_id)
        .eq("status", "not_started")
        .limit(5)
        .execute()
    )
    active_workouts: list[PrepWorkoutRow] = []
    for r in wo_res.data or []:
        r.setdefault("success_criteria", [])
        try:
            active_workouts.append(PrepWorkoutRow(**r))
        except Exception:
            pass

    return WorkspaceOverviewResponse(
        workspace=workspace,
        latest_report=latest_report,
        pending_tasks=pending,
        active_workouts=active_workouts,
    )


# ── Newer evidence search ─────────────────────────────────────────────────────

@router.post("/newer-evidence")
def find_newer_evidence(body: NewerEvidenceSearchRequest) -> dict:
    """
    Return search instructions for finding newer evidence for a card.
    Reuses the existing evidence query planner — no new providers.
    Does NOT automatically replace the card.
    """
    sb = get_supabase()
    card_result = sb.table("evidence_cards").select("*").eq("id", body.card_id).limit(1).execute()
    if not card_result.data:
        raise HTTPException(status_code=404, detail="Card not found")
    card = card_result.data[0]
    if card.get("user_id") != body.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    tag = card.get("tag", "")
    pub_date = card.get("published_date", "unknown date")
    pub = card.get("publication") or card.get("source_domain") or ""

    claim_queries = [
        f"recent evidence {tag}",
        f"updated research {tag} after {pub_date[:4] if pub_date and pub_date != 'unknown date' else ''}",
        f"new study {tag}",
    ][: body.max_queries]

    track_product_event(body.user_id, "newer_evidence_searches", metadata={"card_id": body.card_id})

    return {
        "card_id": body.card_id,
        "card_tag": tag,
        "original_publication": pub,
        "original_date": pub_date,
        "suggested_queries": claim_queries,
        "instructions": (
            "Use these queries in the Evidence Studio search to find newer sources. "
            "Any newer cards found should be linked via the 'updates' or 'stronger_source' "
            "relationship — they do NOT automatically replace this card. "
            "Your original card and its version history are preserved."
        ),
        "max_queries": body.max_queries,
    }
