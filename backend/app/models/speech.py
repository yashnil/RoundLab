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
