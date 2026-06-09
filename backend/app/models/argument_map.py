from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


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
    # Correction metadata — present after migration 20260609400000
    source_type: str = "ai"
    original_arguments: Optional[list[ArgumentItem]] = None
    user_corrected_at: Optional[datetime] = None
    correction_notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class ArgumentMapCorrectionRequest(BaseModel):
    """Request body for PATCH /speeches/{speech_id}/argument-map."""

    arguments: list[ArgumentItem]
    correction_notes: Optional[str] = None

    @field_validator("arguments")
    @classmethod
    def validate_arguments(cls, v: list[ArgumentItem]) -> list[ArgumentItem]:
        if not v:
            raise ValueError("At least one argument is required")
        for arg in v:
            if not arg.label.strip():
                raise ValueError("Every argument must have a non-empty label")
            if not arg.claim.strip():
                raise ValueError("Every argument must have a non-empty claim")
        return v
