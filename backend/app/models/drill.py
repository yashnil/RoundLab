from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DrillRow(BaseModel):
    id: str
    speech_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    skill_target: str
    prompt: str
    order: int
    created_at: datetime
    # Added by migration 20260601000000_add_drill_fields
    instructions: Optional[str] = None
    success_criteria: list[str] = []
    source_weakness: Optional[str] = None
    difficulty: str = "beginner"
    status: str = "assigned"
    # Time limit in seconds — LLM-generated, stored in DB
    time_limit_seconds: Optional[int] = None


class DrillStatusUpdate(BaseModel):
    status: Optional[str] = None
    response: Optional[str] = None


class DrillAttemptRow(BaseModel):
    id: str
    drill_id: str
    user_id: str
    response: Optional[str] = None
    audio_url: Optional[str] = None
    feedback: Optional[dict] = None
    score: Optional[int] = None
    created_at: datetime


class DrillAttemptCreate(BaseModel):
    audio_url: str
