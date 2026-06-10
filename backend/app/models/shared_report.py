from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class CreateShareRequest(BaseModel):
    user_id: str
    include_transcript: bool = True
    include_flow: bool = True
    include_feedback: bool = True
    include_drills: bool = True
    include_delivery: bool = True
    include_evidence_summary: bool = False
    include_improvement: bool = True
    expires_in_days: Optional[int] = None  # None = no expiry; 7 or 30


class UpdateShareRequest(BaseModel):
    user_id: str
    include_transcript: Optional[bool] = None
    include_flow: Optional[bool] = None
    include_feedback: Optional[bool] = None
    include_drills: Optional[bool] = None
    include_delivery: Optional[bool] = None
    include_evidence_summary: Optional[bool] = None
    include_improvement: Optional[bool] = None
    expires_in_days: Optional[int] = None


class ShareResponse(BaseModel):
    id: str
    share_token: str
    include_transcript: bool
    include_flow: bool
    include_feedback: bool
    include_drills: bool
    include_delivery: bool
    include_evidence_summary: bool
    include_improvement: bool
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ── Public-safe shared report payload ─────────────────────────────────────────

class SharedReportFeedback(BaseModel):
    overall_score: Optional[int]
    scores: Optional[dict[str, int]]
    summary: Optional[str]
    strengths: list[str]
    weaknesses: list[str]
    top_3_priorities: Optional[list[str]]
    structured_issues: Optional[list[dict[str, Any]]]


class SharedReportArgument(BaseModel):
    label: str
    claim: str
    warrant: str
    evidence: Optional[str]
    impact: str
    argument_type: str


class SharedReportDrill(BaseModel):
    title: str
    description: Optional[str]
    skill_target: str
    prompt: str
    success_criteria: list[str]
    difficulty: str


class SharedReportDelivery(BaseModel):
    words_per_minute: Optional[float]
    filler_word_count: Optional[int]
    delivery_score: Optional[int]
    pacing_band: Optional[str]
    repeated_phrases_json: Optional[list[dict[str, Any]]]


class SharedReportEvidenceSummary(BaseModel):
    supported_count: int
    partially_supported_count: int
    unsupported_count: int
    unverifiable_count: int
    top_issues: list[dict[str, Any]]  # claim_text, support_level, explanation only


class SharedReportComparison(BaseModel):
    original_overall_score: Optional[int]
    new_overall_score: Optional[int]
    overall_delta: Optional[int]
    original_delivery_score: Optional[int]
    new_delivery_score: Optional[int]
    delivery_score_delta: Optional[int]
    original_wpm: Optional[float]
    new_wpm: Optional[float]
    wpm_delta: Optional[float]
    original_filler_count: Optional[int]
    new_filler_count: Optional[int]
    filler_delta: Optional[int]
    summary: str


class SharedReportIncludeFlags(BaseModel):
    transcript: bool
    flow: bool
    feedback: bool
    drills: bool
    delivery: bool
    evidence_summary: bool
    improvement: bool


class SharedReportPayload(BaseModel):
    token: str
    speech_type: str
    side: Optional[str]
    judge_type: Optional[str]
    topic: Optional[str]
    created_at: str
    feedback: Optional[SharedReportFeedback]
    arguments: Optional[list[SharedReportArgument]]
    drills: Optional[list[SharedReportDrill]]
    delivery: Optional[SharedReportDelivery]
    transcript_text: Optional[str]
    evidence_summary: Optional[SharedReportEvidenceSummary]
    comparison: Optional[SharedReportComparison]
    include_flags: SharedReportIncludeFlags
