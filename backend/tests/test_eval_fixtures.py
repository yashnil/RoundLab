"""Tests for eval fixture loading, validation, and the mock pipeline runner.

All tests are pure — no LLM calls, no network.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from evals.models import (
    EvalSpeechFixture,
    VALID_ISSUE_TYPES,
    VALID_DRILL_TYPES,
    VALID_SPEECH_TYPES,
)
from evals.run_evals import load_fixtures, eval_fixture, run_mock_pipeline

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "evals" / "fixtures"


# ── Fixture loading ────────────────────────────────────────────────────────────

class TestLoadFixtures:
    def test_loads_at_least_one_fixture(self):
        fixtures = load_fixtures()
        assert len(fixtures) >= 1

    def test_loads_twelve_or_more_fixtures(self):
        """Baseline count — grows as new fixtures are added."""
        fixtures = load_fixtures()
        assert len(fixtures) >= 12

    def test_limit_respected(self):
        fixtures = load_fixtures(limit=2)
        assert len(fixtures) <= 2

    def test_fixture_id_filter(self):
        fixtures = load_fixtures(fixture_id="good_constructive")
        assert len(fixtures) == 1
        assert fixtures[0].id == "good_constructive"

    def test_unknown_fixture_id_returns_empty(self):
        fixtures = load_fixtures(fixture_id="does_not_exist")
        assert fixtures == []

    def test_new_fixtures_exist(self):
        """New fixtures added in this pass load without error."""
        for fid in (
            "extension_without_warrant",
            "strong_weighing_good_summary",
            "evidence_vague_attribution",
            "no_weighing_final_focus",
        ):
            fixtures = load_fixtures(fixture_id=fid)
            assert len(fixtures) == 1, f"Fixture '{fid}' not found or failed to load"
            assert fixtures[0].id == fid


# ── Fixture schema validation ──────────────────────────────────────────────────

class TestFixtureSchemas:
    @pytest.fixture(scope="class")
    def all_fixtures(self) -> list[EvalSpeechFixture]:
        return load_fixtures()

    def test_all_have_id(self, all_fixtures):
        for f in all_fixtures:
            assert f.id, f"Fixture missing id: {f.title}"

    def test_all_have_transcript(self, all_fixtures):
        for f in all_fixtures:
            assert len(f.transcript) > 50, f"Transcript too short in fixture: {f.id}"

    def test_all_speech_types_valid(self, all_fixtures):
        for f in all_fixtures:
            assert f.speech_type in VALID_SPEECH_TYPES, (
                f"Invalid speech_type '{f.speech_type}' in fixture '{f.id}'"
            )

    def test_all_issue_types_valid(self, all_fixtures):
        for f in all_fixtures:
            for issue in f.expected_issues:
                assert issue.issue_type in VALID_ISSUE_TYPES, (
                    f"Invalid issue_type '{issue.issue_type}' in fixture '{f.id}'"
                )

    def test_all_drill_types_valid(self, all_fixtures):
        for f in all_fixtures:
            for dt in f.expected_drill_types:
                assert dt in VALID_DRILL_TYPES, (
                    f"Invalid drill_type '{dt}' in fixture '{f.id}'"
                )

    def test_no_duplicate_ids(self, all_fixtures):
        ids = [f.id for f in all_fixtures]
        assert len(ids) == len(set(ids)), "Duplicate fixture IDs found"

    def test_expected_drill_type_on_required_issues(self, all_fixtures):
        """Every required issue should have an expected_drill_type."""
        for f in all_fixtures:
            for issue in f.expected_issues:
                if issue.required:
                    assert issue.expected_drill_type is not None, (
                        f"Required issue '{issue.issue_type}' in '{f.id}' missing expected_drill_type"
                    )

    def test_ids_match_filenames(self, all_fixtures):
        for f in all_fixtures:
            expected_path = FIXTURES_DIR / f"{f.id}.json"
            assert expected_path.exists(), (
                f"Fixture id '{f.id}' does not match its filename (expected {expected_path.name})"
            )


# ── Mock pipeline ──────────────────────────────────────────────────────────────

class TestMockPipeline:
    @pytest.fixture
    def good_fixture(self) -> EvalSpeechFixture:
        fixtures = load_fixtures(fixture_id="good_constructive")
        return fixtures[0]

    @pytest.fixture
    def missing_warrant_fixture(self) -> EvalSpeechFixture:
        fixtures = load_fixtures(fixture_id="missing_warrant_constructive")
        return fixtures[0]

    def test_mock_returns_expected_issues(self, good_fixture):
        output = run_mock_pipeline(good_fixture)
        issue_types = {i["issue_type"] for i in output["issues"]}
        expected_types = {e.issue_type for e in good_fixture.expected_issues}
        assert issue_types == expected_types

    def test_mock_returns_expected_drills(self, good_fixture):
        output = run_mock_pipeline(good_fixture)
        drill_targets = {d["skill_target"] for d in output["drills"]}
        expected_types = set(good_fixture.expected_drill_types)
        assert drill_targets == expected_types

    def test_mock_returns_expected_argument_count(self, good_fixture):
        output = run_mock_pipeline(good_fixture)
        assert len(output["arguments"]) == len(good_fixture.expected_argument_components)

    def test_missing_warrant_fixture_in_mock_produces_high_issue(self, missing_warrant_fixture):
        output = run_mock_pipeline(missing_warrant_fixture)
        high_issues = [i for i in output["issues"] if i["severity"] == "high"]
        assert len(high_issues) >= 2  # missing_warrant and weak_evidence both high


# ── Full mock eval run ─────────────────────────────────────────────────────────

class TestMockEvalRun:
    def test_mock_eval_passes_for_good_constructive(self):
        """Positive control: zero expected issues → zero mock issues → F1=1.0, passes."""
        fixtures = load_fixtures(fixture_id="good_constructive")
        result = eval_fixture(fixtures[0], mock=True)
        assert result.fixture_id == "good_constructive"
        assert result.passed is True
        assert result.issue_metrics.false_positives == 0
        assert result.required_issues_missed == []

    def test_mock_eval_passes_for_missing_warrant(self):
        """Mock mode: expected issues are returned, so required issues are met."""
        fixtures = load_fixtures(fixture_id="missing_warrant_constructive")
        result = eval_fixture(fixtures[0], mock=True)
        assert result.passed is True
        assert result.required_issues_missed == []

    def test_mock_eval_precision_is_one_in_mock_mode(self):
        """In mock mode, the LLM returns exactly the expected issues → no FPs."""
        fixtures = load_fixtures(fixture_id="no_weighing_summary")
        result = eval_fixture(fixtures[0], mock=True)
        assert result.issue_metrics.precision == 1.0
        assert result.issue_metrics.false_positives == 0

    def test_all_fixtures_pass_in_mock_mode(self):
        """Every fixture should produce a passing result in mock mode."""
        fixtures = load_fixtures()
        for fixture in fixtures:
            result = eval_fixture(fixture, mock=True)
            assert result.passed is True, (
                f"Fixture '{fixture.id}' failed in mock mode: "
                f"missed={result.required_issues_missed} error={result.error}"
            )

    def test_positive_control_fixture_no_required_issues(self):
        """strong_weighing_good_summary has no required issues — mock passes trivially."""
        fixtures = load_fixtures(fixture_id="strong_weighing_good_summary")
        result = eval_fixture(fixtures[0], mock=True)
        assert result.required_issues_missed == []
        assert result.passed is True

    def test_extension_without_warrant_requires_weak_extension(self):
        """extension_without_warrant must require weak_extension; no_weighing is optional."""
        fixtures = load_fixtures(fixture_id="extension_without_warrant")
        fixture = fixtures[0]
        required_types = {i.issue_type for i in fixture.expected_issues if i.required}
        assert "weak_extension" in required_types
        # no_weighing is a secondary signal — required=False so the fixture is robust
        # to LLMs that detect extension failure but don't separately flag weighing absence
        optional_types = {i.issue_type for i in fixture.expected_issues if not i.required}
        assert "no_weighing" in optional_types

    def test_no_clash_rebuttal_dropped_argument_not_required(self):
        """dropped_argument is not required in no_clash_rebuttal (transcript provides no round context)."""
        fixtures = load_fixtures(fixture_id="no_clash_rebuttal")
        fixture = fixtures[0]
        issue_types = {i.issue_type: i.required for i in fixture.expected_issues}
        assert issue_types.get("no_clash") is True, "no_clash must be required"
        assert issue_types.get("dropped_argument") is False, "dropped_argument must NOT be required"

    def test_no_clash_rebuttal_passes_mock_when_only_no_clash_detected(self):
        """Mock eval for no_clash_rebuttal passes even with FN on dropped_argument (non-required)."""
        fixtures = load_fixtures(fixture_id="no_clash_rebuttal")
        result = eval_fixture(fixtures[0], mock=True)
        # Mock returns all expected issues (both no_clash and dropped_argument)
        assert result.passed is True
        assert result.required_issues_missed == []

    def test_good_constructive_is_positive_control(self):
        """good_constructive is a positive control: zero expected issues AND zero expected drills."""
        fixtures = load_fixtures(fixture_id="good_constructive")
        fixture = fixtures[0]
        assert fixture.expected_issues == [], "good_constructive should have zero expected issues"
        assert fixture.expected_drill_types == [], "good_constructive should have zero expected drill types"

    def test_result_stores_predicted_issue_types(self):
        """EvalSampleResult stores predicted_issue_types after a mock run."""
        fixtures = load_fixtures(fixture_id="no_weighing_summary")
        result = eval_fixture(fixtures[0], mock=True)
        assert isinstance(result.predicted_issue_types, list)
        assert "no_weighing" in result.predicted_issue_types

    def test_result_has_correct_fields(self):
        fixtures = load_fixtures(fixture_id="good_constructive")
        result = eval_fixture(fixtures[0], mock=True)
        assert result.argument_coverage >= 0.0
        assert result.drill_relevance >= 0.0
        assert result.hallucinated_evidence_count == 0
        assert result.error is None
        assert result.timestamp

    def test_mock_latest_json_shape(self, tmp_path, monkeypatch):
        """Results JSON includes all expected top-level keys."""
        from evals.run_evals import aggregate
        fixtures = load_fixtures(limit=2)
        samples  = [eval_fixture(f, mock=True) for f in fixtures]
        agg      = aggregate(samples, mock=True, run_id="test_run")
        data     = agg.model_dump()

        for key in ("run_id", "timestamp", "mock_mode", "total_fixtures",
                    "passed", "failed", "avg_issue_f1", "samples"):
            assert key in data, f"Missing key '{key}' in result dict"

        assert isinstance(data["samples"], list)
        assert len(data["samples"]) == 2
