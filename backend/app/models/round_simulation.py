"""Pass 16 — Full-Round PF Simulation models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────


class RoundSide(str, Enum):
    PRO = "pro"
    CON = "con"


class SpeakingOrder(str, Enum):
    FIRST = "first"
    SECOND = "second"


class SpeakerRole(str, Enum):
    FIRST = "first"
    SECOND = "second"


class OpponentDifficulty(str, Enum):
    NOVICE = "novice"
    JV = "jv"
    VARSITY = "varsity"


class RoundFormat(str, Enum):
    FULL = "full"
    SHORTENED = "shortened"
    SPEECH_STAGE_DRILL = "speech_stage_drill"
    EVIDENCE_TESTING = "evidence_testing"
    JUDGE_ADAPTATION = "judge_adaptation"


class RoundPhaseType(str, Enum):
    FIRST_CONSTRUCTIVE = "first_constructive"
    SECOND_CONSTRUCTIVE = "second_constructive"
    FIRST_CROSSFIRE = "first_crossfire"
    FIRST_REBUTTAL = "first_rebuttal"
    SECOND_REBUTTAL = "second_rebuttal"
    GRAND_CROSSFIRE = "grand_crossfire"
    FIRST_SUMMARY = "first_summary"
    SECOND_SUMMARY = "second_summary"
    FINAL_CROSSFIRE = "final_crossfire"
    FIRST_FINAL_FOCUS = "first_final_focus"
    SECOND_FINAL_FOCUS = "second_final_focus"
    JUDGE_DELIBERATION = "judge_deliberation"
    COMPLETED = "completed"


class ArgumentFlowStatus(str, Enum):
    INTRODUCED = "introduced"
    ANSWERED = "answered"
    CONCEDED = "conceded"
    EXTENDED = "extended"
    UNDEREXTENDED = "underextended"
    DROPPED = "dropped"
    TURNED = "turned"
    MITIGATED = "mitigated"
    OUTWEIGHED = "outweighed"
    NEW_IN_LATE_SPEECH = "new_in_late_speech"
    UNRESOLVED = "unresolved"
    LIVE = "live"


class CrossfireExchangeType(str, Enum):
    QUESTION = "question"
    ANSWER = "answer"
    CONCESSION = "concession"
    CONTRADICTION = "contradiction"
    EVASION = "evasion"
    EVIDENCE_CHALLENGE = "evidence_challenge"


class EvidenceUseViolationType(str, Enum):
    UNSUPPORTED_TAG = "unsupported_tag"
    CAUSAL_OVERCLAIM = "causal_overclaim"
    STALE_EVIDENCE = "stale_evidence"
    MISSING_CITATION = "missing_citation"
    CARD_DUMPING = "card_dumping"
    NOT_EXTENDED = "not_extended"
    PRIMARY_SOURCE_CHALLENGE = "primary_source_challenge"
    ABSTRACT_ONLY_LIMIT = "abstract_only_limit"
    EVIDENCE_MISMATCH = "evidence_mismatch"


class SpeechLegalityViolationType(str, Enum):
    MISSING_CLASH = "missing_clash"
    NEW_ARGUMENT_IN_SUMMARY = "new_argument_in_summary"
    NEW_ARGUMENT_IN_FINAL_FOCUS = "new_argument_in_final_focus"
    INCONSISTENT_WITH_SUMMARY = "inconsistent_with_summary"
    DROPPED_OFFENSE = "dropped_offense"
    MISSING_WEIGHING = "missing_weighing"
    NEW_EVIDENCE_IN_CROSSFIRE = "new_evidence_in_crossfire"


class RoundStatus(str, Enum):
    SETUP = "setup"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ── Configuration ─────────────────────────────────────────────────────────────


class RoundSimulationConfig(BaseModel):
    format: RoundFormat = RoundFormat.FULL
    student_side: RoundSide
    speaking_order: SpeakingOrder
    speaker_role: SpeakerRole = SpeakerRole.FIRST
    judge_type: str = "flow"
    judge_profile_id: Optional[str] = None
    opponent_difficulty: OpponentDifficulty = OpponentDifficulty.JV
    resolution: str
    resolution_id: Optional[str] = None
    prep_workspace_id: Optional[str] = None
    coaching_hints_enabled: bool = True
    pauses_allowed: bool = True
    practice_mode_overrides: List[str] = Field(default_factory=list)
    # Timing in seconds
    constructive_time: int = 240
    rebuttal_time: int = 240
    summary_time: int = 180
    final_focus_time: int = 120
    crossfire_time: int = 180
    prep_time: int = 120
    # Approved preparation material
    approved_card_ids: List[str] = Field(default_factory=list)
    approved_blockfile_ids: List[str] = Field(default_factory=list)
    approved_frontline_ids: List[str] = Field(default_factory=list)
    source_scope: str = "personal"
    evidence_testing_mode: bool = False


# ── Core simulation ───────────────────────────────────────────────────────────


class RoundSimulation(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None
    config: RoundSimulationConfig
    status: RoundStatus = RoundStatus.SETUP
    current_phase: RoundPhaseType = RoundPhaseType.FIRST_CONSTRUCTIVE
    phase_history: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    is_practice_mode: bool = False
    created_at: str
    updated_at: str


class RoundParticipant(BaseModel):
    id: str
    round_id: str
    user_id: Optional[str] = None
    is_ai: bool
    side: RoundSide
    speaker_role: SpeakerRole
    display_name: str


# ── Speeches ──────────────────────────────────────────────────────────────────


class RoundSpeechInput(BaseModel):
    phase: RoundPhaseType
    audio_url: Optional[str] = None
    transcript_text: Optional[str] = None
    typed_outline: Optional[str] = None


class SpeechLegalityViolation(BaseModel):
    type: SpeechLegalityViolationType
    description: str
    argument_label: Optional[str] = None
    severity: str = "warning"  # warning | error


class RoundSpeech(BaseModel):
    id: str
    round_id: str
    phase: RoundPhaseType
    speaker_side: RoundSide
    is_ai: bool
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    argument_labels: List[str] = Field(default_factory=list)
    responses_made: List[str] = Field(default_factory=list)
    arguments_extended: List[str] = Field(default_factory=list)
    arguments_dropped: List[str] = Field(default_factory=list)
    evidence_card_ids: List[str] = Field(default_factory=list)
    weighing_used: Optional[str] = None
    strategic_goal: Optional[str] = None
    estimated_speaking_time: Optional[int] = None
    legality_violations: List[Dict[str, Any]] = Field(default_factory=list)
    word_count: Optional[int] = None
    is_immutable: bool = False
    created_at: str


# ── Crossfire ─────────────────────────────────────────────────────────────────


class CrossfireExchange(BaseModel):
    id: str
    round_id: str
    phase: RoundPhaseType
    sequence: int
    questioner_side: RoundSide
    question: str
    answer: Optional[str] = None
    target_argument: Optional[str] = None
    exchange_type: CrossfireExchangeType = CrossfireExchangeType.QUESTION
    concession_extracted: Optional[str] = None
    contradiction: Optional[str] = None
    evasion_detected: bool = False
    evidence_challenge: Optional[str] = None
    strategic_significance: str = "low"
    created_at: str


class CrossfireSubmitRequest(BaseModel):
    round_id: str
    phase: RoundPhaseType
    typed_response: Optional[str] = None
    audio_url: Optional[str] = None


# ── Arguments and flow ────────────────────────────────────────────────────────


class RoundArgument(BaseModel):
    id: str
    round_id: str
    label: str
    side: RoundSide
    claim: str
    warrant: Optional[str] = None
    evidence_card_id: Optional[str] = None
    impact: Optional[str] = None
    initial_phase: RoundPhaseType
    status: ArgumentFlowStatus = ArgumentFlowStatus.INTRODUCED
    responses: List[str] = Field(default_factory=list)
    extensions: List[str] = Field(default_factory=list)
    concessions: List[str] = Field(default_factory=list)
    weighing: Optional[str] = None
    is_offense: bool = True
    is_turn: bool = False
    is_framework: bool = False
    parent_argument_id: Optional[str] = None
    last_updated_phase: Optional[str] = None


class RoundFlowEvent(BaseModel):
    id: str
    round_id: str
    phase: RoundPhaseType
    event_type: str  # introduce|answer|extend|drop|turn|weigh|concede|indict|mitigate
    argument_id: str
    side: RoundSide
    description: str
    new_status: ArgumentFlowStatus
    evidence_card_id: Optional[str] = None
    created_at: str


# ── Evidence use ──────────────────────────────────────────────────────────────


class RoundEvidenceUse(BaseModel):
    id: str
    round_id: str
    speech_id: str
    card_id: str
    speaker_side: RoundSide
    phase: RoundPhaseType
    citation_given: bool = False
    tag_matched_source: bool = True
    warrant_explained: bool = False
    extended_later: bool = False
    challenged_by_opponent: bool = False
    challenge_answered: bool = False
    relevant_to_final_decision: bool = False
    violations: List[str] = Field(default_factory=list)
    support_verdict: Optional[str] = None
    source_classification: Optional[str] = None
    flagged: bool = False
    created_at: str


# ── Decision ──────────────────────────────────────────────────────────────────


class DecisionTraceEntry(BaseModel):
    argument_id: str
    argument_label: str
    side: RoundSide
    included: bool
    reason: Optional[str] = None


class RoundDecisionTrace(BaseModel):
    arguments_considered: List[DecisionTraceEntry] = Field(default_factory=list)
    surviving_voters: List[str] = Field(default_factory=list)
    weighing_comparison: str = ""
    judge_profile_effects: List[str] = Field(default_factory=list)
    framework_resolution: Optional[str] = None
    final_winner: Optional[RoundSide] = None
    confidence: str = "contested"


class RoundDecision(BaseModel):
    id: str
    round_id: str
    judge_type: str
    engine_version: str = "v1"
    winner: RoundSide
    reason_for_decision: str
    voting_issues: List[str] = Field(default_factory=list)
    speaker_points: Dict[str, float] = Field(default_factory=dict)
    decisive_concessions: List[str] = Field(default_factory=list)
    dropped_arguments: List[str] = Field(default_factory=list)
    evidence_issues: List[str] = Field(default_factory=list)
    weighing_comparison: str = ""
    legality_issues: List[str] = Field(default_factory=list)
    adaptation_successes: List[str] = Field(default_factory=list)
    adaptation_failures: List[str] = Field(default_factory=list)
    decision_trace: RoundDecisionTrace
    created_at: str


class RejudgeRequest(BaseModel):
    judge_type: str
    judge_profile_id: Optional[str] = None


# ── Opponent planning ─────────────────────────────────────────────────────────


class OpponentArgumentPlan(BaseModel):
    label: str
    claim: str
    warrant: str
    impact: str
    evidence_card_id: Optional[str] = None
    tag: Optional[str] = None
    frontline_ids: List[str] = Field(default_factory=list)
    speech_suitability: List[str] = Field(default_factory=list)


class OpponentRoundPlan(BaseModel):
    id: str
    round_id: str
    side: RoundSide
    difficulty: OpponentDifficulty
    judge_type: str
    constructive_arguments: List[OpponentArgumentPlan] = Field(default_factory=list)
    expected_responses: List[Dict[str, str]] = Field(default_factory=list)
    frontline_priorities: List[str] = Field(default_factory=list)
    preferred_collapse: Optional[str] = None
    weighing_strategy: str = ""
    speech_stage_goals: Dict[str, str] = Field(default_factory=dict)
    approved_card_ids: List[str] = Field(default_factory=list)
    approved_frontline_ids: List[str] = Field(default_factory=list)
    created_at: str


# ── Opponent speech output ────────────────────────────────────────────────────


class OpponentEvidenceReference(BaseModel):
    card_id: str
    tag: str
    cite: str
    support_verdict: str
    source_classification: Optional[str] = None
    quoted_text: Optional[str] = None


class OpponentSpeechResult(BaseModel):
    speech_text: str
    argument_labels: List[str] = Field(default_factory=list)
    responses_made: List[str] = Field(default_factory=list)
    arguments_extended: List[str] = Field(default_factory=list)
    arguments_dropped: List[str] = Field(default_factory=list)
    evidence_references: List[OpponentEvidenceReference] = Field(default_factory=list)
    weighing_used: Optional[str] = None
    strategic_goal: str = ""
    estimated_speaking_time: int = 0
    is_fallback: bool = False


# ── Post-round drills ─────────────────────────────────────────────────────────


class RoundDrillSource(BaseModel):
    round_id: str
    speech_phase: str
    argument_label: Optional[str] = None
    card_id: Optional[str] = None
    weakness_description: str


class RoundDrill(BaseModel):
    id: str
    round_id: str
    drill_id: str
    source: RoundDrillSource
    skill_target: str
    title: str
    prompt: str
    success_criteria: List[str] = Field(default_factory=list)
    time_limit_seconds: int = 90
    created_at: str


# ── Adaptation review ─────────────────────────────────────────────────────────


class RoundAdaptationReview(BaseModel):
    id: str
    round_id: str
    judge_type: str
    adaptation_successes: List[str] = Field(default_factory=list)
    adaptation_failures: List[str] = Field(default_factory=list)
    how_other_judge_sees: Optional[str] = None
    alternate_judge_type: Optional[str] = None
    created_at: str


# ── API request/response models ───────────────────────────────────────────────


class CreateRoundRequest(BaseModel):
    config: RoundSimulationConfig
    team_id: Optional[str] = None


class LoadPreparationRequest(BaseModel):
    round_id: str
    prep_workspace_id: Optional[str] = None
    blockfile_ids: List[str] = Field(default_factory=list)
    frontline_ids: List[str] = Field(default_factory=list)
    card_ids: List[str] = Field(default_factory=list)


class SubmitStudentSpeechRequest(BaseModel):
    round_id: str
    phase: RoundPhaseType
    audio_url: Optional[str] = None
    transcript_text: Optional[str] = None
    typed_outline: Optional[str] = None
    idempotency_key: Optional[str] = None


class GenerateOpponentSpeechRequest(BaseModel):
    round_id: str
    phase: RoundPhaseType
    idempotency_key: Optional[str] = None


class AdvancePhaseRequest(BaseModel):
    round_id: str
    target_phase: Optional[RoundPhaseType] = None
    practice_override: bool = False


class StudentCrossfireQuestionRequest(BaseModel):
    """Student asks the AI opponent a question."""
    round_id: str
    question: str


class RoundStateResponse(BaseModel):
    simulation: RoundSimulation
    current_phase: RoundPhaseType
    phase_label: str
    student_speaks_now: bool
    time_limit_seconds: int
    phase_started_at: Optional[str] = None
    speeches: List[RoundSpeech] = Field(default_factory=list)
    flow_arguments: List[RoundArgument] = Field(default_factory=list)
    active_crossfire: Optional[List[CrossfireExchange]] = None
    decision: Optional[RoundDecision] = None
    coaching_hint: Optional[str] = None


class GenerateDecisionRequest(BaseModel):
    round_id: str
    judge_type: Optional[str] = None


class GenerateDrillsRequest(BaseModel):
    round_id: str


class CreateAdaptationReviewRequest(BaseModel):
    round_id: str
    judge_type: str
    decision_id: Optional[str] = None
    alternate_judge_type: Optional[str] = None


class RoundHistoryItem(BaseModel):
    id: str
    resolution: str
    student_side: str
    judge_type: str
    status: str
    winner: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ── Coach review ──────────────────────────────────────────────────────────────


class CoachAnnotation(BaseModel):
    id: str
    round_id: str
    coach_id: str
    annotation_type: str
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    content: str
    is_correction: bool = False
    finding_id: Optional[str] = None
    created_at: str


class AutomatedFindingRating(BaseModel):
    id: str
    round_id: str
    finding_id: str
    rater_id: str
    rating: str
    note: Optional[str] = None
    created_at: str


class AddAnnotationRequest(BaseModel):
    round_id: str
    annotation_type: str
    content: str
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    is_correction: bool = False
    finding_id: Optional[str] = None


class RateFindingRequest(BaseModel):
    finding_id: str
    rating: str
    note: Optional[str] = None


# ── Replay ────────────────────────────────────────────────────────────────────


class ReplayPhase(BaseModel):
    phase: str
    phase_label: str
    speaker_label: str
    transcript_preview: str = ""
    flow_events: List[Dict[str, Any]] = Field(default_factory=list)
    arguments_changed: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_used: List[str] = Field(default_factory=list)
    legality_violations: List[str] = Field(default_factory=list)
    turning_points: List[Dict[str, Any]] = Field(default_factory=list)


class TurningPoint(BaseModel):
    phase: str
    type: str
    description: str
    argument_label: Optional[str] = None
    severity: str = "notable"


# ── Round quality metadata ────────────────────────────────────────────────────


class RoundQualityReport(BaseModel):
    round_id: str
    drop_detection_precision: Optional[float] = None
    concession_precision: Optional[float] = None
    evidence_reference_accuracy: Optional[float] = None
    decision_confidence: str = "contested"
    hallucination_risk: str = "low"
    overall_quality: str = "good"
    warnings: List[str] = Field(default_factory=list)
    generated_at: str
