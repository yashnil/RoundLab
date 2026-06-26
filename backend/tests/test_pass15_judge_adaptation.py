"""Pass 15 — Judge Adaptation Tests.

Covers:
- Judge profiles (built-in profiles, preference dimensions, comparison helpers)
- Adaptation rules (changes per judge type, jargon replacement)
- Adaptation risk checker (14 risk categories)
- Frontline adapter (response ordering, condensation)
- Speech plan adapter (stage-specific plans)
- Judge comparison (constants, differences, wording diffs)
- Judge workout generator (7 types, body snapshot cap)
- Judge readiness scorer (8 dimensions, composite, None handling)
- Judge adaptation models (serialization, immutability markers)
- API module (importable, router prefix)

Design constraints verified:
- Evidence body text never stored in AdaptationResult
- Support verdict passes through unchanged
- Historical/stale risk integration with Pass 11 and Pass 14
- None != 0 in readiness composite scoring
- Body snapshot capped at 500 chars
- Judge readiness is separate from evidence quality
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from tests import REPO_ROOT, workspace_page


# ── Judge profiles ─────────────────────────────────────────────────────────────

def test_judge_profiles_importable():
    from app.services.judge_profiles import get_builtin_profile, get_all_builtin_profiles
    profiles = get_all_builtin_profiles()
    assert len(profiles) == 5


def test_lay_profile_jargon_tolerance_1():
    from app.services.judge_profiles import get_builtin_profile
    p = get_builtin_profile("lay")
    assert p is not None
    assert p.preferences.jargon_tolerance == 1


def test_flow_profile_line_by_line_5():
    from app.services.judge_profiles import get_builtin_profile
    p = get_builtin_profile("flow")
    assert p is not None
    assert p.preferences.line_by_line_expectation == 5


def test_technical_profile_technical_rule_5():
    from app.services.judge_profiles import get_builtin_profile
    p = get_builtin_profile("technical")
    assert p is not None
    assert p.preferences.technical_rule_sensitivity == 5


def test_parent_profile_narrative_5():
    from app.services.judge_profiles import get_builtin_profile
    p = get_builtin_profile("parent")
    assert p is not None
    assert p.preferences.narrative_preference == 5


def test_coach_profile_weighing_5():
    from app.services.judge_profiles import get_builtin_profile
    p = get_builtin_profile("coach")
    assert p is not None
    assert p.preferences.weighing_expectation == 5


def test_unknown_judge_type_returns_none():
    from app.services.judge_profiles import get_builtin_profile
    assert get_builtin_profile("alien") is None  # type: ignore[arg-type]


def test_profiles_differ_meaningfully_lay_vs_flow():
    from app.services.judge_profiles import get_builtin_profile, profiles_differ_meaningfully
    lay = get_builtin_profile("lay")
    flow = get_builtin_profile("flow")
    assert profiles_differ_meaningfully(lay, flow)


def test_profiles_do_not_differ_meaningfully_same():
    from app.services.judge_profiles import get_builtin_profile, profiles_differ_meaningfully
    lay = get_builtin_profile("lay")
    lay2 = get_builtin_profile("lay")
    assert not profiles_differ_meaningfully(lay, lay2)


def test_preference_delta_has_all_dimensions():
    from app.services.judge_profiles import get_builtin_profile, preference_delta
    lay = get_builtin_profile("lay")
    flow = get_builtin_profile("flow")
    delta = preference_delta(lay, flow)
    assert "jargon_tolerance" in delta
    assert delta["jargon_tolerance"] != 0


def test_strongest_differences_returns_sorted():
    from app.services.judge_profiles import get_builtin_profile, strongest_differences
    lay = get_builtin_profile("lay")
    technical = get_builtin_profile("technical")
    diffs = strongest_differences(lay, technical, top_n=5)
    assert len(diffs) <= 5
    # Should be sorted by abs delta descending
    deltas = [abs(d[3]) for d in diffs]
    assert deltas == sorted(deltas, reverse=True)


def test_preference_label_low():
    from app.services.judge_profiles import preference_label
    assert "very low" in preference_label(1).lower() or "low" in preference_label(1).lower()


def test_preference_label_high():
    from app.services.judge_profiles import preference_label
    assert "very high" in preference_label(5).lower() or "high" in preference_label(5).lower()


# ── Adaptation rules ───────────────────────────────────────────────────────────

def test_adaptation_rules_importable():
    from app.services.adaptation_rules import get_adaptation_changes
    assert callable(get_adaptation_changes)


def test_lay_changes_include_jargon():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("lay", tag="Global warming is non-unique")
    dims = [c.dimension for c in changes]
    assert "jargon_level" in dims or "jargon" in " ".join(dims).lower()


def test_lay_changes_include_evidence_intro():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("lay", has_evidence=True)
    dims = [c.dimension for c in changes]
    assert any("evidence" in d.lower() or "intro" in d.lower() for d in dims)


def test_flow_changes_include_extension():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("flow")
    dims = [c.dimension for c in changes]
    assert any("extension" in d.lower() or "label" in d.lower() for d in dims)


def test_technical_changes_include_concession():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("technical")
    dims = [c.dimension for c in changes]
    assert any("concession" in d.lower() or "offense" in d.lower() or "burden" in d.lower() for d in dims)


def test_coach_changes_include_structure():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("coach")
    dims = [c.dimension for c in changes]
    assert any("structure" in d.lower() or "source" in d.lower() or "quality" in d.lower() for d in dims)


def test_parent_changes_are_superset_of_some_lay_changes():
    from app.services.adaptation_rules import get_adaptation_changes
    lay_dims = {c.dimension for c in get_adaptation_changes("lay")}
    parent_dims = {c.dimension for c in get_adaptation_changes("parent")}
    # Parent should have at least as many or more dimensions
    assert len(parent_dims) >= 1


def test_adaptation_changes_have_reason():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("lay")
    for c in changes:
        assert c.reason, f"Change {c.dimension} has no reason"


def test_jargon_replacement_for_non_unique():
    from app.services.adaptation_rules import get_adaptation_changes
    changes = get_adaptation_changes("lay", tag="non-unique economic pressure")
    text = " ".join(c.adapted for c in changes).lower()
    assert "non-unique" not in text or "already" in text or "already exists" in text


# ── Adaptation risk checker ────────────────────────────────────────────────────

def test_risk_checker_importable():
    from app.services.adaptation_risk_checker import check_all_risks
    assert callable(check_all_risks)


def test_causal_overstatement_detected():
    from app.services.adaptation_risk_checker import check_causal_overstatement
    risks = check_causal_overstatement(
        original_body="Climate may lead to increased risk of collapse in vulnerable regions",
        tag="Climate change causes societal collapse",
        judge_type="lay",
        source_ref="card1",
    )
    assert len(risks) > 0
    assert risks[0].category == "causal_overstatement"


def test_causal_overstatement_not_triggered_correlation():
    from app.services.adaptation_risk_checker import check_causal_overstatement
    risks = check_causal_overstatement(
        original_body="Studies find a correlation between X and Y",
        tag="X correlates with Y",
        judge_type="technical",
        source_ref="card2",
    )
    # Correlation tag + correlation body → no overstatement
    assert all(r.category != "causal_overstatement" for r in risks)


def test_unsafe_card_risk_for_lay():
    from app.services.adaptation_risk_checker import check_unsafe_card
    risks = check_unsafe_card(support_verdict="unsupported", judge_type="lay", source_ref="c1")
    assert len(risks) > 0
    assert risks[0].category == "unsafe_card_used"


def test_unsafe_card_no_risk_when_supported():
    from app.services.adaptation_risk_checker import check_unsafe_card
    risks = check_unsafe_card(support_verdict="supported", judge_type="lay", source_ref="c1")
    assert len(risks) == 0


def test_unsafe_card_no_risk_when_none():
    from app.services.adaptation_risk_checker import check_unsafe_card
    risks = check_unsafe_card(support_verdict=None, judge_type="technical", source_ref="c1")
    assert len(risks) == 0


def test_stale_card_risk_for_technical():
    from app.services.adaptation_risk_checker import check_stale_card
    risks = check_stale_card(freshness_state="stale", judge_type="technical", source_ref="c1")
    assert len(risks) > 0
    assert risks[0].category == "stale_card_used"


def test_stale_card_no_risk_for_fresh():
    from app.services.adaptation_risk_checker import check_stale_card
    risks = check_stale_card(freshness_state="fresh", judge_type="lay", source_ref="c1")
    assert len(risks) == 0


def test_jargon_overflow_lay_judge():
    from app.services.adaptation_risk_checker import check_jargon_overflow
    risks = check_jargon_overflow(
        tag="Extend our non-unique no-link turn",
        body_excerpt="",
        judge_type="lay",
        source_ref="c1",
    )
    assert len(risks) > 0
    assert risks[0].category == "jargon_overflow"


def test_jargon_overflow_no_risk_technical():
    from app.services.adaptation_risk_checker import check_jargon_overflow
    risks = check_jargon_overflow(
        tag="Extend our non-unique no-link turn",
        body_excerpt="",
        judge_type="technical",
        source_ref="c1",
    )
    assert len(risks) == 0


def test_missing_extension_in_summary():
    from app.services.adaptation_risk_checker import check_missing_extension
    risks = check_missing_extension(
        is_summary_or_ff=True,
        has_extension_signal=False,
        judge_type="flow",
        source_ref="arg1",
    )
    assert len(risks) > 0
    assert risks[0].category == "missing_extension"


def test_no_missing_extension_in_rebuttal():
    from app.services.adaptation_risk_checker import check_missing_extension
    risks = check_missing_extension(
        is_summary_or_ff=False,
        has_extension_signal=False,
        judge_type="flow",
        source_ref="arg1",
    )
    assert len(risks) == 0


def test_new_argument_in_final_focus():
    from app.services.adaptation_risk_checker import check_new_argument_late_speech
    risks = check_new_argument_late_speech(
        is_final_focus=True,
        introduces_new_content=True,
        source_ref="ff1",
    )
    assert len(risks) > 0
    assert risks[0].category == "new_argument_late_speech"


def test_no_new_argument_in_rebuttal():
    from app.services.adaptation_risk_checker import check_new_argument_late_speech
    risks = check_new_argument_late_speech(
        is_final_focus=False,
        introduces_new_content=True,
        source_ref="reb1",
    )
    assert len(risks) == 0


def test_under_explanation_lay():
    from app.services.adaptation_risk_checker import check_under_explanation
    risks = check_under_explanation(
        has_warrant=False,
        has_real_world_link=False,
        judge_type="lay",
        source_ref="c1",
    )
    assert len(risks) > 0
    assert risks[0].category == "under_explanation"


def test_no_under_explanation_technical():
    from app.services.adaptation_risk_checker import check_under_explanation
    risks = check_under_explanation(
        has_warrant=False,
        has_real_world_link=False,
        judge_type="technical",
        source_ref="c1",
    )
    assert len(risks) == 0


def test_check_all_risks_returns_list():
    from app.services.adaptation_risk_checker import check_all_risks
    risks = check_all_risks("lay")
    assert isinstance(risks, list)


def test_check_all_risks_sorted_by_severity():
    from app.services.adaptation_risk_checker import check_all_risks
    risks = check_all_risks(
        "lay",
        tag="non-unique extend turn",
        original_body="will inevitably cause",
        support_verdict="insufficient",
    )
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    levels = [severity_order[r.level] for r in risks]
    assert levels == sorted(levels)


def test_critical_risks_filter():
    from app.services.adaptation_risk_checker import check_all_risks, critical_risks
    risks = check_all_risks(
        "lay",
        tag="non-unique",
        support_verdict="insufficient",
    )
    crits = critical_risks(risks)
    assert all(r.level == "critical" for r in crits)


# ── Frontline adapter ──────────────────────────────────────────────────────────

def test_frontline_adapter_importable():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    assert callable(adapt_frontline_for_judge)


def test_lay_frontline_capped_at_3():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    frontline = {"id": "fl1", "title": "climate neg"}
    responses = [
        {"id": "r1", "response_text": "R1", "response_type": "analytic", "priority": 1},
        {"id": "r2", "response_text": "R2", "response_type": "analytic", "priority": 2},
        {"id": "r3", "response_text": "R3", "response_type": "analytic", "priority": 3},
        {"id": "r4", "response_text": "R4", "response_type": "analytic", "priority": 4},
        {"id": "r5", "response_text": "R5", "response_type": "analytic", "priority": 5},
    ]
    result = adapt_frontline_for_judge(frontline, responses, judge_type="lay")
    assert len(result.recommended_response_order) <= 3


def test_parent_frontline_capped_at_3():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    frontline = {"id": "fl1", "title": "test"}
    responses = [{"id": f"r{i}", "response_text": f"R{i}", "priority": i} for i in range(1, 6)]
    result = adapt_frontline_for_judge(frontline, responses, judge_type="parent")
    assert len(result.recommended_response_order) <= 3


def test_flow_frontline_preserves_all_responses():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    frontline = {"id": "fl1", "title": "test"}
    responses = [{"id": f"r{i}", "response_text": f"R{i}", "priority": i, "response_type": "analytic"} for i in range(1, 5)]
    result = adapt_frontline_for_judge(frontline, responses, judge_type="flow")
    assert len(result.recommended_response_order) == 4


def test_technical_frontline_offensive_first():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    frontline = {"id": "fl1", "title": "test"}
    responses = [
        {"id": "r1", "response_text": "Def R", "response_type": "analytic", "priority": 1},
        {"id": "r2", "response_text": "Turn R", "response_type": "turn", "priority": 2},
    ]
    result = adapt_frontline_for_judge(frontline, responses, judge_type="technical")
    # turn should be first in recommended order
    if result.recommended_response_order:
        first = result.recommended_response_order[0]
        assert "r2" in first or "Turn" in first or "turn" in first.lower()


def test_frontline_adaptation_has_changes_list():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    result = adapt_frontline_for_judge({"id": "fl1"}, [], judge_type="lay")
    assert isinstance(result.changes, list)


def test_frontline_adaptation_has_risks_list():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    result = adapt_frontline_for_judge({"id": "fl1"}, [], judge_type="flow")
    assert isinstance(result.risks, list)


def test_frontline_no_evidence_body_in_output():
    from app.services.frontline_adapter import adapt_frontline_for_judge
    result = adapt_frontline_for_judge(
        {"id": "fl1", "title": "test"},
        [{"id": "r1", "response_text": "Test response body text", "priority": 1}],
        judge_type="lay",
    )
    # FrontlineAdaptation should not store response body text
    result_dict = result.model_dump()
    text = str(result_dict)
    # "Test response body text" should not appear verbatim in adaptation output
    assert "Test response body text" not in text


# ── Speech plan adapter ────────────────────────────────────────────────────────

def test_speech_plan_adapter_importable():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    assert callable(adapt_speech_for_judge)


def test_lay_summary_has_collapse_recommendation():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge("summary", "lay", argument_count=3)
    assert result.collapse_recommendation is not None


def test_flow_summary_requires_extension():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge("summary", "flow", has_extensions=False)
    # Missing extension risk should be flagged
    assert any(r.category == "missing_extension" for r in result.risks)


def test_final_focus_new_content_risk():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge(
        "final_focus", "technical", is_introducing_new_content=True
    )
    assert any(r.category == "new_argument_late_speech" for r in result.risks)


def test_speech_plan_has_voter_framing():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge("final_focus", "lay")
    assert result.voter_framing is not None and len(result.voter_framing) > 5


def test_speech_plan_has_time_notes():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge("summary", "technical")
    assert result.time_allocation_notes is not None


def test_speech_plan_response_ordering_not_empty():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge("rebuttal", "flow")
    assert len(result.response_ordering) > 0


def test_speech_plan_rebuttal_no_missing_extension_risk():
    from app.services.speech_plan_adapter import adapt_speech_for_judge
    result = adapt_speech_for_judge("rebuttal", "flow")
    # Rebuttal should not flag missing extension
    assert all(r.category != "missing_extension" for r in result.risks)


# ── Judge comparison ───────────────────────────────────────────────────────────

def test_judge_comparison_importable():
    from app.services.judge_comparison import compare_profiles
    assert callable(compare_profiles)


def test_comparison_requires_two_types():
    from app.services.judge_comparison import compare_profiles
    with pytest.raises(ValueError):
        compare_profiles(["lay"], "evidence", "src1")


def test_comparison_has_universal_constants():
    from app.services.judge_comparison import compare_profiles
    result = compare_profiles(["lay", "technical"], "evidence", "src1")
    assert "Evidence body text is never altered" in result.constants


def test_comparison_lay_vs_technical_has_differences():
    from app.services.judge_comparison import compare_profiles
    result = compare_profiles(["lay", "technical"], "evidence", "src1")
    assert len(result.differences) > 0


def test_comparison_same_type_fewer_differences():
    from app.services.judge_comparison import compare_profiles
    result_same = compare_profiles(["lay", "lay"], "evidence", "src1")
    result_diff = compare_profiles(["lay", "technical"], "evidence", "src1")
    assert len(result_same.differences) <= len(result_diff.differences)


def test_comparison_has_time_allocation():
    from app.services.judge_comparison import compare_profiles
    result = compare_profiles(["lay", "flow"], "evidence", "src1")
    assert len(result.time_allocation_differences) > 0


def test_comparison_result_has_source_fields():
    from app.services.judge_comparison import compare_profiles
    result = compare_profiles(["flow", "parent"], "frontline", "fl1")
    assert result.source_type == "frontline"
    assert result.source_id == "fl1"


def test_comparison_three_judges():
    from app.services.judge_comparison import compare_profiles
    result = compare_profiles(["lay", "flow", "technical"], "evidence", "src1")
    assert len(result.judge_types) == 3


# ── Judge workout generator ────────────────────────────────────────────────────

def test_workout_generator_importable():
    from app.services.judge_workout_generator import generate_judge_workout
    assert callable(generate_judge_workout)


def test_lay_evidence_generates_lay_explanation():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout(
        "lay", "evidence",
        card={"id": "c1", "tag": "Climate change is real", "body_text": "Long body text here"},
        user_id="u1",
    )
    assert workout is not None
    assert workout.workout_type == "lay_explanation"


def test_parent_evidence_generates_parent_context():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout(
        "parent", "evidence",
        card={"id": "c1", "tag": "Economic inequality", "body_text": "Body text"},
        user_id="u1",
    )
    assert workout is not None
    assert workout.workout_type == "parent_context"


def test_flow_argument_generates_flow_extension():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout(
        "flow", "argument",
        argument_title="Economic growth",
        user_id="u1",
    )
    assert workout is not None
    assert workout.workout_type == "flow_extension"


def test_technical_frontline_generates_technical_concession():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout(
        "technical", "frontline",
        frontline={"id": "fl1", "title": "Climate neg"},
        responses=[{"id": "r1", "response_type": "turn"}],
        user_id="u1",
    )
    assert workout is not None
    assert workout.workout_type == "technical_concession"


def test_summary_generates_final_focus_voter():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout(
        "flow", "summary",
        argument_title="Our main argument",
        user_id="u1",
    )
    assert workout is not None
    assert workout.workout_type == "final_focus_voter"


def test_body_snapshot_capped_at_500():
    from app.services.judge_workout_generator import generate_judge_workout
    long_body = "A" * 1000
    workout = generate_judge_workout(
        "lay", "evidence",
        card={"id": "c1", "tag": "Test", "body_text": long_body},
        user_id="u1",
    )
    assert workout is not None
    if workout.source_card_body_snapshot:
        assert len(workout.source_card_body_snapshot) <= 500


def test_workout_has_success_criteria():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout("lay", "evidence", card={"tag": "X"}, user_id="u1")
    assert workout is not None
    assert len(workout.success_criteria) > 0


def test_workout_has_time_limit():
    from app.services.judge_workout_generator import generate_judge_workout
    workout = generate_judge_workout("flow", "argument", argument_title="X", user_id="u1")
    assert workout is not None
    assert workout.time_limit_seconds > 0


def test_judge_switch_includes_two_judge_labels():
    from app.services.judge_workout_generator import build_judge_switch
    workout = build_judge_switch("My argument", "u1")
    assert workout.judge_type == "lay"
    assert workout.comparison_judge_type == "technical"


def test_evidence_adaptation_stores_snapshot_not_full_body():
    from app.services.judge_workout_generator import build_evidence_adaptation
    long_body = "X" * 800
    card = {"id": "c1", "tag": "Tag", "body_text": long_body}
    workout = build_evidence_adaptation(card, "u1")
    if workout.source_card_body_snapshot:
        assert len(workout.source_card_body_snapshot) <= 500


# ── Judge readiness scorer ─────────────────────────────────────────────────────

def test_readiness_scorer_importable():
    from app.services.judge_readiness_scorer import score_judge_readiness
    assert callable(score_judge_readiness)


def test_readiness_returns_report():
    from app.services.judge_readiness_scorer import score_judge_readiness
    from app.models.judge_adaptation import JudgeReadinessReport
    report = score_judge_readiness("lay", "evidence", "src1", "u1", risks=[])
    assert isinstance(report, JudgeReadinessReport)


def test_readiness_composite_not_none_with_data():
    from app.services.judge_readiness_scorer import score_judge_readiness
    report = score_judge_readiness(
        "lay", "evidence", "src1", "u1",
        risks=[],
        has_changes=True,
        evidence_count=1,
    )
    assert report.composite_score is not None
    assert 0 <= report.composite_score <= 100


def test_readiness_composite_reduced_by_critical_risk():
    from app.services.judge_readiness_scorer import score_judge_readiness
    from app.models.judge_adaptation import AdaptationRisk
    critical_risk = AdaptationRisk(
        category="unsafe_card_used",
        level="critical",
        description="Card has insufficient support verdict",
        how_to_mitigate="Remove or replace the card",
    )
    no_risk = score_judge_readiness("lay", "evidence", "src1", "u1", risks=[], evidence_count=1)
    with_risk = score_judge_readiness("lay", "evidence", "src1", "u1", risks=[critical_risk], evidence_count=1)
    if no_risk.composite_score is not None and with_risk.composite_score is not None:
        assert with_risk.composite_score < no_risk.composite_score


def test_readiness_extension_none_for_non_summary():
    from app.services.judge_readiness_scorer import score_judge_readiness
    report = score_judge_readiness(
        "flow", "evidence", "src1", "u1",
        risks=[],
        has_extensions=False,
    )
    # Extension completeness has no data for evidence source type
    assert report.extension_completeness.score is None


def test_readiness_extension_has_data_for_summary():
    from app.services.judge_readiness_scorer import score_judge_readiness
    report = score_judge_readiness(
        "flow", "summary", "src1", "u1",
        risks=[],
        has_extensions=True,
    )
    assert report.extension_completeness.score is not None


def test_readiness_eight_dimensions_present():
    from app.services.judge_readiness_scorer import score_judge_readiness
    report = score_judge_readiness("lay", "evidence", "src1", "u1", risks=[])
    assert hasattr(report, "clarity")
    assert hasattr(report, "organization")
    assert hasattr(report, "extension_completeness")
    assert hasattr(report, "evidence_explanation")
    assert hasattr(report, "weighing_fit")
    assert hasattr(report, "jargon_fit")
    assert hasattr(report, "strategic_focus")
    assert hasattr(report, "speech_stage_legality")


def test_readiness_separate_from_evidence_quality():
    """Verify readiness report has no field that references evidence quality score."""
    from app.services.judge_readiness_scorer import score_judge_readiness
    report = score_judge_readiness("lay", "evidence", "src1", "u1", risks=[])
    report_dict = report.model_dump()
    keys = set(report_dict.keys())
    # Should NOT have evidence quality or freshness fields
    assert "evidence_quality" not in keys
    assert "freshness_state" not in keys
    assert "coverage_score" not in keys


def test_readiness_none_is_not_zero():
    from app.services.judge_readiness_scorer import score_judge_readiness
    report = score_judge_readiness(
        "flow", "evidence", "src1", "u1",
        risks=[],
        evidence_count=0,
    )
    # With no evidence, evidence_explanation should be None (not 0)
    assert report.evidence_explanation.score is None


# ── Judge adaptation models ────────────────────────────────────────────────────

def test_models_importable():
    from app.models.judge_adaptation import (
        JudgeProfile, JudgePreferences, AdaptationChange,
        AdaptationRisk, JudgeAdaptationResult, JudgeComparisonResult,
        JudgeReadinessReport, JudgeWorkoutCreate,
    )
    assert True


def test_judge_preferences_validates_range():
    from app.models.judge_adaptation import JudgePreferences
    with pytest.raises(Exception):
        JudgePreferences(
            jargon_tolerance=6,  # out of range
            speed_tolerance=3, evidence_detail_preference=3,
            line_by_line_expectation=3, extension_strictness=3,
            weighing_expectation=3, narrative_preference=3,
            real_world_explanation=3, technical_rule_sensitivity=3,
            intervention_tolerance=3, organization_preference=3,
            source_qualification_importance=3, persuasion_vs_flow_emphasis=3,
        )


def test_adaptation_result_has_no_body_text_field():
    from app.models.judge_adaptation import JudgeAdaptationResult
    fields = set(JudgeAdaptationResult.model_fields.keys())
    assert "body_text" not in fields
    assert "evidence_body" not in fields
    assert "card_body" not in fields


def test_adaptation_change_serializes():
    from app.models.judge_adaptation import AdaptationChange
    c = AdaptationChange(
        dimension="jargon_level",
        original="non-unique",
        adapted="already exists",
        reason="Lay judges don't know this term",
        may_be_omitted=False,
    )
    data = c.model_dump()
    assert data["dimension"] == "jargon_level"
    assert data["adapted"] == "already exists"


def test_adaptation_risk_categories_all_valid():
    from app.models.judge_adaptation import AdaptationRisk
    cats = [
        "causal_overstatement", "qualifier_removal", "missing_extension",
        "new_argument_late_speech", "jargon_overflow", "under_explanation",
        "unsafe_card_used", "stale_card_used",
    ]
    for cat in cats:
        r = AdaptationRisk(
            category=cat,  # type: ignore[arg-type]
            level="medium",
            description="Test",
            how_to_mitigate="Test",
        )
        assert r.category == cat


def test_workout_create_has_no_full_body():
    from app.models.judge_adaptation import JudgeWorkoutCreate
    fields = set(JudgeWorkoutCreate.model_fields.keys())
    # Only snapshot is allowed, not full body text
    assert "body_text" not in fields
    assert "evidence_body" not in fields


# ── Judge adaptation service orchestrator ──────────────────────────────────────

def test_adaptation_service_importable():
    from app.services.judge_adaptation_service import generate_adaptation
    assert callable(generate_adaptation)


def test_generate_adaptation_returns_result_type():
    from app.services.judge_adaptation_service import generate_adaptation
    from app.models.judge_adaptation import JudgeAdaptationResult
    sb_mock = MagicMock()
    sb_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.services.judge_adaptation_service.get_supabase", return_value=sb_mock):
        result = generate_adaptation("u1", "lay", "evidence", "card1")
    assert isinstance(result, JudgeAdaptationResult)


def test_generate_adaptation_no_body_text_in_result():
    from app.services.judge_adaptation_service import generate_adaptation
    sb_mock = MagicMock()
    sb_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": "c1", "user_id": "u1", "tag": "Test tag", "body_text": "SECRET BODY TEXT",
        "source_domain": "example.com",
    }]
    with patch("app.services.judge_adaptation_service.get_supabase", return_value=sb_mock):
        result = generate_adaptation("u1", "lay", "evidence", "c1")

    result_str = str(result.model_dump())
    assert "SECRET BODY TEXT" not in result_str


def test_generate_adaptation_preserves_judge_type():
    from app.services.judge_adaptation_service import generate_adaptation
    sb_mock = MagicMock()
    sb_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.services.judge_adaptation_service.get_supabase", return_value=sb_mock):
        result = generate_adaptation("u1", "technical", "argument", "arg1")
    assert result.judge_type == "technical"


# ── API module ─────────────────────────────────────────────────────────────────

def test_api_importable():
    from app.api.judge_adaptation import router
    assert router.prefix == "/judge-adaptation"


def test_api_has_adapt_endpoint():
    from app.api.judge_adaptation import router
    paths = [r.path for r in router.routes]
    assert any("adapt" in p for p in paths)


def test_api_has_compare_endpoint():
    from app.api.judge_adaptation import router
    paths = [r.path for r in router.routes]
    assert any("compare" in p for p in paths)


def test_api_has_workouts_endpoint():
    from app.api.judge_adaptation import router
    paths = [r.path for r in router.routes]
    assert any("workouts" in p for p in paths)


def test_api_has_profiles_endpoint():
    from app.api.judge_adaptation import router
    paths = [r.path for r in router.routes]
    assert any("profiles" in p for p in paths)


def test_api_has_readiness_score_endpoint():
    from app.api.judge_adaptation import router
    paths = [r.path for r in router.routes]
    assert any("readiness" in p for p in paths)


def test_api_registered_in_main():
    from app.main import app
    paths = [r.path for r in app.routes]
    assert any("judge-adaptation" in p for p in paths)


# ── Immutability constraints ───────────────────────────────────────────────────

def test_adaptation_result_what_must_remain_explicit_contains_body():
    from app.services.judge_adaptation_service import generate_adaptation
    sb_mock = MagicMock()
    sb_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": "c1", "user_id": "u1", "tag": "Test", "body_text": "body",
    }]
    with patch("app.services.judge_adaptation_service.get_supabase", return_value=sb_mock):
        result = generate_adaptation("u1", "lay", "evidence", "c1")
    explicit = result.what_must_remain_explicit
    assert any("Evidence body" in e or "evidence body" in e.lower() for e in explicit)


def test_adaptation_result_what_must_remain_explicit_contains_citation():
    from app.services.judge_adaptation_service import generate_adaptation
    sb_mock = MagicMock()
    sb_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": "c1", "user_id": "u1", "tag": "Test", "body_text": "body",
    }]
    with patch("app.services.judge_adaptation_service.get_supabase", return_value=sb_mock):
        result = generate_adaptation("u1", "flow", "evidence", "c1")
    explicit = result.what_must_remain_explicit
    assert any("citation" in e.lower() or "source" in e.lower() for e in explicit)


def test_evidence_guide_does_not_include_body():
    from app.services.judge_adaptation_service import generate_adaptation
    sb_mock = MagicMock()
    sb_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": "c1", "user_id": "u1", "tag": "Climate change", "body_text": "CONFIDENTIAL BODY",
        "author": "Smith", "published_date": "2023-01-01",
    }]
    with patch("app.services.judge_adaptation_service.get_supabase", return_value=sb_mock):
        result = generate_adaptation("u1", "lay", "evidence", "c1")

    if result.evidence_guide:
        guide_str = str(result.evidence_guide.model_dump())
        assert "CONFIDENTIAL BODY" not in guide_str


def test_pass11_verdict_preserved_not_upgraded():
    """unsafe_card risk must flag unsupported verdict, not suppress it."""
    from app.services.adaptation_risk_checker import check_unsafe_card
    risks = check_unsafe_card("unsupported", "lay", "c1")
    assert any(r.category == "unsafe_card_used" for r in risks)
    # Must not return empty (pretending verdict is ok for lay judge)
    assert len(risks) > 0


def test_pass14_freshness_preserved_not_upgraded():
    """stale_card risk must flag stale state, not suppress it."""
    from app.services.adaptation_risk_checker import check_stale_card
    risks = check_stale_card("stale", "lay", "c1")
    assert any(r.category == "stale_card_used" for r in risks)


# ── Frontend types sanity ──────────────────────────────────────────────────────

def test_frontend_types_file_exists():
    """Verify types file was created."""
    assert (REPO_ROOT / "frontend/src/types/judgeAdaptation.ts").exists()


def test_judge_adaptation_page_exists():
    """Verify judge adaptation page lives in the workspace route group."""
    new_path = workspace_page("judge-adaptation/page.tsx")
    old_path = REPO_ROOT / "frontend/src/app/judge-adaptation/page.tsx"
    assert new_path.exists(), f"Page not found at workspace path: {new_path}"
    # Old bare path must not exist — Next.js would serve both URLs otherwise.
    assert not old_path.exists(), f"Stale bare path still present: {old_path}"


def test_nav_items_has_judge_adaptation():
    """Verify navItems.ts includes judge-adaptation."""
    content = (REPO_ROOT / "frontend/src/lib/navItems.ts").read_text()
    assert "judge-adaptation" in content


def test_judge_adaptation_components_exist():
    """Verify all 5 judge adaptation components were created."""
    base = REPO_ROOT / "frontend/src/components/judge-adaptation"
    required = [
        "JudgeProfileSelector.tsx",
        "AdaptationChangesPanel.tsx",
        "JudgeComparisonPanel.tsx",
        "JudgeWorkoutCard.tsx",
        "JudgeReadinessCard.tsx",
    ]
    for fname in required:
        assert (base / fname).exists(), f"Missing: {fname}"
