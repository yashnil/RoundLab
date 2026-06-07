from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ArgumentItem(BaseModel):
    label: str
    claim: str
    warrant: str
    evidence: Optional[str] = None
    impact: str
    argument_type: Literal["offense", "defense", "weighing", "response", "unclear"]
    issues: list[str] = []
    confidence: Optional[float] = None
    # Stable index-based ID, assigned when saving (not from LLM)
    id: Optional[str] = None


class ArgumentMapRow(BaseModel):
    id: str
    speech_id: str
    arguments: list[ArgumentItem]
    created_at: datetime
