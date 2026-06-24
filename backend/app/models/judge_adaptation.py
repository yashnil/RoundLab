"""Pass 15 — Judge Adaptation Simulator Models.

All Pydantic models for judge profiles, adaptation results, risks, workouts,
and comparison output.

Immutability contract:
    - Evidence body text is NEVER stored in adaptation output.
    - Source card IDs are referenced but content is not duplicated.
    - Support verdicts and citation metadata pass through unchanged.
    - The system never strengthens a claim for a persuasive judge.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Judge type literals ────────────────────────────────────────────────────────

JudgeType = Literal["lay", "parent", "flow", "technical", "coach", "custom"]

AdaptationTarget = Literal[
    "evidence",
    "argument",
    "frontline",
    "section",
    "summary",
    "final_focus",
    "transcript",
]

AdaptationRiskLevel = Literal["critical", "high", "medium", "low"]

AdaptationRiskCategory = Literal[
    "causal_overstatement",
    "qualifier_removal",
    "missing_extension",
    "new_argument_late_speech",
    "jargon_overflow",
    "under_explanation",
    "shallow_response_overload",
    "evidence_without_analysis",
    "narrative_over_flow",
    "unsafe_card_used",
    "stale_card_used",
    "dropped_argument_uncovered",
    "warrant_collapsed",
    "source_qualification_inflated",
]

WorkoutJudgeType = Literal[
    "lay_explanation",
    "parent_context",
    "flow_extension",
    "technical_concession",
    "judge_switch",
    "evidence_adaptation",
    "final_focus_voter",
]


# ── Preference dimension ───────────────────────────────────────────────────────

class JudgePreferences(BaseModel):
    """
    Thirteen preference dimensions on a 1-5 scale.
    1 = very low / not expected; 5 = very high / strongly expected.
    """
    jargon_tolerance: int = Field(ge=1, le=5)
    speed_tolerance: int = Field(ge=1, le=5)
    evidence_detail_preference: int = Field(ge=1, le=5)
    line_by_line_expectation: int = Field(ge=1, le=5)
    extension_strictness: int = Field(ge=1, le=5)
    weighing_expectation: int = Field(ge=1, le=5)
    narrative_preference: int = Field(ge=1, le=5)
    real_world_explanation: int = Field(ge=1, le=5)
    technical_rule_sensitivity: int = Field(ge=1, le=5)
    intervention_tolerance: int = Field(ge=1, le=5)
    organization_preference: int = Field(ge=1, le=5)
    source_qualification_importance: int = Field(ge=1, le=5)
    persuasion_vs_flow_emphasis: int = Field(ge=1, le=5)


# ── Judge profile ─────────────────────────────────────────────────────────────

class JudgeProfile(BaseModel):
    """Full judge profile (built-in or custom)."""
    id: Optional[str] = None
    judge_type: JudgeType
    name: str
    description: str
    preferences: JudgePreferences
    is_builtin: bool = True

    # Custom profile only
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CustomJudgeProfileCreate(BaseModel):
    user_id: str
    team_id: Optional[str] = None
    name: str
    base_type: JudgeType = "custom"
    description: Optional[str] = None
    preferences: JudgePreferences


class CustomJudgeProfileRow(BaseModel):
    id: str
    user_id: str
    name: str
    base_type: JudgeType
    description: Optional[str] = None
    preferences: JudgePreferences
    is_public: bool = False
    created_at: str
    updated_at: str


# ── Adaptation change ─────────────────────────────────────────────────────────

class AdaptationChange(BaseModel):
    """A single recommended change for this judge type."""
    dimension: str  # e.g. "jargon_level", "response_ordering", "evidence_introduction"
    original: Optional[str] = None
    adapted: str
    reason: str
    may_be_omitted: bool = False


# ── Adaptation risk ───────────────────────────────────────────────────────────

class AdaptationRisk(BaseModel):
    """A detected risk when adapting for this judge."""
    category: AdaptationRiskCategory
    level: AdaptationRiskLevel
    description: str
    source_ref: Optional[str] = None   # card_id, argument_id, etc.
    how_to_mitigate: str


# ── Evidence presentation guidance ───────────────────────────────────────────

class EvidencePresentationGuide(BaseModel):
    """Judge-specific guidance for presenting one card.

    The card body text is NEVER included here.
    """
    card_id: str
    card_tag: Optional[str] = None
    judge_type: JudgeType

    # For lay/parent
    who_is_source: Optional[str] = None
    what_source_found: Optional[str] = None
    why_it_matters: Optional[str] = None
    one_sentence_causal: Optional[str] = None

    # For flow
    short_citation: Optional[str] = None
    flow_warrant: Optional[str] = None
    flow_impact: Optional[str] = None
    role_on_flow: Optional[str] = None

    # For technical
    support_limit: Optional[str] = None
    relevant_qualifier: Optional[str] = None
    concession_interaction: Optional[str] = None
    card_role: Optional[Literal["offense", "defense", "indict"]] = None

    # For coach
    best_practice_note: Optional[str] = None
    methodological_limitation: Optional[str] = None

    # Shared
    estimated_read_time_seconds: Optional[int] = None
    can_be_paraphrased: bool = True
    risks: list[AdaptationRisk] = Field(default_factory=list)


# ── Frontline adaptation ───────────────────────────────────────────────────────

class FrontlineAdaptation(BaseModel):
    """Judge-specific guidance for presenting a frontline."""
    frontline_id: str
    judge_type: JudgeType

    recommended_response_order: list[str] = Field(default_factory=list)
    lead_response_reason: Optional[str] = None
    responses_to_condense: list[str] = Field(default_factory=list)
    responses_to_expand: list[str] = Field(default_factory=list)
    responses_needing_evidence: list[str] = Field(default_factory=list)
    analytic_responses_sufficient: bool = False

    read_evidence: bool = True
    offensive_carry_recommendation: Optional[str] = None
    must_extend_in_summary: list[str] = Field(default_factory=list)
    must_extend_in_final_focus: list[str] = Field(default_factory=list)

    estimated_rebuttal_seconds: int = 90
    changes: list[AdaptationChange] = Field(default_factory=list)
    risks: list[AdaptationRisk] = Field(default_factory=list)


# ── Speech plan adaptation ────────────────────────────────────────────────────

class SpeechStageAdaptation(BaseModel):
    """Judge-specific speech plan for one speech stage."""
    stage: Literal["rebuttal", "summary", "final_focus"]
    judge_type: JudgeType

    response_ordering: list[str] = Field(default_factory=list)
    time_allocation_notes: Optional[str] = None
    evidence_vs_analytics_balance: Optional[str] = None
    collapse_recommendation: Optional[str] = None
    required_extensions: list[str] = Field(default_factory=list)
    voter_framing: Optional[str] = None
    comparative_explanation: Optional[str] = None
    technical_detail_level: Optional[str] = None
    suggested_phrasing: list[str] = Field(default_factory=list)
    changes: list[AdaptationChange] = Field(default_factory=list)
    risks: list[AdaptationRisk] = Field(default_factory=list)
    estimated_seconds: int = 180


# ── Judge adaptation result ───────────────────────────────────────────────────

class JudgeAdaptationResult(BaseModel):
    """Full adaptation result for one source + judge combination."""
    # Identity
    id: Optional[str] = None
    user_id: str
    judge_type: JudgeType
    source_type: AdaptationTarget
    source_id: str  # card_id / argument_id / frontline_id / etc.

    # What the adaptation is for
    original_purpose: str
    judge_goal: str

    # Core adaptation output
    changes: list[AdaptationChange] = Field(default_factory=list)
    risks: list[AdaptationRisk] = Field(default_factory=list)
    critical_risks: list[AdaptationRisk] = Field(default_factory=list)

    # Evidence presentation (for evidence source_type)
    evidence_guide: Optional[EvidencePresentationGuide] = None

    # Frontline adaptation (for frontline source_type)
    frontline_adaptation: Optional[FrontlineAdaptation] = None

    # Speech plans (for summary/final_focus source_type)
    speech_plan: Optional[SpeechStageAdaptation] = None

    # Generic summary fields
    what_to_emphasize: list[str] = Field(default_factory=list)
    what_to_simplify: list[str] = Field(default_factory=list)
    what_must_remain_explicit: list[str] = Field(default_factory=list)
    what_can_be_shortened: list[str] = Field(default_factory=list)
    suggested_phrasing: list[str] = Field(default_factory=list)
    preserved_source_refs: list[str] = Field(default_factory=list)
    estimated_seconds: int = 120

    # Meta
    rules_version: str = "p15_v1"
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Judge comparison ──────────────────────────────────────────────────────────

class JudgeComparisonDiff(BaseModel):
    """One difference between two judge adaptations."""
    dimension: str
    judge_a_value: str
    judge_b_value: str
    why_different: str


class JudgeComparisonResult(BaseModel):
    """Comparison of the same material across two or more judge types."""
    source_type: AdaptationTarget
    source_id: str
    judge_types: list[JudgeType]

    constants: list[str] = Field(default_factory=list)
    differences: list[JudgeComparisonDiff] = Field(default_factory=list)
    strategic_risks_by_judge: dict[str, list[AdaptationRisk]] = Field(default_factory=dict)
    wording_differences: list[JudgeComparisonDiff] = Field(default_factory=list)
    time_allocation_differences: list[JudgeComparisonDiff] = Field(default_factory=list)

    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Judge workout ─────────────────────────────────────────────────────────────

class JudgeWorkoutCreate(BaseModel):
    """A workout derived from actual prepared material for a specific judge type."""
    user_id: str
    workout_type: WorkoutJudgeType
    judge_type: JudgeType
    title: str
    description: Optional[str] = None
    prompt: str
    instructions: Optional[str] = None
    success_criteria: list[str] = Field(default_factory=list)
    time_limit_seconds: int = 90

    # Source material links
    source_card_id: Optional[str] = None
    source_card_tag: Optional[str] = None
    # Bounded snapshot: max 500 chars, only for auditability
    source_card_body_snapshot: Optional[str] = None
    source_argument_id: Optional[str] = None
    source_frontline_id: Optional[str] = None

    # Comparison workout: second judge
    comparison_judge_type: Optional[JudgeType] = None
    workspace_id: Optional[str] = None


class JudgeWorkoutRow(JudgeWorkoutCreate):
    id: str
    status: str = "not_started"
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


# ── Judge readiness score ──────────────────────────────────────────────────────

class JudgeReadinessDimensionScore(BaseModel):
    """Score for a single judge-readiness sub-dimension."""
    dimension: str
    score: Optional[int] = None  # None = insufficient data
    explanation: str
    contributing_risks: list[str] = Field(default_factory=list)


class JudgeReadinessReport(BaseModel):
    """
    Separate from evidence quality/freshness scores.
    Never merged into evidence quality dimension.
    """
    user_id: str
    judge_type: JudgeType
    source_type: AdaptationTarget
    source_id: str

    clarity: JudgeReadinessDimensionScore
    organization: JudgeReadinessDimensionScore
    extension_completeness: JudgeReadinessDimensionScore
    evidence_explanation: JudgeReadinessDimensionScore
    weighing_fit: JudgeReadinessDimensionScore
    jargon_fit: JudgeReadinessDimensionScore
    strategic_focus: JudgeReadinessDimensionScore
    speech_stage_legality: JudgeReadinessDimensionScore

    composite_score: Optional[int] = None
    risks: list[AdaptationRisk] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── API Request/Response models ────────────────────────────────────────────────

class JudgeAdaptationRequest(BaseModel):
    user_id: str
    judge_type: JudgeType
    source_type: AdaptationTarget
    source_id: str  # card_id / argument_id / frontline_id / section_id
    workspace_id: Optional[str] = None
    custom_profile_id: Optional[str] = None
    include_phrasing_suggestions: bool = True  # triggers optional LLM path


class JudgeComparisonRequest(BaseModel):
    user_id: str
    judge_types: list[JudgeType]
    source_type: AdaptationTarget
    source_id: str
    workspace_id: Optional[str] = None


class SaveAdaptationNoteRequest(BaseModel):
    adaptation_id: str
    user_id: str
    judge_type: JudgeType
    note_text: str


class AdaptationNoteRow(BaseModel):
    id: str
    adaptation_id: str
    user_id: str
    judge_type: JudgeType
    note_text: str
    created_at: str


class CoachAssignWorkoutRequest(BaseModel):
    assigned_by: str
    assigned_to: str
    team_id: Optional[str] = None
    judge_type: JudgeType
    source_card_id: Optional[str] = None
    source_card_tag: Optional[str] = None
    source_card_body_snapshot: Optional[str] = None
    workout_type: WorkoutJudgeType
    title: str
    prompt: str
    instructions: Optional[str] = None
    success_criteria: list[str] = Field(default_factory=list)
    time_limit_seconds: int = 90
