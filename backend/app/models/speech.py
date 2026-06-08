from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SpeechCreateRequest(BaseModel):
    user_id: str
    title: str
    speech_type: str  # constructive | rebuttal | summary | final_focus | crossfire
    side: Optional[str] = None       # pro | con
    judge_type: Optional[str] = None  # lay | flow | tech | coach
    topic: Optional[str] = None
    # Re-record relationship — set when recording after a drill to track improvement
    parent_speech_id: Optional[str] = None
    source_drill_id: Optional[str] = None


class SpeechUpdateRequest(BaseModel):
    audio_url: str
    duration_seconds: Optional[int] = None


class SpeechRow(BaseModel):
    id: str
    user_id: str
    title: str
    speech_type: str
    side: Optional[str] = None
    judge_type: Optional[str] = None
    topic: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    # Re-record relationship (nullable — absent on older rows)
    parent_speech_id: Optional[str] = None
    source_drill_id: Optional[str] = None
