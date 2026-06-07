"""
Schema validation tests for new Pass 4 data types.
Tests that Pydantic models correctly validate the new fields
and handle partial/missing data gracefully.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.argument_map import ArgumentItem, ArgumentMapRow
from app.models.drill import DrillRow
from app.services.feedback_generation import DebateIssue, _FeedbackOutput, ScoreExplanation
from app.models.feedback_report import FeedbackScores


# ── ArgumentItem with id ───────────────────────────────────────────────────────

class TestArgumentItem:
    def test_basic_valid(self):
        item = ArgumentItem(
            label="C1: Economic Growth",
            claim="Tariffs harm economic growth.",
            warrant="Higher costs reduce trade volumes.",
            evidence="IMF 2023 study",
            impact="$400B reduction in global GDP.",
            argument_type="offense",
            issues=[],
            confidence=0.85,
        )
        assert item.label == "C1: Economic Growth"
        assert item.id is None  # id is optional, None by default

    def test_id_assignment(self):
        item = ArgumentItem(
            label="C2: Poverty",
            claim="Tariffs increase poverty.",
            warrant="Higher prices reduce purchasing power.",
            evidence=None,
            impact="200M pushed below poverty line.",
            argument_type="offense",
            issues=["missing warrant"],
            confidence=0.6,
            id="arg_1",
        )
        assert item.id == "arg_1"

    def test_missing_evidence_is_none(self):
        item = ArgumentItem(
            label="Weighing: Magnitude",
            claim="Our impact is larger.",
            warrant="Scale of harm is 10x their impact.",
            evidence=None,
            impact="Millions affected vs. thousands.",
            argument_type="weighing",
            issues=[],
            confidence=0.75,
        )
        assert item.evidence is None

    def test_invalid_argument_type_rejected(self):
        with pytest.raises(ValidationError):
            ArgumentItem(
                label="Bad arg",
                claim="claim",
                warrant="warrant",
                impact="impact",
                argument_type="invalid_type",  # type: ignore[arg-type]
                issues=[],
                confidence=None,
            )

    def test_issues_defaults_to_empty(self):
        item = ArgumentItem(
            label="Defense",
            claim="Not true.",
            warrant="The evidence is misread.",
            impact="No real impact.",
            argument_type="defense",
            confidence=None,
        )
        assert item.issues == []


# ── DrillRow with time_limit_seconds ──────────────────────────────────────────

class TestDrillRow:
    _BASE = dict(
        id="d1",
        speech_id="s1",
        user_id="u1",
        title="Warrant Chain Drill",
        description="Practice building warrant chains.",
        skill_target="warranting",
        prompt="Take your weakest argument and add a 'because' sentence.",
        order=1,
        created_at=datetime(2026, 6, 1),
        instructions="1. Pick your weakest argument.\n2. Add a warrant.",
        success_criteria=["Warrant is explicit", "Links claim to evidence"],
        source_weakness="Missing warrant on C1",
        difficulty="beginner",
        status="assigned",
    )

    def test_with_time_limit(self):
        row = DrillRow(**self._BASE, time_limit_seconds=60)
        assert row.time_limit_seconds == 60

    def test_without_time_limit_defaults_none(self):
        row = DrillRow(**self._BASE)
        assert row.time_limit_seconds is None

    def test_time_limit_none_explicit(self):
        row = DrillRow(**self._BASE, time_limit_seconds=None)
        assert row.time_limit_seconds is None

    def test_various_time_limits(self):
        for seconds in [30, 60, 90, 120, 180, 300]:
            row = DrillRow(**self._BASE, time_limit_seconds=seconds)
            assert row.time_limit_seconds == seconds


# ── DebateIssue schema ─────────────────────────────────────────────────────────

class TestDebateIssue:
    _VALID = dict(
        issue_type="missing_warrant",
        severity="high",
        title="Missing warrant on Contention 1",
        explanation="The claim is stated but no logical link to the evidence is provided.",
        why_it_matters="Flow judges may not evaluate this argument without a clear warrant.",
        recommendation="Add a 'because' sentence explaining WHY the claim follows from the evidence.",
        affected_argument_labels=["C1: Economic Growth"],
        recommended_drill_type="warranting",
    )

    def test_valid_issue(self):
        issue = DebateIssue(**self._VALID)
        assert issue.severity == "high"
        assert issue.issue_type == "missing_warrant"
        assert issue.affected_argument_labels == ["C1: Economic Growth"]

    def test_empty_affected_labels_allowed(self):
        data = {**self._VALID, "affected_argument_labels": []}
        issue = DebateIssue(**data)
        assert issue.affected_argument_labels == []

    def test_required_fields_enforced(self):
        with pytest.raises(ValidationError):
            DebateIssue(
                issue_type="missing_warrant",
                severity="high",
                # missing title, explanation, etc.
            )

    def test_multiple_severities(self):
        for sev in ["low", "medium", "high"]:
            issue = DebateIssue(**{**self._VALID, "severity": sev})
            assert issue.severity == sev


# ── _FeedbackOutput includes structured_issues ───────────────────────────────

class TestFeedbackOutputStructuredIssues:
    _SCORES = FeedbackScores(clash=12, weighing=10, extensions=14, drops=15, judge_adaptation=11)
    _EXPL = ScoreExplanation(
        dimension_name="warranting",
        score=10,
        score_band="Developing 8-11",
        evidence_from_speech="Warrants were thin on C1.",
        why_not_higher="No logical link stated.",
        how_to_improve="Add a 'because' sentence.",
    )

    def test_structured_issues_defaults_empty(self):
        output = _FeedbackOutput(
            overall_score=62,
            scores=self._SCORES,
            score_explanations=[self._EXPL],
            summary="Solid speech.",
            strengths=["Good signposting"],
            weaknesses=["Weak warranting"],
            decision_logic="Pro is winning on magnitude.",
            dropped_or_undercovered_arguments=[],
            warranting_diagnostics=["C1 warrant is thin."],
            weighing_diagnostics=[],
            evidence_diagnostics=[],
            judge_adaptation_notes="Good for lay judge.",
            top_3_priorities=["Improve warranting", "Add weighing", "Extend C1"],
            recommendations=["Practice warrant chains"],
        )
        assert output.structured_issues == []

    def test_structured_issues_populated(self):
        issue = DebateIssue(
            issue_type="no_weighing",
            severity="medium",
            title="No impact weighing",
            explanation="Impacts stated but not compared.",
            why_it_matters="Judge cannot evaluate which side wins on magnitude.",
            recommendation="Add explicit magnitude/probability/timeframe comparison.",
            affected_argument_labels=["Weighing: Magnitude"],
            recommended_drill_type="weighing",
        )
        output = _FeedbackOutput(
            overall_score=62,
            scores=self._SCORES,
            score_explanations=[self._EXPL],
            summary="Solid speech.",
            strengths=["Good signposting"],
            weaknesses=["Weak warranting"],
            decision_logic="Pro is winning on magnitude.",
            dropped_or_undercovered_arguments=[],
            warranting_diagnostics=[],
            weighing_diagnostics=[],
            evidence_diagnostics=[],
            judge_adaptation_notes="Good for lay judge.",
            top_3_priorities=["Weighing", "Warrants", "Extensions"],
            recommendations=["Practice weighing"],
            structured_issues=[issue],
        )
        assert len(output.structured_issues) == 1
        assert output.structured_issues[0].issue_type == "no_weighing"
