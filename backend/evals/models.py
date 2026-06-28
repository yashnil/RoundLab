"""Pydantic models for the Dissio evaluation harness.

EvalSpeechFixture  — labeled ground-truth speech (what we expect the AI to produce)
IssueDetectionMetrics — precision/recall/F1 for structured_issues
EvalSampleResult   — result for one fixture after pipeline run
EvalRunResult      — aggregate result for a full eval run
"""

from typing import Optional
from pydantic import BaseModel


# ── Valid issue types (must match backend feedback_generation.DebateIssue) ────

VALID_ISSUE_TYPES: frozenset[str] = frozenset({
    "missing_warrant",
    "weak_evidence",
    "unclear_impact",
    "no_weighing",
    "dropped_argument",
    "weak_extension",
    "no_clash",
    "new_argument",
    "organization",
    "delivery",
})

VALID_DRILL_TYPES: frozenset[str] = frozenset({
    "weighing",
    "warranting",
    "drops",
    "extensions",
    "evidence",
    "clash",
    "judge_adaptation",
    "collapse",
    "line_by_line",
})

VALID_SPEECH_TYPES: frozenset[str] = frozenset({
    "constructive",
    "rebuttal",
    "summary",
    "final_focus",
    "crossfire",
})


# ── Fixture input models ───────────────────────────────────────────────────────

class ExpectedIssue(BaseModel):
    """One labeled expected issue in a fixture.

    required=True means this issue MUST be detected for the sample to pass.
    All expected issues (required or not) contribute to recall.
    """

    issue_type: str
    severity: str = "medium"
    required: bool = False
    expected_drill_type: Optional[str] = None


class ExpectedArgumentComponent(BaseModel):
    """Minimal description of one expected argument extracted from the speech."""

    label_hint: str
    """Partial label to match against, e.g. 'C1', 'Rebuttal'. Case-insensitive substring match."""

    has_claim: bool = True
    has_warrant: bool = True
    has_evidence: bool = False
    has_impact: bool = True

    # Optional sample text — used by mock runner to construct fake responses
    example_claim: str = ""
    example_warrant: str = ""
    example_evidence: Optional[str] = None
    example_impact: str = ""


class EvalSpeechFixture(BaseModel):
    """Fully labeled speech fixture used as ground truth for eval."""

    id: str
    title: str
    event_type: str = "Public Forum"
    speech_type: str
    side: Optional[str] = None
    judge_type: Optional[str] = None
    topic: Optional[str] = None
    transcript: str
    expected_issues: list[ExpectedIssue] = []
    expected_argument_components: list[ExpectedArgumentComponent] = []
    expected_drill_types: list[str] = []
    notes: str = ""


# ── Result models ──────────────────────────────────────────────────────────────

class IssueDetectionMetrics(BaseModel):
    """Precision/recall/F1 for structured_issues detection."""

    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def summary(self) -> str:
        return f"P={self.precision:.2f} R={self.recall:.2f} F1={self.f1:.2f} (TP={self.true_positives} FP={self.false_positives} FN={self.false_negatives})"


class EvalSampleResult(BaseModel):
    """Eval result for one fixture."""

    fixture_id: str
    fixture_title: str
    speech_type: str
    mock_mode: bool

    issue_metrics: IssueDetectionMetrics
    argument_coverage: float  # 0.0 – 1.0
    drill_relevance: float    # 0.0 – 1.0
    hallucinated_evidence_count: int

    required_issues_missed: list[str] = []
    passed: bool

    # Diagnostic fields — populated when actual pipeline output is available
    predicted_issue_types: list[str] = []
    """Normalized issue_types the model actually generated (empty in some stored results)."""

    detected_signal_types: list[str] = []
    """Issue types detected by the deterministic DebateSignalDetector before the LLM call."""

    quality_gate_budget: int = -1
    """Recommended issue budget from the quality gate (-1 = not computed)."""

    error: Optional[str] = None
    timestamp: str


class EvalRunResult(BaseModel):
    """Aggregate result for a full eval run."""

    run_id: str
    timestamp: str
    mock_mode: bool
    total_fixtures: int
    passed: int
    failed: int

    avg_issue_precision: float
    avg_issue_recall: float
    avg_issue_f1: float
    avg_argument_coverage: float
    avg_drill_relevance: float
    total_hallucinated_evidence: int

    samples: list[EvalSampleResult]
