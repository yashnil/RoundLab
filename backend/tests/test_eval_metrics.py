"""Unit tests for the eval metrics module.

All tests are pure — no LLM calls, no network, no Supabase.
"""

import sys
from pathlib import Path

# Ensure evals/ is importable from the backend root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from evals.metrics import (
    check_required_issues,
    detect_hallucinated_evidence,
    normalize_drill_type,
    normalize_issue_type,
    sample_passes,
    score_argument_coverage,
    score_drill_relevance,
    score_issue_detection,
    summarize_eval_result,
)
from evals.models import (
    EvalSampleResult,
    ExpectedArgumentComponent,
    ExpectedIssue,
    IssueDetectionMetrics,
)


# ── normalize_issue_type ───────────────────────────────────────────────────────

class TestNormalizeIssueType:
    def test_valid_type_passthrough(self):
        assert normalize_issue_type("missing_warrant") == "missing_warrant"

    def test_strips_whitespace(self):
        assert normalize_issue_type("  no_weighing  ") == "no_weighing"

    def test_converts_hyphens(self):
        assert normalize_issue_type("missing-warrant") == "missing_warrant"

    def test_converts_spaces(self):
        assert normalize_issue_type("missing warrant") == "missing_warrant"

    def test_lowercases(self):
        assert normalize_issue_type("DROPPED_ARGUMENT") == "dropped_argument"

    def test_invalid_returns_none(self):
        assert normalize_issue_type("made_up_type") is None

    def test_empty_returns_none(self):
        assert normalize_issue_type("") is None

    # synonym mapping tests
    def test_synonym_weak_citation(self):
        assert normalize_issue_type("weak_citation") == "weak_evidence"

    def test_synonym_unclear_citation(self):
        assert normalize_issue_type("unclear_citation") == "weak_evidence"

    def test_synonym_missing_evidence(self):
        assert normalize_issue_type("missing_evidence") == "weak_evidence"

    def test_synonym_insufficient_evidence(self):
        assert normalize_issue_type("insufficient_evidence") == "weak_evidence"

    def test_synonym_circular_argument(self):
        assert normalize_issue_type("circular_argument") == "missing_warrant"

    def test_synonym_assertion_only(self):
        assert normalize_issue_type("assertion_only") == "missing_warrant"

    def test_synonym_no_warrant(self):
        assert normalize_issue_type("no_warrant") == "missing_warrant"

    def test_synonym_missing_internal_link(self):
        assert normalize_issue_type("missing_internal_link") == "missing_warrant"

    def test_synonym_no_comparative_weighing(self):
        assert normalize_issue_type("no_comparative_weighing") == "no_weighing"

    def test_synonym_missing_impact_calculus(self):
        assert normalize_issue_type("missing_impact_calculus") == "no_weighing"

    def test_synonym_unanswered_contention(self):
        assert normalize_issue_type("unanswered_contention") == "dropped_argument"

    def test_synonym_no_direct_engagement(self):
        assert normalize_issue_type("no_direct_engagement") == "no_clash"

    def test_synonym_late_breaking_argument(self):
        assert normalize_issue_type("late_breaking_argument") == "new_argument"

    def test_synonym_new_evidence(self):
        assert normalize_issue_type("new_evidence") == "new_argument"

    def test_synonym_new_material(self):
        assert normalize_issue_type("new_material") == "new_argument"

    def test_synonym_new_analysis(self):
        assert normalize_issue_type("new_analysis") == "new_argument"

    def test_synonym_late_evidence(self):
        assert normalize_issue_type("late_evidence") == "new_argument"

    def test_synonym_failure_to_engage(self):
        assert normalize_issue_type("failure_to_engage") == "no_clash"

    def test_synonym_no_refutation(self):
        assert normalize_issue_type("no_refutation") == "no_clash"

    def test_synonym_no_direct_response(self):
        assert normalize_issue_type("no_direct_response") == "no_clash"

    def test_synonym_undeveloped_impact(self):
        assert normalize_issue_type("undeveloped_impact") == "unclear_impact"

    def test_synonym_no_impact(self):
        assert normalize_issue_type("no_impact") == "unclear_impact"

    def test_synonym_incomplete_extension(self):
        assert normalize_issue_type("incomplete_extension") == "weak_extension"

    def test_synonym_card_attribution_unclear(self):
        assert normalize_issue_type("card_attribution_unclear") == "weak_evidence"

    def test_synonym_space_variant_normalized(self):
        """Synonyms with spaces are normalized before lookup."""
        assert normalize_issue_type("missing internal link") == "missing_warrant"

    def test_synonym_hyphen_variant_normalized(self):
        assert normalize_issue_type("late-breaking-argument") == "new_argument"


# ── normalize_drill_type ───────────────────────────────────────────────────────

class TestNormalizeDrillType:
    def test_valid(self):
        assert normalize_drill_type("weighing") == "weighing"

    def test_invalid_returns_none(self):
        assert normalize_drill_type("fake_skill") is None

    def test_hyphen_variant(self):
        assert normalize_drill_type("line-by-line") == "line_by_line"

    def test_synonym_impact_calculus(self):
        assert normalize_drill_type("impact_calculus") == "weighing"

    def test_synonym_impact_comparison(self):
        assert normalize_drill_type("impact_comparison") == "weighing"

    def test_synonym_judge_calibration(self):
        assert normalize_drill_type("judge_calibration") == "judge_adaptation"


# ── score_issue_detection ──────────────────────────────────────────────────────

class TestScoreIssueDetection:
    def _make_expected(self, *types: str) -> list[ExpectedIssue]:
        return [ExpectedIssue(issue_type=t, severity="medium") for t in types]

    def _make_actual(self, *types: str) -> list[dict]:
        return [{"issue_type": t, "severity": "medium", "title": t} for t in types]

    def test_perfect_match(self):
        expected = self._make_expected("missing_warrant", "no_weighing")
        actual   = self._make_actual("missing_warrant", "no_weighing")
        m = score_issue_detection(expected, actual)
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0
        assert m.true_positives == 2
        assert m.false_positives == 0
        assert m.false_negatives == 0

    def test_all_false_positives_no_expected(self):
        expected = []
        actual   = self._make_actual("missing_warrant", "no_weighing")
        m = score_issue_detection(expected, actual)
        # Precision: 0/2; Recall: 1.0 (nothing expected so nothing missed)
        assert m.precision == 0.0
        assert m.recall == 1.0
        assert m.false_positives == 2
        assert m.true_positives == 0

    def test_all_false_negatives_no_actual(self):
        expected = self._make_expected("missing_warrant", "no_weighing")
        actual   = []
        m = score_issue_detection(expected, actual)
        assert m.recall == 0.0
        assert m.false_negatives == 2
        assert m.true_positives == 0

    def test_hallucinated_extra_issue_lowers_precision(self):
        expected = self._make_expected("missing_warrant")
        actual   = self._make_actual("missing_warrant", "delivery")  # delivery is extra
        m = score_issue_detection(expected, actual)
        assert m.true_positives == 1
        assert m.false_positives == 1
        assert m.precision == pytest.approx(0.5)

    def test_missed_required_issue_lowers_recall(self):
        expected = self._make_expected("missing_warrant", "no_weighing")
        actual   = self._make_actual("no_weighing")  # missing_warrant not detected
        m = score_issue_detection(expected, actual)
        assert m.false_negatives == 1
        assert m.recall == pytest.approx(0.5)

    def test_f1_zero_on_no_match(self):
        expected = self._make_expected("missing_warrant")
        actual   = self._make_actual("no_clash")  # wrong type
        m = score_issue_detection(expected, actual)
        assert m.true_positives == 0
        assert m.f1 == 0.0

    def test_perfect_precision_with_empty_actual(self):
        """No actual issues → precision is 1.0 (no false positives) but recall is 0."""
        expected = self._make_expected("missing_warrant")
        m = score_issue_detection(expected, [])
        assert m.precision == 1.0
        assert m.recall == 0.0

    def test_zero_expected_zero_actual(self):
        """Strong speech with 0 expected and 0 actual → perfect score."""
        m = score_issue_detection([], [])
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0

    def test_zero_expected_nonzero_actual_lowers_precision(self):
        """Zero expected issues but model generates FPs → precision drops."""
        m = score_issue_detection([], self._make_actual("missing_warrant", "unclear_impact"))
        assert m.precision == 0.0
        assert m.false_positives == 2

    def test_synonym_in_actual_counts_as_tp(self):
        """Synonyms in actual issues normalize and match expected types."""
        expected = self._make_expected("weak_evidence")
        actual   = [{"issue_type": "weak_citation", "severity": "high", "title": "t"}]
        m = score_issue_detection(expected, actual)
        assert m.true_positives == 1
        assert m.false_positives == 0
        assert m.f1 == 1.0


# ── score_drill_relevance ──────────────────────────────────────────────────────

class TestScoreDrillRelevance:
    def test_full_coverage(self):
        expected = ["weighing", "warranting"]
        actual   = [{"skill_target": "weighing"}, {"skill_target": "warranting"}, {"skill_target": "drops"}]
        assert score_drill_relevance(expected, actual) == 1.0

    def test_partial_coverage(self):
        expected = ["weighing", "warranting", "drops"]
        actual   = [{"skill_target": "weighing"}]
        assert score_drill_relevance(expected, actual) == pytest.approx(1/3, abs=0.001)

    def test_no_expected_returns_one(self):
        assert score_drill_relevance([], [{"skill_target": "weighing"}]) == 1.0

    def test_no_actual_returns_zero(self):
        assert score_drill_relevance(["weighing"], []) == 0.0

    def test_generated_expected_type_is_relevant(self):
        """Expected drill type in actual drills counts as relevant."""
        expected = ["drops"]
        actual   = [{"skill_target": "drops"}]
        assert score_drill_relevance(expected, actual) == 1.0


# ── score_argument_coverage ────────────────────────────────────────────────────

class TestScoreArgumentCoverage:
    def _make_actual_args(self, *labels: str) -> list[dict]:
        return [{"label": lbl, "claim": "test", "warrant": "test", "evidence": None, "impact": "test", "argument_type": "offense"} for lbl in labels]

    def test_full_coverage(self):
        expected = [
            ExpectedArgumentComponent(label_hint="C1"),
            ExpectedArgumentComponent(label_hint="C2"),
        ]
        actual = self._make_actual_args("C1: Economic Burden", "C2: Escalation Risk")
        assert score_argument_coverage(expected, actual) == 1.0

    def test_partial_coverage(self):
        expected = [
            ExpectedArgumentComponent(label_hint="C1"),
            ExpectedArgumentComponent(label_hint="C2"),
        ]
        actual = self._make_actual_args("C1: Economic Burden")  # C2 missing
        assert score_argument_coverage(expected, actual) == pytest.approx(0.5)

    def test_no_expected_returns_one(self):
        actual = self._make_actual_args("C1: Test")
        assert score_argument_coverage([], actual) == 1.0

    def test_case_insensitive_matching(self):
        expected = [ExpectedArgumentComponent(label_hint="rebuttal")]
        actual   = self._make_actual_args("Rebuttal: Direct Response")
        assert score_argument_coverage(expected, actual) == 1.0


# ── detect_hallucinated_evidence ───────────────────────────────────────────────

class TestDetectHallucinatedEvidence:
    def test_named_source_not_flagged(self):
        args = [{"label": "C1", "evidence": "RAND Corporation 2023 finds that..."}]
        assert detect_hallucinated_evidence(args) == []

    def test_vague_source_flagged(self):
        args = [{"label": "C1", "evidence": "Studies show that basing costs are high"}]
        flagged = detect_hallucinated_evidence(args)
        assert "C1" in flagged

    def test_no_evidence_not_flagged(self):
        args = [{"label": "C1", "evidence": None}]
        assert detect_hallucinated_evidence(args) == []

    def test_experts_say_flagged(self):
        args = [{"label": "C2", "evidence": "Experts say that the presence is destabilizing"}]
        flagged = detect_hallucinated_evidence(args)
        assert "C2" in flagged

    def test_multiple_flagged(self):
        args = [
            {"label": "C1", "evidence": "Research shows costs are high"},
            {"label": "C2", "evidence": "RAND Corporation 2023"},
        ]
        flagged = detect_hallucinated_evidence(args)
        assert "C1" in flagged
        assert "C2" not in flagged


# ── check_required_issues ──────────────────────────────────────────────────────

class TestCheckRequiredIssues:
    def test_required_issue_detected(self):
        expected = [ExpectedIssue(issue_type="missing_warrant", required=True)]
        actual   = [{"issue_type": "missing_warrant"}]
        missed   = check_required_issues(expected, actual)
        assert missed == []

    def test_required_issue_missed(self):
        expected = [ExpectedIssue(issue_type="missing_warrant", required=True)]
        actual   = [{"issue_type": "no_clash"}]  # wrong type
        missed   = check_required_issues(expected, actual)
        assert "missing_warrant" in missed

    def test_non_required_not_in_missed(self):
        expected = [ExpectedIssue(issue_type="missing_warrant", required=False)]
        actual   = []
        missed   = check_required_issues(expected, actual)
        assert missed == []


# ── sample_passes ──────────────────────────────────────────────────────────────

class TestSamplePasses:
    def _good_metrics(self) -> IssueDetectionMetrics:
        return IssueDetectionMetrics(
            precision=1.0, recall=1.0, f1=1.0,
            true_positives=2, false_positives=0, false_negatives=0,
        )

    def test_passes_with_good_metrics(self):
        assert sample_passes(self._good_metrics(), 1.0, 1.0, []) is True

    def test_fails_when_required_issue_missed(self):
        assert sample_passes(self._good_metrics(), 1.0, 1.0, ["missing_warrant"]) is False

    def test_fails_when_f1_below_threshold(self):
        bad = IssueDetectionMetrics(
            precision=0.0, recall=0.0, f1=0.0,
            true_positives=0, false_positives=3, false_negatives=2,
        )
        assert sample_passes(bad, 1.0, 1.0, []) is False

    def test_fails_when_coverage_below_threshold(self):
        assert sample_passes(self._good_metrics(), 0.0, 1.0, []) is False


# ── summarize_eval_result ──────────────────────────────────────────────────────

class TestSummarizeEvalResult:
    def _make_result(self, passed: bool, missed: list[str] = []) -> EvalSampleResult:
        return EvalSampleResult(
            fixture_id="test_fixture",
            fixture_title="Test",
            speech_type="constructive",
            mock_mode=True,
            issue_metrics=IssueDetectionMetrics(
                precision=1.0, recall=1.0, f1=1.0,
                true_positives=1, false_positives=0, false_negatives=0,
            ),
            argument_coverage=1.0,
            drill_relevance=1.0,
            hallucinated_evidence_count=0,
            required_issues_missed=missed,
            passed=passed,
            timestamp="2026-06-01T00:00:00Z",
        )

    def test_pass_contains_tick(self):
        summary = summarize_eval_result(self._make_result(True))
        assert "PASS" in summary

    def test_fail_contains_cross(self):
        summary = summarize_eval_result(self._make_result(False))
        assert "FAIL" in summary

    def test_missed_issues_shown(self):
        summary = summarize_eval_result(self._make_result(False, ["missing_warrant"]))
        assert "missing_warrant" in summary
