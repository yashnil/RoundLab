"""
Job lifecycle helpers for the analysis_jobs table.

All functions accept a Supabase client as the first argument so tests can
inject a mock without touching the singleton.

Status transitions:
  queued → running → succeeded
                   ↘ failed
  failed → queued (via retry_job)
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def create_job(
    sb,
    user_id: str,
    job_type: str,
    *,
    speech_id: str | None = None,
    drill_id: str | None = None,
    document_id: str | None = None,
) -> dict:
    """Insert a new queued job and return the saved row."""
    row: dict = {
        "user_id": user_id,
        "job_type": job_type,
        "status": "queued",
        "attempt_count": 1,
    }
    if speech_id:
        row["speech_id"] = speech_id
    if drill_id:
        row["drill_id"] = drill_id
    if document_id:
        row["document_id"] = document_id

    result = sb.table("analysis_jobs").insert(row).execute()
    job = result.data[0]
    logger.info(
        "create_job: job_id=%s type=%s speech_id=%s",
        job["id"],
        job_type,
        speech_id,
    )
    return job


def start_job(sb, job_id: str) -> None:
    """Mark a job running and record when it started."""
    sb.table("analysis_jobs").update({
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()


def update_job_progress(sb, job_id: str, step: str, progress: int) -> None:
    """Update current_step and progress (0–100). Best-effort — never raises."""
    try:
        sb.table("analysis_jobs").update({
            "current_step": step,
            "progress": max(0, min(100, progress)),
        }).eq("id", job_id).execute()
    except Exception as exc:
        logger.warning(
            "update_job_progress: failed | job_id=%s | %s",
            job_id,
            type(exc).__name__,
        )


def complete_job(
    sb,
    job_id: str,
    result_json: dict[str, Any] | None = None,
) -> None:
    """Mark job succeeded and record completed_at."""
    payload: dict = {
        "status": "succeeded",
        "progress": 100,
        "current_step": "done",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if result_json is not None:
        payload["result_json"] = result_json
    sb.table("analysis_jobs").update(payload).eq("id", job_id).execute()
    logger.info("complete_job: job_id=%s", job_id)


def fail_job(
    sb,
    job_id: str,
    error_message: str,
    error_code: str | None = None,
) -> None:
    """Mark job failed with a user-safe error message and record completed_at."""
    payload: dict = {
        "status": "failed",
        "error_message": error_message,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if error_code:
        payload["error_code"] = error_code
    sb.table("analysis_jobs").update(payload).eq("id", job_id).execute()
    logger.info("fail_job: job_id=%s code=%s msg=%s", job_id, error_code, error_message)


def get_job(sb, job_id: str, user_id: str) -> dict | None:
    """Fetch a single job by ID with ownership check. Returns None if not found."""
    result = (
        sb.table("analysis_jobs")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def list_jobs_for_speech(
    sb,
    speech_id: str,
    user_id: str,
    limit: int = 10,
) -> list[dict]:
    """Return jobs for a speech, newest first."""
    result = (
        sb.table("analysis_jobs")
        .select("*")
        .eq("speech_id", speech_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def retry_job(sb, job_id: str, user_id: str) -> dict:
    """
    Reset a failed job to queued and increment attempt_count.

    Raises ValueError if the job doesn't belong to the user or is not failed.
    The caller is responsible for re-enqueuing the background task.
    """
    existing = get_job(sb, job_id, user_id)
    if not existing:
        raise ValueError("Job not found")
    if existing["status"] != "failed":
        raise ValueError(
            f"Cannot retry job with status '{existing['status']}' — only failed jobs can be retried"
        )

    attempt_count = (existing.get("attempt_count") or 1) + 1
    result = (
        sb.table("analysis_jobs")
        .update({
            "status": "queued",
            "current_step": None,
            "progress": None,
            "error_message": None,
            "error_code": None,
            "started_at": None,
            "completed_at": None,
            "attempt_count": attempt_count,
        })
        .eq("id", job_id)
        .execute()
    )
    updated = result.data[0]
    logger.info("retry_job: job_id=%s attempt_count=%d", job_id, attempt_count)
    return updated
