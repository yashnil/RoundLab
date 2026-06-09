from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AnalysisJobRow(BaseModel):
    id: str
    user_id: str
    speech_id: Optional[str] = None
    drill_id: Optional[str] = None
    document_id: Optional[str] = None
    job_type: str
    status: str
    current_step: Optional[str] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    result_json: Optional[dict[str, Any]] = None
    attempt_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
