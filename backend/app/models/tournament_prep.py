"""Pydantic models for Pass 14 — Tournament Prep Intelligence.

Tables: prep_workspaces · prep_readiness_reports · prep_gaps ·
        prep_tasks · prep_workouts
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

# ── Literal types ─────────────────────────────────────────────────────────────

Side = Literal["pro", "con", "both"]

GapCategory = Literal[
    "missing_argument",
    "missing_claim_support",
    "missing_warrant",
    "missing_impact",
    "missing_uniqueness",
    "missing_link",
    "missing_internal_link",
    "missing_response",
    "missing_counterevidence",
    "missing_weighing",
    "weak_source",
    "unsupported_card",
    "partial_support",
    "abstract_only",
    "stale_evidence",
    "freshness_unknown",
    "duplicate_evidence",
    "insufficient_source_diversity",
    "missing_summary_extension",
    "missing_final_focus_extension",
    "frontline_underdeveloped",
]

GapSeverity = Literal["critical", "high", "medium", "low", "info"]

FreshnessState = Literal[
    "current",
    "aging",
    "stale",
    "superseded",
    "older_but_still_relevant",
    "freshness_unknown",
    "not_time_sensitive",
]

FrontlineReadiness = Literal[
    "ready",
    "usable_with_gaps",
    "underdeveloped",
    "unsafe",
]

CoverageState = Literal[
    "covered",
    "partially_covered",
    "missing",
    "not_applicable",
    "warning",
]

TaskType = Literal[
    "research_evidence",
    "replace_stale_card",
    "verify_citation",
    "strengthen_warrant",
    "add_impact_evidence",
    "find_counterevidence",
    "build_frontline",
    "add_weighing",
    "write_summary_extension",
    "write_final_focus_extension",
    "complete_a_drill",
    "review_unsafe_card",
]

TaskStatus = Literal["pending", "in_progress", "completed", "skipped"]

WorkoutType = Literal[
    "evidence_explanation",
    "card_comparison",
    "frontline_speed",
    "summary_extension",
    "evidence_indictment",
    "stale_evidence",
    "lay_judge_evidence",
]

PrepWorkoutStatus = Literal["not_started", "in_progress", "completed", "skipped"]

# ── PrepWorkspace ─────────────────────────────────────────────────────────────

class PrepWorkspaceCreate(BaseModel):
    user_id: str
    resolution_id: str
    side: Side = "both"
    tournament_date: Optional[date] = None
    judge_emphasis: Optional[str] = None
    team_id: Optional[str] = None


class PrepWorkspaceUpdate(BaseModel):
    user_id: str
    side: Optional[Side] = None
    tournament_date: Optional[date] = None
    judge_emphasis: Optional[str] = None


class PrepWorkspaceRow(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None
    resolution_id: str
    side: Side = "both"
    tournament_date: Optional[date] = None
    judge_emphasis: Optional[str] = None
    created_at: str
    updated_at: str


# ── EvidenceFreshnessAssessment ───────────────────────────────────────────────

class EvidenceFreshnessAssessment(BaseModel):
    """Freshness evaluation for one evidence card."""
    card_id: str
    card_tag: Optional[str] = None
    published_date: Optional[str] = None       # ISO date string or None
    freshness_state: FreshnessState
    claim_type: str = "general"                 # e.g. statistics, law, historical, scientific
    rule_applied: str                           # human-readable rule name
    explanation: str
    days_old: Optional[int] = None
    has_newer_corroboration: bool = False
    assessed_at: str                            # ISO datetime


# ── CoverageDimension ─────────────────────────────────────────────────────────

class CoverageDimension(BaseModel):
    """One row in the coverage matrix for a blockfile argument."""
    dimension: str                              # e.g. "claim", "warrant", "impact"
    state: CoverageState
    evidence: list[str] = []                    # card_ids that satisfy this dimension
    notes: Optional[str] = None


class BlockfileCoverageResult(BaseModel):
    """Coverage matrix for one blockfile section or argument."""
    argument_id: Optional[str] = None
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    argument_type: Optional[str] = None        # contention, response, framework, etc.
    dimensions: list[CoverageDimension] = []
    covered_count: int = 0
    total_applicable_count: int = 0
    coverage_pct: float = 0.0
    gaps: list[str] = []                       # gap category strings for this section


# ── PrepGap ───────────────────────────────────────────────────────────────────

class PrepGap(BaseModel):
    """One detected preparation gap."""
    id: Optional[str] = None
    gap_category: GapCategory
    severity: GapSeverity
    title: str
    reason: str
    is_deterministic: bool = True
    # Library links
    argument_id: Optional[str] = None
    blockfile_id: Optional[str] = None
    section_id: Optional[str] = None
    card_id: Optional[str] = None
    frontline_id: Optional[str] = None
    # Action
    recommended_action: Optional[str] = None
    estimated_minutes: Optional[int] = None
    resolved: bool = False


# ── Readiness dimensions ──────────────────────────────────────────────────────

class DimensionScore(BaseModel):
    """Score and explanation for one readiness dimension."""
    dimension: str
    score: Optional[int] = None         # 0-100; None = insufficient data
    weight: float = 1.0                  # configurable weight in composite
    explanation: str = ""
    contributing_gaps: list[str] = []   # gap IDs that caused deductions


class ReadinessDimensions(BaseModel):
    argument_coverage: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="argument_coverage", weight=1.5)
    )
    evidence_quality: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="evidence_quality", weight=1.2)
    )
    evidence_freshness: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="evidence_freshness", weight=1.0)
    )
    frontline_readiness: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="frontline_readiness", weight=1.3)
    )
    source_diversity: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="source_diversity", weight=0.8)
    )
    speech_stage_readiness: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="speech_stage_readiness", weight=1.0)
    )
    weighing_preparation: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="weighing_preparation", weight=0.9)
    )


# ── PrepReadinessReport ───────────────────────────────────────────────────────

class PrepReadinessReport(BaseModel):
    """Full readiness snapshot for a resolution + side."""
    id: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: str
    resolution_id: str
    resolution_title: Optional[str] = None
    side: Side = "both"
    generated_at: str
    library_watermark: Optional[str] = None
    tournament_date: Optional[date] = None
    # Scores
    dimensions: ReadinessDimensions = Field(default_factory=ReadinessDimensions)
    composite_score: Optional[int] = None
    # Summaries
    gaps: list[PrepGap] = []
    critical_gaps: list[PrepGap] = []
    stale_cards: list[EvidenceFreshnessAssessment] = []
    unsafe_cards: list[str] = []           # card_ids with unsafe verdicts
    strongest_arguments: list[str] = []    # argument titles
    weakest_frontlines: list[str] = []     # frontline titles
    # Coverage
    blockfile_coverage: list[BlockfileCoverageResult] = []
    # Freshness
    freshness_assessments: list[EvidenceFreshnessAssessment] = []
    # Next actions
    next_recommended_actions: list[str] = []
    # Meta
    total_cards: int = 0
    total_arguments: int = 0
    total_frontlines: int = 0
    total_blockfiles: int = 0


# ── PrepTask ──────────────────────────────────────────────────────────────────

class PrepTaskCreate(BaseModel):
    workspace_id: str
    user_id: str
    task_type: TaskType = "research_evidence"
    title: str
    reason: Optional[str] = None
    argument_id: Optional[str] = None
    blockfile_id: Optional[str] = None
    card_id: Optional[str] = None
    frontline_id: Optional[str] = None
    gap_id: Optional[str] = None
    priority: int = 2
    estimated_minutes: Optional[int] = None
    due_date: Optional[date] = None
    is_auto_generated: bool = False
    assigned_by: Optional[str] = None


class PrepTaskUpdate(BaseModel):
    user_id: str
    status: Optional[TaskStatus] = None
    completion_notes: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None


class PrepTaskRow(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    assigned_by: Optional[str] = None
    gap_id: Optional[str] = None
    task_type: TaskType
    title: str
    reason: Optional[str] = None
    argument_id: Optional[str] = None
    blockfile_id: Optional[str] = None
    card_id: Optional[str] = None
    frontline_id: Optional[str] = None
    priority: int = 2
    estimated_minutes: Optional[int] = None
    due_date: Optional[date] = None
    status: TaskStatus = "pending"
    completion_notes: Optional[str] = None
    is_auto_generated: bool = False
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


# ── PrepWorkout ───────────────────────────────────────────────────────────────

class PrepWorkoutCreate(BaseModel):
    workspace_id: str
    user_id: str
    gap_id: Optional[str] = None
    task_id: Optional[str] = None
    workout_type: WorkoutType = "evidence_explanation"
    title: str
    description: Optional[str] = None
    prompt: str
    instructions: Optional[str] = None
    success_criteria: list[str] = []
    time_limit_seconds: int = 90
    source_card_id: Optional[str] = None
    source_card_tag: Optional[str] = None
    source_card_body: Optional[str] = None


class PrepWorkoutRow(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    gap_id: Optional[str] = None
    task_id: Optional[str] = None
    workout_type: WorkoutType
    title: str
    description: Optional[str] = None
    prompt: str
    instructions: Optional[str] = None
    success_criteria: list[str] = []
    time_limit_seconds: int = 90
    source_card_id: Optional[str] = None
    source_card_tag: Optional[str] = None
    source_card_body: Optional[str] = None
    drill_id: Optional[str] = None
    drill_attempt_id: Optional[str] = None
    status: PrepWorkoutStatus = "not_started"
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


# ── PrepPlan ──────────────────────────────────────────────────────────────────

class PrepPlan(BaseModel):
    """Ordered set of tasks derived from a readiness report."""
    workspace_id: str
    user_id: str
    resolution_title: Optional[str] = None
    tournament_date: Optional[date] = None
    tasks: list[PrepTaskRow] = []
    workouts: list[PrepWorkoutRow] = []
    total_estimated_minutes: int = 0
    generated_from_report_id: Optional[str] = None


# ── API request/response types ─────────────────────────────────────────────────

class GenerateReadinessReportRequest(BaseModel):
    workspace_id: str
    user_id: str
    force_refresh: bool = False


class GeneratePrepPlanRequest(BaseModel):
    workspace_id: str
    user_id: str
    report_id: str


class FreshnessCheckRequest(BaseModel):
    user_id: str
    card_id: str
    resolution_id: Optional[str] = None


class NewerEvidenceSearchRequest(BaseModel):
    user_id: str
    card_id: str
    resolution_id: Optional[str] = None
    max_queries: int = 3            # bounded query count


class WorkspaceOverviewResponse(BaseModel):
    workspace: PrepWorkspaceRow
    latest_report: Optional[PrepReadinessReport] = None
    pending_tasks: list[PrepTaskRow] = []
    active_workouts: list[PrepWorkoutRow] = []


# ── Observability events ──────────────────────────────────────────────────────

class PrepObsEvent(BaseModel):
    event_name: str
    user_id: str
    workspace_id: Optional[str] = None
    report_id: Optional[str] = None
    gap_count: Optional[int] = None
    task_count: Optional[int] = None
    metadata: dict[str, Any] = {}
