"""Pydantic models for the Training OS API."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Mastery models ─────────────────────────────────────────────────────────────

class MasteryScore(BaseModel):
    """Per-skill mastery snapshot for a single user."""

    user_id: str
    skill_id: str
    mastery_score: float = Field(0.0, ge=0, le=100)
    confidence: float = Field(0.0, ge=0, le=1)
    evidence_count: int = Field(0, ge=0)
    mastery_state: str = "not_started"
    last_demonstrated_at: Optional[str] = None
    coach_override_score: Optional[float] = None
    coach_override_note: Optional[str] = None
    recurring_weakness: int = Field(0, ge=0)
    explanation: Optional[str] = None


class MasteryProfile(BaseModel):
    """All skill mastery scores for a user."""

    user_id: str
    skills: dict[str, MasteryScore]
    computed_at: str
    event_pack: str = "public_forum"


class MasteryEvidenceRecord(BaseModel):
    """A single piece of evidence that contributed to a mastery score."""

    skill_id: str
    raw_score: float
    normalized_score: float
    source_type: str
    source_id: Optional[str] = None
    change_reason: Optional[str] = None
    recorded_at: str


class AddMasteryEvidenceRequest(BaseModel):
    """Request to record a new mastery evidence item."""

    skill_id: str
    raw_score: float = Field(..., ge=0)
    source_type: str
    source_id: Optional[str] = None
    change_reason: Optional[str] = None
    input_scale: str = "0-100"  # "0-100" or "0-20"


class CoachOverrideRequest(BaseModel):
    """Coach explicit mastery override for a student's skill."""

    skill_id: str
    override_score: float = Field(..., ge=0, le=100)
    note: str
    # Optional link to the observable artifact that prompted this change
    artifact_id: Optional[str] = None


class CoachPriorityOverrideRequest(BaseModel):
    """Coach changes practice priority WITHOUT changing mastery scores."""

    skills: list[str] = Field(..., min_length=1)
    note: str = ""


# ── Training plan models ───────────────────────────────────────────────────────

class TrainingPlan(BaseModel):
    """A structured training plan for a user."""

    id: str
    user_id: str
    plan_type: str
    event_pack: str = "public_forum"
    current_week: int = 1
    total_weeks: int
    weeks: list[dict[str, Any]]
    status: str = "active"
    tournament_date: Optional[str] = None
    created_at: str


class GeneratePlanRequest(BaseModel):
    """Request to generate a new training plan."""

    plan_type: str  # '1_week' | '4_week' | 'tournament_countdown' | 'custom'
    tournament_date: Optional[str] = None   # ISO date string, e.g. "2026-10-01"
    coach_priority_skills: Optional[list[str]] = None


# ── Curriculum models ──────────────────────────────────────────────────────────

class CurriculumProgress(BaseModel):
    """Progress on a single curriculum lesson."""

    lesson_id: str
    status: str = "not_started"
    score: Optional[float] = None
    completed_at: Optional[str] = None
    coach_note: Optional[str] = None


class MarkLessonRequest(BaseModel):
    """Request to update lesson progress status."""

    lesson_id: str
    status: str  # 'not_started' | 'in_progress' | 'completed' | 'skipped'
    score: Optional[float] = None


# ── Coach calibration ──────────────────────────────────────────────────────────

class CoachCalibrationRequest(BaseModel):
    """Coach calibration settings for a team."""

    standard: str = "novice"        # 'novice' | 'jv' | 'varsity'
    judge_emphasis: str = "lay"     # 'lay' | 'flow' | 'technical' | 'mixed'
    rubric_weights: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)


# ── Diagnostic models ──────────────────────────────────────────────────────────

class DiagnosticStartRequest(BaseModel):
    """Start a new diagnostic intake."""

    experience_level: str = "novice"  # 'first_time' | 'novice' | 'jv' | 'varsity'
    intake_data: dict[str, Any] = Field(default_factory=dict)


class DiagnosticCompleteRequest(BaseModel):
    """Complete a diagnostic, optionally with speech analysis scores."""

    diagnostic_id: str
    speech_scores: Optional[dict[str, float]] = None  # rubric dimension → 0-20 score


# ── Practice agenda ────────────────────────────────────────────────────────────

class PracticeAgendaRequest(BaseModel):
    """Request a coach-facing practice agenda for a team."""

    team_id: str
    duration_minutes: int = Field(60, ge=10, le=240)
