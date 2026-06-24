"""Pass 16 — Speech legality checker tests.

Covers:
- Constructive legality (minimal requirements)
- Rebuttal clash requirement
- Summary new-argument prohibition
- Summary weighing requirement
- Summary extension requirement
- Final focus new-argument prohibition
- Final focus weighing requirement
- Final focus consistency with summary
- Crossfire no-new-evidence rule
"""
from __future__ import annotations
import uuid
import pytest

from app.models.round_simulation import (
    ArgumentFlowStatus,
    RoundArgument,
    RoundPhaseType as RPT,
    RoundSide,
    SpeechLegalityViolationType,
)
from app.services.speech_legality_checker import (
    check_constructive,
    check_crossfire,
    check_final_focus,
    check_rebuttal,
    check_summary,
    check_speech_legality,
)


def _arg(
    label="AC1",
    side=RoundSide.PRO,
    status=ArgumentFlowStatus.INTRODUCED,
    claim="Economic harms are significant.",
) -> RoundArgument:
    return RoundArgument(
        id=str(uuid.uuid4()),
        round_id="r1",
        label=label,
        side=side,
        claim=claim,
        initial_phase=RPT.FIRST_CONSTRUCTIVE,
        status=status,
    )


# ── Constructive ───────────────────────────────────────────────────────────────

class TestCheckConstructive:
    def test_empty_speech_flagged(self):
        violations = check_constructive("", RoundSide.PRO, [])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.DROPPED_OFFENSE in types

    def test_substantial_speech_passes(self):
        transcript = "My name is X. We stand in firm affirmation. " * 10
        violations = check_constructive(transcript, RoundSide.PRO, [])
        assert violations == []


# ── Rebuttal ───────────────────────────────────────────────────────────────────

class TestCheckRebuttal:
    def test_missing_clash_when_opponent_live(self):
        opponent_arg = _arg("NC1", RoundSide.CON, ArgumentFlowStatus.INTRODUCED)
        violations = check_rebuttal("We extend our case.", RoundSide.PRO, [opponent_arg])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.MISSING_CLASH in types

    def test_no_violation_when_opponent_mentioned(self):
        opponent_arg = _arg("NC1", RoundSide.CON, ArgumentFlowStatus.INTRODUCED)
        violations = check_rebuttal("Turning to NC1: their warrant fails.", RoundSide.PRO, [opponent_arg])
        assert violations == []

    def test_no_violation_when_no_opponent_args(self):
        # No opponent args yet → no clash required
        violations = check_rebuttal("We extend AC1.", RoundSide.PRO, [])
        assert violations == []

    def test_dropped_opponent_arg_no_clash_required(self):
        opponent_arg = _arg("NC1", RoundSide.CON, ArgumentFlowStatus.DROPPED)
        violations = check_rebuttal("We extend our case.", RoundSide.PRO, [opponent_arg])
        # Dropped arg doesn't require clash
        clash_violations = [v for v in violations if v.type == SpeechLegalityViolationType.MISSING_CLASH]
        assert len(clash_violations) == 0


# ── Summary ────────────────────────────────────────────────────────────────────

class TestCheckSummary:
    def test_new_argument_language_flagged(self):
        transcript = "Firstly, I want to argue a new contention: the economy is harmed."
        violations = check_summary(transcript, RoundSide.PRO, [])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.NEW_ARGUMENT_IN_SUMMARY in types

    def test_no_weighing_flagged(self):
        transcript = "We extend AC1 through the flow. Our argument stands."
        own_arg = _arg("AC1", RoundSide.PRO, ArgumentFlowStatus.LIVE)
        violations = check_summary(transcript, RoundSide.PRO, [own_arg])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.MISSING_WEIGHING in types

    def test_weighing_present_clears_violation(self):
        transcript = "Extend AC1. It outweighs NC1 on magnitude and probability."
        own_arg = _arg("AC1", RoundSide.PRO, ArgumentFlowStatus.EXTENDED)
        violations = check_summary(transcript, RoundSide.PRO, [own_arg])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.MISSING_WEIGHING not in types

    def test_dropped_offense_flagged_when_no_extension(self):
        transcript = "We acknowledge the round has been close."
        own_arg = _arg("AC1", RoundSide.PRO, ArgumentFlowStatus.LIVE)
        violations = check_summary(transcript, RoundSide.PRO, [own_arg])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.DROPPED_OFFENSE in types

    def test_extension_clears_dropped_offense(self):
        transcript = "We extend AC1 through the flow and it outweighs NC1 on magnitude."
        own_arg = _arg("AC1", RoundSide.PRO, ArgumentFlowStatus.LIVE)
        violations = check_summary(transcript, RoundSide.PRO, [own_arg])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.DROPPED_OFFENSE not in types


# ── Final focus ────────────────────────────────────────────────────────────────

class TestCheckFinalFocus:
    def test_new_argument_flagged(self):
        transcript = "I want to introduce an additional reason to vote pro: health impacts."
        violations = check_final_focus(transcript, RoundSide.PRO, [])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.NEW_ARGUMENT_IN_FINAL_FOCUS in types

    def test_missing_weighing_flagged(self):
        transcript = "Our AC1 argument stands. Please vote pro."
        violations = check_final_focus(transcript, RoundSide.PRO, [])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.MISSING_WEIGHING in types

    def test_consistency_check_when_summary_present(self):
        summary = "We extend AC1 through the flow."
        final_focus = "Our NC2 argument is the decisive voter."
        violations = check_final_focus(final_focus, RoundSide.PRO, [], summary_transcript=summary)
        types = [v.type for v in violations]
        # AC1 not mentioned in final focus → inconsistency
        assert SpeechLegalityViolationType.INCONSISTENT_WITH_SUMMARY in types

    def test_consistent_final_focus_passes(self):
        summary = "We extend AC1 through the flow."
        final_focus = "AC1 is the voter. It outweighs on magnitude."
        violations = check_final_focus(final_focus, RoundSide.PRO, [], summary_transcript=summary)
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.INCONSISTENT_WITH_SUMMARY not in types


# ── Crossfire ──────────────────────────────────────────────────────────────────

class TestCheckCrossfire:
    def test_new_evidence_flagged(self):
        violations = check_crossfire("Can you clarify?", ["card-1", "card-2"])
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.NEW_EVIDENCE_IN_CROSSFIRE in types

    def test_no_new_evidence_passes(self):
        violations = check_crossfire("Can you explain your warrant?", [])
        assert violations == []


# ── Top-level dispatcher ───────────────────────────────────────────────────────

class TestCheckSpeechLegalityDispatcher:
    def test_dispatches_to_constructive(self):
        violations = check_speech_legality(
            RPT.FIRST_CONSTRUCTIVE, "", RoundSide.PRO, []
        )
        # Should get DROPPED_OFFENSE for empty speech
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.DROPPED_OFFENSE in types

    def test_dispatches_to_rebuttal(self):
        arg = _arg("NC1", RoundSide.CON, ArgumentFlowStatus.INTRODUCED)
        violations = check_speech_legality(
            RPT.FIRST_REBUTTAL, "We extend.", RoundSide.PRO, [arg]
        )
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.MISSING_CLASH in types

    def test_dispatches_to_summary(self):
        violations = check_speech_legality(
            RPT.FIRST_SUMMARY,
            "Firstly I want to argue a new reason.",
            RoundSide.PRO,
            [],
        )
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.NEW_ARGUMENT_IN_SUMMARY in types

    def test_dispatches_to_crossfire(self):
        violations = check_speech_legality(
            RPT.FIRST_CROSSFIRE,
            "Can you explain?",
            RoundSide.PRO,
            [],
            new_card_ids=["new-card"],
        )
        types = [v.type for v in violations]
        assert SpeechLegalityViolationType.NEW_EVIDENCE_IN_CROSSFIRE in types

    def test_unknown_phase_returns_empty(self):
        violations = check_speech_legality(
            RPT.JUDGE_DELIBERATION, "...", RoundSide.PRO, []
        )
        assert violations == []
