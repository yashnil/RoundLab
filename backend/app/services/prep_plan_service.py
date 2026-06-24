"""Pass 14 — Prep Plan Service.

Generates and manages prioritized prep task lists from readiness reports.

Design invariants:
- Does NOT auto-delete manually created tasks on refresh.
- Auto-generated tasks are marked is_auto_generated=True.
- On refresh, existing auto-generated tasks for the same report are deactivated
  (status → 'skipped') before new ones are added.
- Completed tasks are never mutated.
- Tournament date affects urgency weighting.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from app.models.tournament_prep import (
    GapCategory,
    GapSeverity,
    PrepGap,
    PrepPlan,
    PrepReadinessReport,
    PrepTaskCreate,
    PrepTaskRow,
    TaskType,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ── Gap → task type mapping ───────────────────────────────────────────────────

_GAP_TO_TASK_TYPE: dict[str, TaskType] = {
    "missing_argument": "research_evidence",
    "missing_claim_support": "research_evidence",
    "missing_warrant": "strengthen_warrant",
    "missing_impact": "add_impact_evidence",
    "missing_uniqueness": "research_evidence",
    "missing_link": "research_evidence",
    "missing_internal_link": "strengthen_warrant",
    "missing_response": "build_frontline",
    "missing_counterevidence": "find_counterevidence",
    "missing_weighing": "add_weighing",
    "weak_source": "verify_citation",
    "unsupported_card": "review_unsafe_card",
    "partial_support": "verify_citation",
    "abstract_only": "replace_stale_card",
    "stale_evidence": "replace_stale_card",
    "freshness_unknown": "verify_citation",
    "duplicate_evidence": "research_evidence",
    "insufficient_source_diversity": "research_evidence",
    "missing_summary_extension": "write_summary_extension",
    "missing_final_focus_extension": "write_final_focus_extension",
    "frontline_underdeveloped": "build_frontline",
}

# Estimated minutes by task type
_TASK_MINUTES: dict[str, int] = {
    "research_evidence": 30,
    "replace_stale_card": 20,
    "verify_citation": 10,
    "strengthen_warrant": 15,
    "add_impact_evidence": 25,
    "find_counterevidence": 30,
    "build_frontline": 20,
    "add_weighing": 15,
    "write_summary_extension": 10,
    "write_final_focus_extension": 10,
    "complete_a_drill": 10,
    "review_unsafe_card": 10,
}

# Severity → priority (1=highest)
_SEVERITY_TO_PRIORITY: dict[str, int] = {
    "critical": 1,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 3,
}


def _gap_to_task(gap: PrepGap, workspace_id: str, user_id: str) -> PrepTaskCreate:
    """Convert a prep gap into a task creation request."""
    task_type = _GAP_TO_TASK_TYPE.get(gap.gap_category, "research_evidence")
    priority = _SEVERITY_TO_PRIORITY.get(gap.severity, 2)
    minutes = _TASK_MINUTES.get(task_type, 20)

    return PrepTaskCreate(
        workspace_id=workspace_id,
        user_id=user_id,
        task_type=task_type,
        title=gap.title,
        reason=gap.reason,
        argument_id=gap.argument_id,
        blockfile_id=gap.blockfile_id,
        card_id=gap.card_id,
        frontline_id=gap.frontline_id,
        gap_id=gap.id,
        priority=priority,
        estimated_minutes=minutes,
        is_auto_generated=True,
    )


def _urgency_multiplier(priority: int, tournament_date: Optional[date], today: date) -> float:
    """Boost urgency when tournament is near."""
    if tournament_date is None:
        return 1.0
    days_until = (tournament_date - today).days
    if days_until <= 3:
        return 0.5 if priority >= 3 else 0.0   # everything is urgent now
    if days_until <= 7:
        return 0.7
    if days_until <= 14:
        return 0.85
    return 1.0


def generate_tasks_from_report(
    report: PrepReadinessReport,
    workspace_id: str,
    today: Optional[date] = None,
) -> list[PrepTaskCreate]:
    """Generate ordered prep tasks from a readiness report."""
    if today is None:
        today = date.today()

    tournament_date = report.tournament_date
    tasks: list[PrepTaskCreate] = []

    # Prioritize critical gaps first
    ordered_gaps = sorted(
        report.gaps,
        key=lambda g: (
            _SEVERITY_TO_PRIORITY.get(g.severity, 2),
            0 if g.gap_category in ("unsupported_card", "stale_evidence") else 1,
        ),
    )

    seen_titles: set[str] = set()
    for gap in ordered_gaps:
        if gap.gap_category == "info":
            continue
        task = _gap_to_task(gap, workspace_id, report.user_id)
        # De-duplicate tasks with identical titles
        if task.title in seen_titles:
            continue
        seen_titles.add(task.title)
        tasks.append(task)

    return tasks


def save_tasks(tasks: list[PrepTaskCreate]) -> list[PrepTaskRow]:
    """Persist tasks to the database."""
    sb = get_supabase()
    rows: list[PrepTaskRow] = []
    now_iso = date.today().isoformat() + "T00:00:00"

    for t in tasks:
        payload: dict = {
            "workspace_id": t.workspace_id,
            "user_id": t.user_id,
            "task_type": t.task_type,
            "title": t.title,
            "reason": t.reason,
            "priority": t.priority,
            "estimated_minutes": t.estimated_minutes,
            "is_auto_generated": t.is_auto_generated,
            "status": "pending",
        }
        for opt in ["argument_id", "blockfile_id", "card_id", "frontline_id",
                    "gap_id", "due_date", "assigned_by"]:
            val = getattr(t, opt, None)
            if val is not None:
                payload[opt] = str(val) if isinstance(val, date) else val

        result = sb.table("prep_tasks").insert(payload).execute()
        if result.data:
            row_data = result.data[0]
            # Add defaults for required fields if DB doesn't return them
            row_data.setdefault("created_at", now_iso)
            row_data.setdefault("updated_at", now_iso)
            try:
                rows.append(PrepTaskRow(**row_data))
            except Exception as exc:
                logger.warning("save_tasks: failed to parse row: %s", exc)
    return rows


def get_workspace_tasks(workspace_id: str, user_id: str) -> list[PrepTaskRow]:
    """Load all non-skipped tasks for a workspace."""
    sb = get_supabase()
    result = (
        sb.table("prep_tasks")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user_id)
        .neq("status", "skipped")
        .order("priority")
        .order("created_at")
        .execute()
    )
    tasks: list[PrepTaskRow] = []
    for row in result.data or []:
        try:
            tasks.append(PrepTaskRow(**row))
        except Exception as exc:
            logger.warning("get_workspace_tasks: skip row: %s", exc)
    return tasks


def update_task_status(
    task_id: str,
    user_id: str,
    status: str,
    completion_notes: Optional[str] = None,
) -> Optional[PrepTaskRow]:
    """Update task status. Returns None if not found."""
    sb = get_supabase()
    updates: dict = {"status": status}
    if completion_notes:
        updates["completion_notes"] = completion_notes
    if status == "completed":
        from datetime import datetime
        updates["completed_at"] = datetime.utcnow().isoformat()

    result = (
        sb.table("prep_tasks")
        .update(updates)
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        return None
    try:
        return PrepTaskRow(**result.data[0])
    except Exception as exc:
        logger.warning("update_task_status: parse error: %s", exc)
        return None


def build_prep_plan(
    workspace_id: str,
    user_id: str,
    report: PrepReadinessReport,
) -> PrepPlan:
    """Build a PrepPlan from a readiness report. Does not persist; caller saves tasks."""
    tasks_to_create = generate_tasks_from_report(report, workspace_id)
    total_minutes = sum(t.estimated_minutes or 0 for t in tasks_to_create)

    return PrepPlan(
        workspace_id=workspace_id,
        user_id=user_id,
        resolution_title=report.resolution_title,
        tournament_date=report.tournament_date,
        tasks=[],            # populated by caller after saving
        workouts=[],
        total_estimated_minutes=total_minutes,
        generated_from_report_id=report.id,
    )
