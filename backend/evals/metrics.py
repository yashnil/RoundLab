"""Deterministic, pure scoring helpers for the RoundLab eval harness.

No LLM calls. No network. Every function here is unit-testable in isolation.
"""

from __future__ import annotations

from evals.models import (
    EvalSampleResult,
    ExpectedArgumentComponent,
    ExpectedIssue,
    IssueDetectionMetrics,
    VALID_ISSUE_TYPES,
    VALID_DRILL_TYPES,
)


# ── Normalization ──────────────────────────────────────────────────────────────

# Maps common LLM-generated synonyms to canonical issue_type values.
# Covers hyphen/underscore/space variants automatically (handled before lookup).
_ISSUE_SYNONYMS: dict[str, str] = {
    # weak_evidence
    "weak_citation": "weak_evidence",
    "unclear_citation": "weak_evidence",
    "missing_evidence": "weak_evidence",
    "insufficient_evidence": "weak_evidence",
    "unattributed_evidence": "weak_evidence",
    "vague_evidence": "weak_evidence",
    "unsupported_evidence": "weak_evidence",
    "no_evidence": "weak_evidence",
    "poor_evidence": "weak_evidence",
    "card_attribution_unclear": "weak_evidence",
    # missing_warrant
    "circular_argument": "missing_warrant",
    "unsupported_claim": "missing_warrant",
    "assertion_only": "missing_warrant",
    "no_warrant": "missing_warrant",
    "thin_warrant": "missing_warrant",
    "weak_warrant": "missing_warrant",
    "missing_link": "missing_warrant",
    "missing_internal_link": "missing_warrant",
    "no_internal_link": "missing_warrant",
    # no_weighing
    "no_comparative_weighing": "no_weighing",
    "missing_weighing": "no_weighing",
    "no_impact_comparison": "no_weighing",
    "no_impact_calculus": "no_weighing",
    "missing_impact_calculus": "no_weighing",
    "insufficient_weighing": "no_weighing",
    # dropped_argument
    "unanswered_contention": "dropped_argument",
    "unanswered_argument": "dropped_argument",
    "dropped_contention": "dropped_argument",
    "dropped_offense": "dropped_argument",
    "unaddressed_argument": "dropped_argument",
    # no_clash
    "no_direct_engagement": "no_clash",
    "missing_clash": "no_clash",
    "failure_to_clash": "no_clash",
    "no_engagement": "no_clash",
    "lack_of_clash": "no_clash",
    "failure_to_engage": "no_clash",
    "no_direct_response": "no_clash",
    "no_refutation": "no_clash",
    "no_response_to_opponent": "no_clash",
    "no_rebuttal_to_opponent": "no_clash",
    # new_argument
    "late_breaking_argument": "new_argument",
    "new_evidence": "new_argument",
    "new_contention": "new_argument",
    "late_argument": "new_argument",
    "new_evidence_in_ff": "new_argument",
    "new_evidence_in_final_focus": "new_argument",
    "late_introduction": "new_argument",
    "late_evidence": "new_argument",
    "new_material": "new_argument",
    "introduced_new_argument": "new_argument",
    "new_claim": "new_argument",
    "new_analysis": "new_argument",
    # unclear_impact
    "missing_impact": "unclear_impact",
    "undeveloped_impact": "unclear_impact",
    "no_impact": "unclear_impact",
    "vague_impact": "unclear_impact",
    "weak_impact": "unclear_impact",
    "underdeveloped_impact": "unclear_impact",
    # weak_extension
    "poor_extension": "weak_extension",
    "incomplete_extension": "weak_extension",
    "missing_extension": "weak_extension",
    "no_extension": "weak_extension",
}

_DRILL_SYNONYMS: dict[str, str] = {
    "impact_comparison": "weighing",
    "impact_calculus": "weighing",
    "warrant_building": "warranting",
    "drop_coverage": "drops",
    "argument_extension": "extensions",
    "source_use": "evidence",
    "direct_clash": "clash",
    "judge_calibration": "judge_adaptation",
}


def normalize_issue_type(raw: str) -> str | None:
    """Canonicalize an issue_type string.

    Returns the valid issue_type string, or None if unrecognizable.
    Handles hyphen/space variants, strips whitespace, and resolves synonyms.
    """
    if not raw:
        return None
    cleaned = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in VALID_ISSUE_TYPES:
        return cleaned
    # Check synonym map
    if cleaned in _ISSUE_SYNONYMS:
        return _ISSUE_SYNONYMS[cleaned]
    return None


def normalize_drill_type(raw: str) -> str | None:
    """Canonicalize a skill_target / drill type string."""
    if not raw:
        return None
    cleaned = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in VALID_DRILL_TYPES:
        return cleaned
    if cleaned in _DRILL_SYNONYMS:
        return _DRILL_SYNONYMS[cleaned]
    return None


# ── Issue detection ────────────────────────────────────────────────────────────

def score_issue_detection(
    expected: list[ExpectedIssue],
    actual_issues: list[dict],
) -> IssueDetectionMetrics:
    """Compute precision/recall/F1 for structured issue detection.

    Matching: exact issue_type match (after normalization).
    Each expected issue can be matched by at most one actual issue.
    """
    expected_types = [normalize_issue_type(e.issue_type) for e in expected]
    expected_types = [t for t in expected_types if t]  # drop invalid

    actual_types: list[str] = []
    for issue in actual_issues:
        raw = issue.get("issue_type", "")
        t = normalize_issue_type(raw)
        if t:
            actual_types.append(t)

    # Count true/false positives using a multiset approach
    remaining_expected = list(expected_types)
    true_positives = 0
    false_positives = 0

    for at in actual_types:
        if at in remaining_expected:
            true_positives += 1
            remaining_expected.remove(at)
        else:
            false_positives += 1

    false_negatives = len(remaining_expected)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
    recall    = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return IssueDetectionMetrics(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


# ── Drill relevance ────────────────────────────────────────────────────────────

def score_drill_relevance(
    expected_drill_types: list[str],
    actual_drills: list[dict],
) -> float:
    """Fraction of expected drill skill targets covered by actual generated drills.

    Returns 1.0 if expected_drill_types is empty (nothing to cover).
    """
    if not expected_drill_types:
        return 1.0

    expected_norm = {normalize_drill_type(t) for t in expected_drill_types if t}
    expected_norm.discard(None)

    actual_norm: set[str | None] = set()
    for drill in actual_drills:
        t = normalize_drill_type(drill.get("skill_target", ""))
        if t:
            actual_norm.add(t)

    if not expected_norm:
        return 1.0

    covered = expected_norm & actual_norm
    return round(len(covered) / len(expected_norm), 4)


# ── Argument component coverage ────────────────────────────────────────────────

def score_argument_coverage(
    expected_components: list[ExpectedArgumentComponent],
    actual_arguments: list[dict],
) -> float:
    """Fraction of expected argument components found in actual extracted arguments.

    Match: any actual argument whose label contains label_hint (case-insensitive).
    Returns 1.0 if expected_components is empty.
    """
    if not expected_components:
        return 1.0

    matched = 0
    actual_labels = [str(a.get("label", "")).lower() for a in actual_arguments]

    for comp in expected_components:
        hint = comp.label_hint.lower()
        if any(hint in lab for lab in actual_labels):
            matched += 1

    return round(matched / len(expected_components), 4)


# ── Hallucination detection ────────────────────────────────────────────────────

# Phrases that suggest invented or vague evidence claims
_HALLUCINATION_SIGNALS = [
    "research shows",
    "studies show",
    "experts say",
    "scientists believe",
    "it is widely known",
    "evidence suggests",
    "according to unnamed",
    "some reports",
    "various scholars",
    "unnamed sources",
]

def detect_hallucinated_evidence(arguments: list[dict]) -> list[str]:
    """Return labels of arguments whose evidence field contains hallucination signals.

    A "hallucinated" evidence claim uses vague attributions instead of named sources.
    This is a heuristic, not a definitive detector — false positives are possible.
    """
    flagged: list[str] = []
    for arg in arguments:
        evidence = str(arg.get("evidence") or "").lower()
        if not evidence:
            continue
        if any(signal in evidence for signal in _HALLUCINATION_SIGNALS):
            flagged.append(str(arg.get("label", "<unlabeled>")))
    return flagged


# ── Sample pass/fail ───────────────────────────────────────────────────────────

def check_required_issues(
    expected: list[ExpectedIssue],
    actual_issues: list[dict],
) -> list[str]:
    """Return issue_types from required=True expected issues that were NOT detected."""
    actual_types = {normalize_issue_type(i.get("issue_type", "")) for i in actual_issues}
    actual_types.discard(None)

    missed: list[str] = []
    for exp in expected:
        if exp.required:
            t = normalize_issue_type(exp.issue_type)
            if t and t not in actual_types:
                missed.append(t)
    return missed


def sample_passes(
    issue_metrics: IssueDetectionMetrics,
    argument_coverage: float,
    drill_relevance: float,
    required_issues_missed: list[str],
    f1_threshold: float = 0.5,
    coverage_threshold: float = 0.5,
) -> bool:
    """Determine pass/fail for a single eval sample.

    Fails if:
    - Any required issue was not detected
    - Issue F1 < f1_threshold
    - Argument coverage < coverage_threshold
    """
    if required_issues_missed:
        return False
    if issue_metrics.f1 < f1_threshold:
        return False
    if argument_coverage < coverage_threshold:
        return False
    return True


# ── Summary ────────────────────────────────────────────────────────────────────

def summarize_eval_result(result: "EvalSampleResult") -> str:
    """Return a one-line human-readable summary of a sample result."""
    status = "✓ PASS" if result.passed else "✗ FAIL"
    return (
        f"{status} [{result.fixture_id}] "
        f"F1={result.issue_metrics.f1:.2f} "
        f"cov={result.argument_coverage:.2f} "
        f"drill={result.drill_relevance:.2f}"
        + (f" | missed: {', '.join(result.required_issues_missed)}" if result.required_issues_missed else "")
        + (f" | error: {result.error}" if result.error else "")
    )
