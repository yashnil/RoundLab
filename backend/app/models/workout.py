from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class WorkoutStep(BaseModel):
    id: str
    title: str
    category: str          # "argument" | "evidence" | "delivery" | "rerecord"
    focus: str             # "warranting" | "weighing" | "evidence" | "delivery" | etc.
    estimated_minutes: int
    source: str            # "feedback" | "drill" | "delivery" | "evidence"
    problem: str
    instruction: str
    success_criteria: str
    linked_drill_id: Optional[str] = None
    completed: bool = False


class WorkoutJson(BaseModel):
    steps: list[WorkoutStep]
    re_record_goal: str
    coach_note: str
    generated_from: dict[str, Any]


class WorkoutRow(BaseModel):
    id: str
    user_id: str
    speech_id: str
    title: str
    description: Optional[str] = None
    estimated_minutes: Optional[int] = None
    workout_type: str = "tournament_prep"
    status: str = "not_started"
    focus_area: Optional[str] = None
    workout_json: WorkoutJson
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class GenerateWorkoutRequest(BaseModel):
    user_id: str
    force_regenerate: bool = False


class UpdateWorkoutRequest(BaseModel):
    user_id: str
    status: Optional[str] = None
    completed_step_ids: Optional[list[str]] = None
