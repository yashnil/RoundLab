import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.models.job import AnalysisJobRow
from app.services.jobs import (
    create_job,
    get_job,
    list_jobs_for_speech,
    retry_job as _retry_job,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=AnalysisJobRow)
async def get_job_endpoint(job_id: str, user_id: str = Query(...)) -> AnalysisJobRow:
    """Fetch a single analysis job by ID. Only the job owner can read it."""
    sb = get_supabase()
    try:
        job = get_job(sb, job_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch job") from exc
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/speeches/{speech_id}/jobs", response_model=list[AnalysisJobRow])
async def list_speech_jobs(
    speech_id: str,
    user_id: str = Query(...),
) -> list[AnalysisJobRow]:
    """List analysis jobs for a speech, newest first. Used for recovery on page load."""
    sb = get_supabase()
    try:
        return list_jobs_for_speech(sb, speech_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch jobs") from exc


@router.post("/jobs/{job_id}/retry", response_model=AnalysisJobRow)
async def retry_job_endpoint(
    job_id: str,
    user_id: str = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> AnalysisJobRow:
    """
    Retry a failed speech_analysis job.

    Resets the job to queued, increments attempt_count, and re-enqueues
    the background pipeline. Only failed jobs can be retried.
    """
    from app.services.analysis_pipeline import run_speech_analysis_pipeline

    sb = get_supabase()
    try:
        updated = _retry_job(sb, job_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to retry job") from exc

    # Re-enqueue pipeline for speech_analysis jobs
    speech_id: str | None = updated.get("speech_id")
    if updated.get("job_type") == "speech_analysis" and speech_id:
        background_tasks.add_task(
            run_speech_analysis_pipeline,
            updated["id"],
            speech_id,
            user_id,
        )
        logger.info(
            "retry_job: pipeline re-enqueued | job_id=%s speech_id=%s",
            updated["id"],
            speech_id,
        )

    return updated
