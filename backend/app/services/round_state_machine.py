"""Pass 16 — PF Round State Machine.

Deterministic phase ordering and transition validation.
Never allows skipping phases, wrong speech types, or illegal arguments.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.models.round_simulation import (
    OpponentDifficulty,
    RoundFormat,
    RoundPhaseType,
    RoundSide,
    RoundSimulationConfig,
    SpeakerRole,
    SpeakingOrder,
)


# Ordered phase sequence for a full PF round
_FULL_PHASE_ORDER: List[RoundPhaseType] = [
    RoundPhaseType.FIRST_CONSTRUCTIVE,
    RoundPhaseType.SECOND_CONSTRUCTIVE,
    RoundPhaseType.FIRST_CROSSFIRE,
    RoundPhaseType.FIRST_REBUTTAL,
    RoundPhaseType.SECOND_REBUTTAL,
    RoundPhaseType.GRAND_CROSSFIRE,
    RoundPhaseType.FIRST_SUMMARY,
    RoundPhaseType.SECOND_SUMMARY,
    RoundPhaseType.FINAL_CROSSFIRE,
    RoundPhaseType.FIRST_FINAL_FOCUS,
    RoundPhaseType.SECOND_FINAL_FOCUS,
    RoundPhaseType.JUDGE_DELIBERATION,
    RoundPhaseType.COMPLETED,
]

# Shortened format skips grand crossfire and final crossfire
_SHORTENED_PHASE_ORDER: List[RoundPhaseType] = [
    RoundPhaseType.FIRST_CONSTRUCTIVE,
    RoundPhaseType.SECOND_CONSTRUCTIVE,
    RoundPhaseType.FIRST_CROSSFIRE,
    RoundPhaseType.FIRST_REBUTTAL,
    RoundPhaseType.SECOND_REBUTTAL,
    RoundPhaseType.FIRST_SUMMARY,
    RoundPhaseType.SECOND_SUMMARY,
    RoundPhaseType.FIRST_FINAL_FOCUS,
    RoundPhaseType.SECOND_FINAL_FOCUS,
    RoundPhaseType.JUDGE_DELIBERATION,
    RoundPhaseType.COMPLETED,
]

# Speech-stage drill: just one speech + deliberation
_SPEECH_STAGE_DRILL_ORDER: List[RoundPhaseType] = [
    RoundPhaseType.FIRST_CONSTRUCTIVE,
    RoundPhaseType.JUDGE_DELIBERATION,
    RoundPhaseType.COMPLETED,
]

# Evidence-testing: constructives + crossfire + summaries
_EVIDENCE_TESTING_ORDER: List[RoundPhaseType] = [
    RoundPhaseType.FIRST_CONSTRUCTIVE,
    RoundPhaseType.SECOND_CONSTRUCTIVE,
    RoundPhaseType.FIRST_CROSSFIRE,
    RoundPhaseType.FIRST_SUMMARY,
    RoundPhaseType.SECOND_SUMMARY,
    RoundPhaseType.JUDGE_DELIBERATION,
    RoundPhaseType.COMPLETED,
]

# Crossfire phases where new evidence is prohibited
CROSSFIRE_PHASES = {
    RoundPhaseType.FIRST_CROSSFIRE,
    RoundPhaseType.GRAND_CROSSFIRE,
    RoundPhaseType.FINAL_CROSSFIRE,
}

# Phases where new independent arguments are prohibited
LATE_PHASES_NO_NEW_ARGS = {
    RoundPhaseType.FIRST_SUMMARY,
    RoundPhaseType.SECOND_SUMMARY,
    RoundPhaseType.FIRST_FINAL_FOCUS,
    RoundPhaseType.SECOND_FINAL_FOCUS,
}

# Speech-type labels for phases
PHASE_SPEECH_TYPES: Dict[RoundPhaseType, str] = {
    RoundPhaseType.FIRST_CONSTRUCTIVE: "constructive",
    RoundPhaseType.SECOND_CONSTRUCTIVE: "constructive",
    RoundPhaseType.FIRST_REBUTTAL: "rebuttal",
    RoundPhaseType.SECOND_REBUTTAL: "rebuttal",
    RoundPhaseType.FIRST_SUMMARY: "summary",
    RoundPhaseType.SECOND_SUMMARY: "summary",
    RoundPhaseType.FIRST_FINAL_FOCUS: "final_focus",
    RoundPhaseType.SECOND_FINAL_FOCUS: "final_focus",
}

# Human-readable phase labels
PHASE_LABELS: Dict[RoundPhaseType, str] = {
    RoundPhaseType.FIRST_CONSTRUCTIVE: "First Constructive",
    RoundPhaseType.SECOND_CONSTRUCTIVE: "Second Constructive",
    RoundPhaseType.FIRST_CROSSFIRE: "First Crossfire",
    RoundPhaseType.FIRST_REBUTTAL: "First Rebuttal",
    RoundPhaseType.SECOND_REBUTTAL: "Second Rebuttal",
    RoundPhaseType.GRAND_CROSSFIRE: "Grand Crossfire",
    RoundPhaseType.FIRST_SUMMARY: "First Summary",
    RoundPhaseType.SECOND_SUMMARY: "Second Summary",
    RoundPhaseType.FINAL_CROSSFIRE: "Final Crossfire",
    RoundPhaseType.FIRST_FINAL_FOCUS: "First Final Focus",
    RoundPhaseType.SECOND_FINAL_FOCUS: "Second Final Focus",
    RoundPhaseType.JUDGE_DELIBERATION: "Judge Deliberation",
    RoundPhaseType.COMPLETED: "Round Complete",
}


def get_phase_order(fmt: RoundFormat) -> List[RoundPhaseType]:
    """Return the ordered list of phases for the given format."""
    if fmt == RoundFormat.SHORTENED:
        return _SHORTENED_PHASE_ORDER
    if fmt == RoundFormat.SPEECH_STAGE_DRILL:
        return _SPEECH_STAGE_DRILL_ORDER
    if fmt == RoundFormat.EVIDENCE_TESTING:
        return _EVIDENCE_TESTING_ORDER
    return _FULL_PHASE_ORDER


def next_phase(
    current: RoundPhaseType,
    fmt: RoundFormat,
) -> Optional[RoundPhaseType]:
    """Return the next legal phase, or None if already at COMPLETED."""
    order = get_phase_order(fmt)
    try:
        idx = order.index(current)
    except ValueError:
        return None
    if idx + 1 >= len(order):
        return None
    return order[idx + 1]


def validate_phase_transition(
    current: RoundPhaseType,
    target: RoundPhaseType,
    fmt: RoundFormat,
    practice_override: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Returns (ok, error_message).
    Jumping forward is illegal without practice_override.
    Jumping backward is always illegal.
    """
    if current == RoundPhaseType.COMPLETED:
        return False, "Round is already completed."
    order = get_phase_order(fmt)
    try:
        cur_idx = order.index(current)
        tgt_idx = order.index(target)
    except ValueError:
        return False, f"Phase {target} is not part of {fmt} format."
    if tgt_idx <= cur_idx:
        return False, f"Cannot move backward from {current} to {target}."
    expected_next = order[cur_idx + 1]
    if target != expected_next and not practice_override:
        return False, (
            f"Expected next phase is {expected_next}, got {target}. "
            "Use practice_override=True to skip."
        )
    return True, None


def phase_speaker(
    phase: RoundPhaseType,
    config: RoundSimulationConfig,
) -> Optional[RoundSide]:
    """
    Return which side speaks in a given phase, or None for crossfire/deliberation/completed.
    First/second speaking order determines who gives FIRST_CONSTRUCTIVE.
    """
    if phase in CROSSFIRE_PHASES or phase in (
        RoundPhaseType.JUDGE_DELIBERATION,
        RoundPhaseType.COMPLETED,
    ):
        return None

    first_speaker_side = (
        RoundSide.PRO if config.speaking_order == SpeakingOrder.FIRST else RoundSide.CON
    )
    second_speaker_side = RoundSide.CON if first_speaker_side == RoundSide.PRO else RoundSide.PRO

    # Constructives: first, then second
    if phase == RoundPhaseType.FIRST_CONSTRUCTIVE:
        return first_speaker_side
    if phase == RoundPhaseType.SECOND_CONSTRUCTIVE:
        return second_speaker_side
    # Rebuttals: second speaker gives first rebuttal (standard PF)
    # In standard PF the rebuttal order mirrors constructive order
    if phase == RoundPhaseType.FIRST_REBUTTAL:
        return first_speaker_side
    if phase == RoundPhaseType.SECOND_REBUTTAL:
        return second_speaker_side
    # Summaries: first speaker of each team summarizes
    if phase == RoundPhaseType.FIRST_SUMMARY:
        return first_speaker_side
    if phase == RoundPhaseType.SECOND_SUMMARY:
        return second_speaker_side
    # Final focus: second speaker of each team
    if phase == RoundPhaseType.FIRST_FINAL_FOCUS:
        return first_speaker_side
    if phase == RoundPhaseType.SECOND_FINAL_FOCUS:
        return second_speaker_side
    return None


def student_speaks_in_phase(
    phase: RoundPhaseType,
    config: RoundSimulationConfig,
) -> bool:
    """Return True if the student should speak in this phase."""
    if phase in CROSSFIRE_PHASES:
        return True
    speaker = phase_speaker(phase, config)
    return speaker == config.student_side


def get_time_limit(phase: RoundPhaseType, config: RoundSimulationConfig) -> int:
    """Return time limit in seconds for the phase."""
    if phase in CROSSFIRE_PHASES:
        return config.crossfire_time
    speech_type = PHASE_SPEECH_TYPES.get(phase)
    if speech_type == "constructive":
        return config.constructive_time
    if speech_type == "rebuttal":
        return config.rebuttal_time
    if speech_type == "summary":
        return config.summary_time
    if speech_type == "final_focus":
        return config.final_focus_time
    return 0


def is_new_argument_legal(
    phase: RoundPhaseType,
    is_practice_override: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Return (legal, reason) for introducing a new independent argument."""
    if phase in LATE_PHASES_NO_NEW_ARGS:
        if is_practice_override:
            return True, "practice_override: new argument allowed in drill mode (labeled)"
        return False, f"New independent arguments are not permitted in {PHASE_LABELS.get(phase, phase)}."
    if phase in CROSSFIRE_PHASES:
        return False, "New arguments may not be introduced during crossfire."
    return True, None


def get_difficulty_params(difficulty: OpponentDifficulty) -> Dict[str, object]:
    """Return behavior parameters for a given difficulty level."""
    if difficulty == OpponentDifficulty.NOVICE:
        return {
            "max_arguments": 2,
            "response_depth": "shallow",
            "weighing_enabled": False,
            "evidence_indictments": False,
            "strategic_collapse": False,
            "speech_speed_wpm": 130,
            "coaching_hints_available": True,
            "signposting": "explicit",
        }
    if difficulty == OpponentDifficulty.VARSITY:
        return {
            "max_arguments": 4,
            "response_depth": "deep",
            "weighing_enabled": True,
            "evidence_indictments": True,
            "strategic_collapse": True,
            "speech_speed_wpm": 220,
            "coaching_hints_available": False,
            "signposting": "minimal",
        }
    # JV default
    return {
        "max_arguments": 3,
        "response_depth": "moderate",
        "weighing_enabled": True,
        "evidence_indictments": False,
        "strategic_collapse": False,
        "speech_speed_wpm": 170,
        "coaching_hints_available": False,
        "signposting": "standard",
    }
