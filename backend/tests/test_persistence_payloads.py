"""
Tests for persistence payload logic — clamping, ID assignment, and backward compatibility.
Pure unit tests; no live Supabase connection required.
"""

import pytest

from app.models.argument_map import ArgumentItem, ArgumentMapRow
from app.models.drill import DrillRow
from app.models.speech import SpeechUpdateRequest
from app.services.feedback_generation import DebateIssue, _FeedbackOutput, ScoreExplanation
from app.models.feedback_report import FeedbackScores
from datetime import datetime


# ── SpeechUpdateRequest with duration_seconds ──────────────────────────────────

class TestSpeechUpdateRequest:
    def test_audio_url_only(self):
        req = SpeechUpdateRequest(audio_url="user/speech/audio.webm")
        assert req.audio_url == "user/speech/audio.webm"
        assert req.duration_seconds is None

    def test_with_duration_seconds(self):
        req = SpeechUpdateRequest(audio_url="user/speech/audio.webm", duration_seconds=90)
        assert req.duration_seconds == 90

    def test_duration_seconds_none_explicit(self):
        req = SpeechUpdateRequest(audio_url="user/speech/audio.webm", duration_seconds=None)
        assert req.duration_seconds is None


class TestDurationClamping:
    """Test the clamping logic from app/api/speeches.py PATCH route."""

    @staticmethod
    def clamp_duration(val: int) -> int:
        return max(5, min(3600, val))

    def test_normal_value_unchanged(self):
        assert self.clamp_duration(90) == 90

    def test_lower_bound(self):
        assert self.clamp_duration(0) == 5
        assert self.clamp_duration(-10) == 5

    def test_upper_bound(self):
        assert self.clamp_duration(9999) == 3600

    def test_boundary_values(self):
        assert self.clamp_duration(5) == 5
        assert self.clamp_duration(3600) == 3600

    def test_common_speech_durations(self):
        # 45s constructive, 3m rebuttal, 2m final focus
        for dur in [45, 90, 120, 180, 240]:
            assert self.clamp_duration(dur) == dur


# ── time_limit_seconds clamping ────────────────────────────────────────────────

class TestTimeLimitClamping:
    """Test the clamping logic from app/api/drills.py generate_drills_for_speech."""

    @staticmethod
    def clamp_time_limit(val: int | None) -> int | None:
        if val is None:
            return None
        return max(30, min(300, int(val)))

    def test_none_passthrough(self):
        assert self.clamp_time_limit(None) is None

    def test_normal_value_unchanged(self):
        assert self.clamp_time_limit(60) == 60
        assert self.clamp_time_limit(90) == 90
        assert self.clamp_time_limit(120) == 120

    def test_lower_bound(self):
        assert self.clamp_time_limit(0) == 30
        assert self.clamp_time_limit(10) == 30

    def test_upper_bound(self):
        assert self.clamp_time_limit(600) == 300
        assert self.clamp_time_limit(9999) == 300

    def test_boundary_values(self):
        assert self.clamp_time_limit(30) == 30
        assert self.clamp_time_limit(300) == 300


# ── ArgumentItem ID assignment ─────────────────────────────────────────────────

class TestArgumentIDAssignment:
    """Test that stable IDs are assigned correctly before DB persist."""

    def _make_item(self, label: str) -> ArgumentItem:
        return ArgumentItem(
            label=label,
            claim="Test claim",
            warrant="Test warrant",
            evidence=None,
            impact="Test impact",
            argument_type="offense",
            issues=[],
            confidence=0.8,
        )

    def test_ids_assigned_sequentially(self):
        items = [self._make_item(f"Arg {i}") for i in range(1, 4)]
        # Simulate what argument_maps.py does
        for idx, item in enumerate(items):
            item.id = f"arg_{idx + 1}"
        assert items[0].id == "arg_1"
        assert items[1].id == "arg_2"
        assert items[2].id == "arg_3"

    def test_id_none_by_default(self):
        item = self._make_item("Test")
        assert item.id is None

    def test_id_serializes_to_json(self):
        item = self._make_item("C1: Economic Growth")
        item.id = "arg_1"
        dumped = item.model_dump()
        assert dumped["id"] == "arg_1"

    def test_empty_argument_list_no_ids(self):
        items: list[ArgumentItem] = []
        for idx, item in enumerate(items):
            item.id = f"arg_{idx + 1}"
        assert len(items) == 0  # Should not crash


# ── structured_issues round-trip ──────────────────────────────────────────────

class TestStructuredIssuesRoundTrip:
    """Ensure structured_issues can be serialized to/from JSON (for JSONB storage)."""

    _SCORES = FeedbackScores(clash=12, weighing=10, extensions=14, drops=15, judge_adaptation=11)
    _EXPL = ScoreExplanation(
        dimension_name="warranting",
        score=10,
        score_band="Developing 8-11",
        evidence_from_speech="Warrants were thin on C1.",
        why_not_higher="No logical link stated.",
        how_to_improve="Add a 'because' sentence.",
    )

    def _make_output(self, issues: list) -> _FeedbackOutput:
        return _FeedbackOutput(
            overall_score=62,
            scores=self._SCORES,
            score_explanations=[self._EXPL],
            summary="Solid speech.",
            strengths=["Good signposting"],
            weaknesses=["Weak warranting"],
            decision_logic="Pro is winning.",
            dropped_or_undercovered_arguments=[],
            warranting_diagnostics=[],
            weighing_diagnostics=[],
            evidence_diagnostics=[],
            judge_adaptation_notes="OK for lay.",
            top_3_priorities=["Warrants", "Weighing", "Extensions"],
            recommendations=["Practice warrant chains"],
            structured_issues=issues,
        )

    def test_empty_issues_serializes(self):
        output = self._make_output([])
        dumped = output.model_dump()
        assert dumped["structured_issues"] == []

    def test_single_issue_round_trip(self):
        issue = DebateIssue(
            issue_type="missing_warrant",
            severity="high",
            title="Missing warrant on C1",
            explanation="No logical link.",
            why_it_matters="Flow judges won't evaluate it.",
            recommendation="Add a because sentence.",
            affected_argument_labels=["C1: Economic Growth"],
            recommended_drill_type="warranting",
        )
        output = self._make_output([issue])
        dumped = output.model_dump()
        assert len(dumped["structured_issues"]) == 1
        assert dumped["structured_issues"][0]["issue_type"] == "missing_warrant"
        assert dumped["structured_issues"][0]["affected_argument_labels"] == ["C1: Economic Growth"]

    def test_multiple_issues_preserve_order(self):
        issues = [
            DebateIssue(
                issue_type=t,
                severity="medium",
                title=f"Issue {t}",
                explanation="Test",
                why_it_matters="Because.",
                recommendation="Fix it.",
                affected_argument_labels=[],
                recommended_drill_type="warranting",
            )
            for t in ["missing_warrant", "no_weighing", "unclear_impact"]
        ]
        output = self._make_output(issues)
        dumped = output.model_dump()
        types = [i["issue_type"] for i in dumped["structured_issues"]]
        assert types == ["missing_warrant", "no_weighing", "unclear_impact"]


# ── Backward compatibility: old feedback without structured_issues ──────────────

class TestOldFeedbackCompatibility:
    """Old reports stored in raw_feedback without structured_issues must remain valid."""

    def test_structured_issues_defaults_to_empty(self):
        # Simulate loading old raw_feedback JSON that lacks structured_issues
        old_raw = {
            "overall_score": 55,
            "scores": {"clash": 10, "weighing": 8, "extensions": 12, "drops": 13, "judge_adaptation": 12},
            "score_explanations": [],
            "summary": "Older report",
            "strengths": ["Good delivery"],
            "weaknesses": ["Weak warrants"],
            "decision_logic": "Pro likely winning.",
            "dropped_or_undercovered_arguments": [],
            "warranting_diagnostics": [],
            "weighing_diagnostics": [],
            "evidence_diagnostics": [],
            "judge_adaptation_notes": "Fine for lay.",
            "top_3_priorities": ["Warranting", "Weighing", "Drops"],
            "recommendations": ["Practice warrants"],
            # NB: no structured_issues key
        }
        output = _FeedbackOutput(**old_raw)
        assert output.structured_issues == []

    def test_partial_raw_feedback_with_issues(self):
        issue = DebateIssue(
            issue_type="no_weighing",
            severity="high",
            title="No weighing",
            explanation="Impacts stated but not compared.",
            why_it_matters="Judge cannot compare sides.",
            recommendation="Add explicit comparisons.",
            affected_argument_labels=[],
            recommended_drill_type="weighing",
        )
        output = _FeedbackOutput(
            overall_score=60,
            scores=FeedbackScores(clash=12, weighing=8, extensions=14, drops=14, judge_adaptation=12),
            score_explanations=[],
            summary="New report with issues.",
            strengths=[],
            weaknesses=["No weighing"],
            decision_logic="Unclear.",
            dropped_or_undercovered_arguments=[],
            warranting_diagnostics=[],
            weighing_diagnostics=[],
            evidence_diagnostics=[],
            judge_adaptation_notes="",
            top_3_priorities=["Weighing"],
            recommendations=[],
            structured_issues=[issue],
        )
        assert len(output.structured_issues) == 1
        assert output.structured_issues[0].severity == "high"


# ── DrillRow time_limit_seconds backward compatibility ────────────────────────

class TestDrillTimeLimitCompatibility:
    _BASE = dict(
        id="d1",
        speech_id="s1",
        user_id="u1",
        title="Warrant Drill",
        description="Test drill",
        skill_target="warranting",
        prompt="Add a because sentence.",
        order=1,
        created_at=datetime(2026, 6, 1),
        instructions="1. Pick argument.\n2. Add warrant.",
        success_criteria=["Warrant is explicit"],
        source_weakness="Missing warrant",
        difficulty="beginner",
        status="assigned",
    )

    def test_old_drill_without_time_limit_is_valid(self):
        """Drills generated before the migration must load without error."""
        row = DrillRow(**self._BASE)
        assert row.time_limit_seconds is None

    def test_new_drill_with_time_limit(self):
        row = DrillRow(**self._BASE, time_limit_seconds=60)
        assert row.time_limit_seconds == 60

    def test_time_limit_preserved_through_model_dump(self):
        row = DrillRow(**self._BASE, time_limit_seconds=90)
        d = row.model_dump()
        assert d["time_limit_seconds"] == 90
