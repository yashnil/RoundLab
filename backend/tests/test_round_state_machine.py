"""Pass 16 — Round state machine tests.

Covers:
- Every valid PF phase transition
- Invalid phase transitions rejected
- Speaking order variants (first/second)
- Format variants (full, shortened, speech_stage_drill, evidence_testing)
- Difficulty parameters
- Time limits
- Late argument legality
"""
from __future__ import annotations
import pytest

from app.models.round_simulation import (
    OpponentDifficulty,
    RoundFormat,
    RoundPhaseType as RPT,
    RoundSide,
    RoundSimulationConfig,
    SpeakingOrder,
)
from app.services.round_state_machine import (
    CROSSFIRE_PHASES,
    LATE_PHASES_NO_NEW_ARGS,
    get_difficulty_params,
    get_phase_order,
    get_time_limit,
    is_new_argument_legal,
    next_phase,
    phase_speaker,
    student_speaks_in_phase,
    validate_phase_transition,
)


def _cfg(
    side=RoundSide.PRO,
    order=SpeakingOrder.FIRST,
    fmt=RoundFormat.FULL,
    **kw,
) -> RoundSimulationConfig:
    return RoundSimulationConfig(
        format=fmt,
        student_side=side,
        speaking_order=order,
        resolution="The USFG should substantially reduce its military.",
        **kw,
    )


# ── Phase order ────────────────────────────────────────────────────────────────

def test_full_phase_order_has_13_phases():
    order = get_phase_order(RoundFormat.FULL)
    assert len(order) == 13
    assert order[0] == RPT.FIRST_CONSTRUCTIVE
    assert order[-1] == RPT.COMPLETED


def test_shortened_order_skips_grand_and_final_crossfire():
    order = get_phase_order(RoundFormat.SHORTENED)
    assert RPT.GRAND_CROSSFIRE not in order
    assert RPT.FINAL_CROSSFIRE not in order
    assert RPT.FIRST_CONSTRUCTIVE in order
    assert RPT.COMPLETED in order


def test_speech_stage_drill_order_minimal():
    order = get_phase_order(RoundFormat.SPEECH_STAGE_DRILL)
    assert RPT.FIRST_CONSTRUCTIVE in order
    assert RPT.COMPLETED in order
    assert len(order) == 3


def test_evidence_testing_order():
    order = get_phase_order(RoundFormat.EVIDENCE_TESTING)
    assert RPT.FIRST_CROSSFIRE in order
    assert RPT.FIRST_SUMMARY in order
    assert RPT.SECOND_SUMMARY in order
    assert RPT.FIRST_REBUTTAL not in order


# ── next_phase ─────────────────────────────────────────────────────────────────

def test_next_phase_from_first_constructive():
    nxt = next_phase(RPT.FIRST_CONSTRUCTIVE, RoundFormat.FULL)
    assert nxt == RPT.SECOND_CONSTRUCTIVE


def test_next_phase_from_completed_is_none():
    assert next_phase(RPT.COMPLETED, RoundFormat.FULL) is None


def test_next_phase_from_judge_deliberation():
    nxt = next_phase(RPT.JUDGE_DELIBERATION, RoundFormat.FULL)
    assert nxt == RPT.COMPLETED


# ── validate_phase_transition ──────────────────────────────────────────────────

def test_valid_sequential_transitions():
    order = get_phase_order(RoundFormat.FULL)
    for i in range(len(order) - 1):
        ok, err = validate_phase_transition(order[i], order[i + 1], RoundFormat.FULL)
        assert ok, f"Transition {order[i]} → {order[i + 1]} rejected: {err}"


def test_skip_phase_rejected_without_override():
    ok, err = validate_phase_transition(
        RPT.FIRST_CONSTRUCTIVE,
        RPT.FIRST_REBUTTAL,
        RoundFormat.FULL,
        practice_override=False,
    )
    assert not ok
    assert "Expected next phase" in (err or "")


def test_skip_phase_allowed_with_practice_override():
    ok, err = validate_phase_transition(
        RPT.FIRST_CONSTRUCTIVE,
        RPT.FIRST_REBUTTAL,
        RoundFormat.FULL,
        practice_override=True,
    )
    assert ok


def test_backward_transition_always_rejected():
    ok, err = validate_phase_transition(
        RPT.FIRST_REBUTTAL,
        RPT.FIRST_CONSTRUCTIVE,
        RoundFormat.FULL,
    )
    assert not ok


def test_transition_from_completed_rejected():
    ok, err = validate_phase_transition(
        RPT.COMPLETED,
        RPT.FIRST_CONSTRUCTIVE,
        RoundFormat.FULL,
    )
    assert not ok
    assert "completed" in (err or "").lower()


def test_phase_not_in_format_rejected():
    ok, err = validate_phase_transition(
        RPT.FIRST_CONSTRUCTIVE,
        RPT.GRAND_CROSSFIRE,
        RoundFormat.SHORTENED,
        practice_override=True,
    )
    assert not ok
    assert "not part of" in (err or "")


# ── Phase speaker assignment ───────────────────────────────────────────────────

def test_first_speaking_order_pro_speaks_first():
    cfg = _cfg(side=RoundSide.PRO, order=SpeakingOrder.FIRST)
    assert phase_speaker(RPT.FIRST_CONSTRUCTIVE, cfg) == RoundSide.PRO
    assert phase_speaker(RPT.SECOND_CONSTRUCTIVE, cfg) == RoundSide.CON


def test_second_speaking_order_con_speaks_first():
    cfg = _cfg(side=RoundSide.PRO, order=SpeakingOrder.SECOND)
    # Student is PRO but speaking SECOND means CON speaks first
    assert phase_speaker(RPT.FIRST_CONSTRUCTIVE, cfg) == RoundSide.CON
    assert phase_speaker(RPT.SECOND_CONSTRUCTIVE, cfg) == RoundSide.PRO


def test_crossfire_speaker_is_none():
    cfg = _cfg()
    for cx_phase in CROSSFIRE_PHASES:
        assert phase_speaker(cx_phase, cfg) is None


def test_completed_phase_speaker_is_none():
    cfg = _cfg()
    assert phase_speaker(RPT.COMPLETED, cfg) is None


# ── student_speaks_in_phase ────────────────────────────────────────────────────

def test_student_speaks_when_speaking_first():
    cfg = _cfg(side=RoundSide.PRO, order=SpeakingOrder.FIRST)
    assert student_speaks_in_phase(RPT.FIRST_CONSTRUCTIVE, cfg) is True
    assert student_speaks_in_phase(RPT.SECOND_CONSTRUCTIVE, cfg) is False


def test_student_speaks_in_crossfire_always():
    cfg = _cfg()
    for cx_phase in CROSSFIRE_PHASES:
        assert student_speaks_in_phase(cx_phase, cfg) is True


# ── Time limits ────────────────────────────────────────────────────────────────

def test_constructive_time_limit():
    cfg = _cfg()
    assert get_time_limit(RPT.FIRST_CONSTRUCTIVE, cfg) == 240
    assert get_time_limit(RPT.SECOND_CONSTRUCTIVE, cfg) == 240


def test_summary_time_limit():
    cfg = _cfg()
    assert get_time_limit(RPT.FIRST_SUMMARY, cfg) == 180
    assert get_time_limit(RPT.SECOND_SUMMARY, cfg) == 180


def test_final_focus_time_limit():
    cfg = _cfg()
    assert get_time_limit(RPT.FIRST_FINAL_FOCUS, cfg) == 120


def test_crossfire_time_limit():
    cfg = _cfg()
    assert get_time_limit(RPT.FIRST_CROSSFIRE, cfg) == 180


def test_custom_time_limit():
    cfg = _cfg(constructive_time=300, final_focus_time=90)
    assert get_time_limit(RPT.FIRST_CONSTRUCTIVE, cfg) == 300
    assert get_time_limit(RPT.FIRST_FINAL_FOCUS, cfg) == 90


# ── Late argument legality ────────────────────────────────────────────────────

def test_new_argument_legal_in_constructive():
    legal, reason = is_new_argument_legal(RPT.FIRST_CONSTRUCTIVE)
    assert legal
    assert reason is None


def test_new_argument_illegal_in_summary():
    legal, reason = is_new_argument_legal(RPT.FIRST_SUMMARY)
    assert not legal
    assert "First Summary" in (reason or "")


def test_new_argument_illegal_in_final_focus():
    legal, reason = is_new_argument_legal(RPT.SECOND_FINAL_FOCUS)
    assert not legal


def test_new_argument_illegal_in_crossfire():
    legal, reason = is_new_argument_legal(RPT.FIRST_CROSSFIRE)
    assert not legal
    assert "crossfire" in (reason or "").lower()


def test_practice_override_allows_late_argument():
    legal, reason = is_new_argument_legal(RPT.FIRST_SUMMARY, is_practice_override=True)
    assert legal
    assert "practice_override" in (reason or "").lower()


# ── LATE_PHASES_NO_NEW_ARGS set ────────────────────────────────────────────────

def test_late_phases_set_contains_expected():
    assert RPT.FIRST_SUMMARY in LATE_PHASES_NO_NEW_ARGS
    assert RPT.SECOND_SUMMARY in LATE_PHASES_NO_NEW_ARGS
    assert RPT.FIRST_FINAL_FOCUS in LATE_PHASES_NO_NEW_ARGS
    assert RPT.SECOND_FINAL_FOCUS in LATE_PHASES_NO_NEW_ARGS
    assert RPT.FIRST_CONSTRUCTIVE not in LATE_PHASES_NO_NEW_ARGS


# ── Difficulty params ──────────────────────────────────────────────────────────

def test_novice_difficulty_params():
    p = get_difficulty_params(OpponentDifficulty.NOVICE)
    assert p["max_arguments"] == 2
    assert p["evidence_indictments"] is False
    assert p["coaching_hints_available"] is True


def test_jv_difficulty_params():
    p = get_difficulty_params(OpponentDifficulty.JV)
    assert p["max_arguments"] == 3
    assert p["weighing_enabled"] is True
    assert p["evidence_indictments"] is False


def test_varsity_difficulty_params():
    p = get_difficulty_params(OpponentDifficulty.VARSITY)
    assert p["max_arguments"] == 4
    assert p["evidence_indictments"] is True
    assert p["strategic_collapse"] is True
