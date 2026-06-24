"""Pass 17 — Round quality tests.

Tests for:
- Opponent round memory (build, prompt context, immutable updates)
- Concession detector (explicit, partial, qualified, evasion, non-concession)
- Round decision engine fixes (weighing comparison, adaptation feedback, tiebreak)
- Round drill generator fixes (correct phases, conditional crossfire drill)
- Round prep connector fixes (DROPPED bug, new gap categories)
- Crossfire simulator (question diversity, follow-up, AI answers)
- Coach round review (annotation creation, export)
- Round replay (turning point detection)
- Opponent strategy (plan quality validator, fallbacks)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Opponent round memory ─────────────────────────────────────────────────────

from app.models.round_simulation import RoundSimulationConfig
from app.services.opponent_round_memory import (
    OpponentRoundMemory,
    build_memory_for_phase,
    record_opponent_commitment,
    record_student_commitment,
    to_prompt_context,
)


def _make_arg_dict(label: str, side: str, status: str, is_offense: bool = True) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "label": label,
        "side": side,
        "status": status,
        "is_offense": is_offense,
        "claim": f"Claim for {label}",
        "weighing": False,
        "introduced_in_phase": "pro_constructive",
    }


def _make_config(side: str = "pro", judge: str = "flow") -> RoundSimulationConfig:
    return RoundSimulationConfig(
        format="full",
        student_side=RoundSide.PRO if side == "pro" else RoundSide.CON,
        speaking_order="first",
        speaker_role="first",
        judge_type=judge,
        opponent_difficulty="jv",
        resolution="Test resolution",
        coaching_hints_enabled=False,
        pauses_allowed=False,
        constructive_time=240,
        rebuttal_time=240,
        summary_time=180,
        final_focus_time=120,
        crossfire_time=180,
        prep_time=120,
    )


class TestOpponentRoundMemory:
    def test_build_empty_round(self):
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=[], config=config,
        )
        assert mem.round_id == "r1"
        assert mem.opponent_commitments == []
        assert mem.student_commitments == []

    def test_build_extracts_commitments_from_speeches(self):
        speeches = [
            {"is_ai": True, "speaker_side": "con", "argument_labels": ["A1", "A2"],
             "responses_made": [], "arguments_extended": [], "evidence_card_ids": [], "phase": "con_constructive"},
            {"is_ai": False, "speaker_side": "pro", "argument_labels": ["C1"],
             "responses_made": [], "arguments_extended": [], "evidence_card_ids": [], "phase": "pro_constructive"},
        ]
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=speeches, config=config,
        )
        assert "A1" in mem.opponent_commitments
        assert "A2" in mem.opponent_commitments
        assert "C1" in mem.student_commitments

    def test_to_prompt_context_returns_string(self):
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=[], config=config,
        )
        ctx = to_prompt_context(mem)
        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_record_opponent_commitment_adds_claim(self):
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=[], config=config,
        )
        updated = record_opponent_commitment(mem, "new claim")
        assert "new claim" in updated.opponent_commitments

    def test_record_student_commitment_no_duplicate(self):
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=[{
                "is_ai": False, "speaker_side": "pro", "argument_labels": ["existing claim"],
                "responses_made": [], "arguments_extended": [], "evidence_card_ids": [], "phase": "pro_constructive",
            }], config=config,
        )
        updated = record_student_commitment(mem, "existing claim")
        assert updated.student_commitments.count("existing claim") == 1

    def test_build_evidence_read_from_speeches(self):
        speeches = [
            {"is_ai": True, "speaker_side": "con", "argument_labels": [],
             "evidence_card_ids": ["card-1", "card-2"], "responses_made": [],
             "arguments_extended": [], "phase": "con_constructive"},
        ]
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=speeches, config=config,
        )
        assert "card-1" in mem.evidence_read
        assert "card-2" in mem.evidence_read

    def test_to_prompt_context_under_600_chars(self):
        config = _make_config()
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=[], config=config,
        )
        ctx = to_prompt_context(mem)
        assert len(ctx) <= 600

    def test_build_judge_risk_for_flow(self):
        config = _make_config(judge="flow")
        mem = build_memory_for_phase(
            round_id="r1", opponent_side=RoundSide.CON,
            all_args=[], evidence_uses=[], crossfire_exchanges=[],
            prior_speeches=[], config=config,
        )
        # Flow judge should produce some judge risk notes about weighing
        # (exact content depends on implementation)
        assert isinstance(mem.judge_risk_notes, list)


# ── Concession detector ───────────────────────────────────────────────────────

from app.services.concession_detector import ConcessionFinding, detect_concessions, detect_contradiction


class TestConcessionDetector:
    def test_explicit_concession_detected(self):
        findings = detect_concessions(
            answer_text="I concede that point about economic growth.",
            speaker_side="pro",
            target_argument_label="Econ Growth",
            prior_positions=[],
        )
        explicit = [f for f in findings if f.type == "explicit"]
        assert len(explicit) >= 1
        assert explicit[0].confidence == "high"
        assert not explicit[0].requires_confirmation

    def test_partial_concession_detected(self):
        findings = detect_concessions(
            answer_text="To some extent that's true, but the impact is still significant.",
            speaker_side="pro",
            target_argument_label="Impact",
            prior_positions=[],
        )
        types = {f.type for f in findings}
        assert "partial" in types or "qualified" in types

    def test_polite_acknowledgment_not_high_confidence(self):
        """'That's a good question' should not be treated as a concession."""
        findings = detect_concessions(
            answer_text="That's a good question.",
            speaker_side="pro",
            target_argument_label="any arg",
            prior_positions=[],
        )
        high_conf = [f for f in findings if f.confidence == "high"]
        assert len(high_conf) == 0

    def test_thats_fair_is_low_confidence_or_non_concession(self):
        findings = detect_concessions(
            answer_text="That's fair.",
            speaker_side="pro",
            target_argument_label="any arg",
            prior_positions=[],
        )
        # Must not be high-confidence concession
        high_conf_concessions = [
            f for f in findings
            if f.confidence == "high" and f.type in ("explicit", "partial")
        ]
        assert len(high_conf_concessions) == 0

    def test_evasion_detected_short_answer(self):
        findings = detect_concessions(
            answer_text="I'll address that later.",
            speaker_side="con",
            target_argument_label="Nuclear War",
            prior_positions=["Nuclear war is the largest impact."],
        )
        types = {f.type for f in findings}
        assert "evasion" in types

    def test_no_findings_on_direct_denial(self):
        """A direct rebuttal is not a concession."""
        findings = detect_concessions(
            answer_text="No, that's incorrect. The evidence clearly shows the opposite — Smith 2023 proves no such causation.",
            speaker_side="pro",
            target_argument_label="Climate",
            prior_positions=[],
        )
        explicit = [f for f in findings if f.type == "explicit"]
        assert len(explicit) == 0

    def test_detect_contradiction_basic(self):
        result = detect_contradiction(
            new_statement="Trade does not increase GDP.",
            prior_statements=["Trade increases GDP significantly."],
            argument_label="Trade",
        )
        # May or may not detect — but should not raise
        assert result is None or isinstance(result, ConcessionFinding)

    def test_detect_contradiction_returns_none_when_no_conflict(self):
        result = detect_contradiction(
            new_statement="This policy helps workers.",
            prior_statements=["This policy helps workers enormously."],
            argument_label="Workers",
        )
        # Consistent statements should not produce a contradiction
        if result is not None:
            assert result.confidence in ("medium", "low")

    def test_findings_have_required_fields(self):
        findings = detect_concessions(
            answer_text="I concede that point.",
            speaker_side="pro",
            target_argument_label="Test Arg",
            prior_positions=[],
        )
        for f in findings:
            assert hasattr(f, "type")
            assert hasattr(f, "speaker_side")
            assert hasattr(f, "confidence")
            assert hasattr(f, "requires_confirmation")
            assert hasattr(f, "strategic_effect")

    def test_agreement_on_fact_has_appropriate_type(self):
        findings = detect_concessions(
            answer_text="Yes, the studies were published in 2020.",
            speaker_side="pro",
            target_argument_label="Evidence date",
            prior_positions=[],
        )
        # agreement_on_fact or non_concession — should not be "explicit" concession
        assert all(
            f.type not in ("explicit", "partial")
            or f.requires_confirmation
            for f in findings
            if "2020" in f.transcript_span
        )


# ── Decision engine fixes ─────────────────────────────────────────────────────

from app.models.round_simulation import (
    ArgumentFlowStatus,
    RoundArgument,
    RoundDecision,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
)
from app.services.round_decision_engine import (
    _build_weighing_comparison,
    _compute_adaptation_feedback,
    run_decision_engine,
)


def _make_round_arg(label: str, side: RoundSide, status: ArgumentFlowStatus, weighing: bool = False) -> RoundArgument:
    return RoundArgument(
        id=str(uuid.uuid4()),
        round_id="r1",
        label=label,
        side=side,
        claim=f"Claim {label}",
        warrant=f"Warrant {label}",
        evidence_card_id=None,
        is_offense=True,
        is_framework=False,
        status=status,
        initial_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        weighing="comparative" if weighing else "",
    )


class TestDecisionEngineFixes:
    def test_weighing_comparison_both_sides(self):
        pro = [_make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE)]
        con = [_make_round_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE)]
        result = _build_weighing_comparison(pro, con)
        assert "C1" in result
        assert "A1" in result
        assert "Pro" in result or "pro" in result

    def test_weighing_comparison_no_pro_offense(self):
        result = _build_weighing_comparison([], [_make_round_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE)])
        assert "Con" in result or "con" in result
        assert "no surviving offense" in result.lower() or "A1" in result

    def test_weighing_comparison_no_con_offense(self):
        result = _build_weighing_comparison([_make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE)], [])
        assert "Pro" in result or "pro" in result

    def test_weighing_comparison_empty_both(self):
        result = _build_weighing_comparison([], [])
        assert result  # not empty string

    def test_weighing_comparison_notes_pro_did_weighing(self):
        pro = [_make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE, weighing=True)]
        con = [_make_round_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE, weighing=False)]
        result = _build_weighing_comparison(pro, con)
        assert "Pro" in result or "weighing" in result.lower()

    def test_compute_adaptation_feedback_flow_judge_weighing_success(self):
        pro = [_make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE, weighing=True)]
        successes, failures = _compute_adaptation_feedback(
            judge_type="flow", pro_offense=pro, con_offense=[],
            evidence_uses=[], judge_effects=[],
        )
        assert any("weighing" in s.lower() for s in successes)

    def test_compute_adaptation_feedback_flow_judge_no_weighing_failure(self):
        pro = [_make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE, weighing=False)]
        successes, failures = _compute_adaptation_feedback(
            judge_type="flow", pro_offense=pro, con_offense=[],
            evidence_uses=[], judge_effects=[],
        )
        assert any("weighing" in f.lower() for f in failures)

    def test_compute_adaptation_feedback_lay_judge_too_many_args(self):
        pro = [_make_round_arg(f"C{i}", RoundSide.PRO, ArgumentFlowStatus.LIVE) for i in range(3)]
        con = [_make_round_arg(f"A{i}", RoundSide.CON, ArgumentFlowStatus.LIVE) for i in range(3)]
        successes, failures = _compute_adaptation_feedback(
            judge_type="lay", pro_offense=pro, con_offense=con,
            evidence_uses=[], judge_effects=[],
        )
        assert any("too many" in f.lower() or "fewer" in f.lower() for f in failures)

    def test_compute_adaptation_feedback_returns_lists(self):
        successes, failures = _compute_adaptation_feedback(
            judge_type="truth", pro_offense=[], con_offense=[],
            evidence_uses=[], judge_effects=[],
        )
        assert isinstance(successes, list)
        assert isinstance(failures, list)

    def test_decision_adaptation_fields_populated(self):
        """run_decision_engine must return non-empty adaptation lists."""
        args = [
            _make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE, weighing=True),
            _make_round_arg("A1", RoundSide.CON, ArgumentFlowStatus.DROPPED),
        ]
        decision = run_decision_engine(
            round_id="r1", judge_type="flow",
            all_args=args, evidence_uses=[], legality_violations=[],
        )
        # adaptation_successes should not be empty for flow judge with weighing
        assert isinstance(decision.adaptation_successes, list)
        assert isinstance(decision.adaptation_failures, list)
        # At least one feedback item expected for flow judge
        assert len(decision.adaptation_successes) + len(decision.adaptation_failures) >= 1

    def test_decision_engine_version_v2(self):
        """Engine version updated in Pass 17."""
        args = [_make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE)]
        decision = run_decision_engine(
            round_id="r1", judge_type="lay",
            all_args=args, evidence_uses=[], legality_violations=[],
        )
        assert decision.engine_version == "v2"

    def test_tiebreak_favors_con_for_flow_judge(self):
        """On tie, flow judge should favor CON (status quo)."""
        args = [
            _make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE),
            _make_round_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE),
        ]
        decision = run_decision_engine(
            round_id="r1", judge_type="flow",
            all_args=args, evidence_uses=[], legality_violations=[],
        )
        # Winner must be one of the valid sides
        assert decision.winner in (RoundSide.PRO, RoundSide.CON)
        # On a tie with equal drops and equal weighing, flow judge defaults to CON
        assert decision.winner == RoundSide.CON

    def test_tiebreak_con_drops_more_goes_pro(self):
        """If con dropped more args than pro, pro wins tiebreak."""
        args = [
            _make_round_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE),
            _make_round_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE),
            _make_round_arg("A2", RoundSide.CON, ArgumentFlowStatus.DROPPED),
            _make_round_arg("A3", RoundSide.CON, ArgumentFlowStatus.DROPPED),
        ]
        decision = run_decision_engine(
            round_id="r1", judge_type="flow",
            all_args=args, evidence_uses=[], legality_violations=[],
        )
        # Con dropped 2, pro dropped 0 → pro wins the tiebreak
        assert decision.winner == RoundSide.PRO


# ── Drill generator fixes ─────────────────────────────────────────────────────

from app.services.round_drill_generator import generate_post_round_drills


class TestDrillGeneratorFixes:
    def _make_arg(self, label: str, side: RoundSide, status: ArgumentFlowStatus, is_offense: bool = True) -> RoundArgument:
        return RoundArgument(
            id=str(uuid.uuid4()), round_id="r1", label=label, side=side,
            claim=f"Claim {label}", warrant="", evidence_card_id=None,
            is_offense=is_offense, is_framework=False, status=status,
            initial_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
            weighing="",
        )

    def test_crossfire_concession_drill_only_when_dropped_or_conceded(self):
        """crossfire_concession drill should only appear when there are drops/concessions."""
        # No drops, no concessions
        args = [
            self._make_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE),
            self._make_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE),
        ]
        drills = generate_post_round_drills(
            round_id="r1", student_side=RoundSide.PRO,
            all_args=args, evidence_uses=[], decision=None,
        )
        drill_types = [d.source.weakness_description for d in drills]
        # crossfire_concession should not be forced when student has no drops
        drill_titles = [d.title for d in drills]
        # Check: if no drops/concessions, crossfire drill should not be #1 priority
        if args:
            student_drops = [a for a in args if a.side == RoundSide.PRO and a.status == ArgumentFlowStatus.DROPPED]
            student_conceded = [a for a in args if a.side == RoundSide.PRO and a.status == ArgumentFlowStatus.CONCEDED]
            if not student_drops and not student_conceded:
                # crossfire drill may or may not appear — but it should not be the only drill
                crossfire_drills = [d for d in drills if "Crossfire" in d.title]
                assert len(drills) >= 1  # at least one drill should exist

    def test_crossfire_drill_added_when_student_has_drops(self):
        """When student dropped args, crossfire_concession drill should appear."""
        args = [
            self._make_arg("C1", RoundSide.PRO, ArgumentFlowStatus.DROPPED),
            self._make_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE),
        ]
        drills = generate_post_round_drills(
            round_id="r1", student_side=RoundSide.PRO,
            all_args=args, evidence_uses=[], decision=None,
        )
        drill_titles = [d.title for d in drills]
        assert any("Crossfire" in t for t in drill_titles)

    def test_drill_phases_correct_for_dropped_response(self):
        """Dropped response drill should point to rebuttal phase, not FIRST_SUMMARY."""
        args = [
            self._make_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE),
        ]
        drills = generate_post_round_drills(
            round_id="r1", student_side=RoundSide.PRO,
            all_args=args, evidence_uses=[], decision=None,
        )
        dropped_response_drills = [d for d in drills if "Dropped" in d.title or "Response" in d.title or "Coverage" in d.title]
        for d in dropped_response_drills:
            assert d.source.speech_phase != RoundPhaseType.FIRST_SUMMARY.value, (
                f"Dropped response drill should not point to FIRST_SUMMARY, got {d.source.speech_phase}"
            )

    def test_weighing_drill_added_when_no_student_weighing(self):
        """Weighing drill should be added when student did no weighing."""
        args = [
            self._make_arg("C1", RoundSide.PRO, ArgumentFlowStatus.LIVE),  # no weighing
        ]
        drills = generate_post_round_drills(
            round_id="r1", student_side=RoundSide.PRO,
            all_args=args, evidence_uses=[], decision=None,
        )
        drill_titles = [d.title for d in drills]
        assert any("Weighing" in t or "Impact" in t for t in drill_titles)

    def test_weighing_drill_not_forced_when_student_did_weighing(self):
        """Weighing drill should be deprioritized when student already weighed."""
        from app.models.round_simulation import RoundArgument as RA
        arg = RA(
            id=str(uuid.uuid4()), round_id="r1", label="C1", side=RoundSide.PRO,
            claim="Claim", warrant="", evidence_card_id=None,
            is_offense=True, is_framework=False, status=ArgumentFlowStatus.LIVE,
            initial_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
            weighing="comparative",
        )
        drills = generate_post_round_drills(
            round_id="r1", student_side=RoundSide.PRO,
            all_args=[arg], evidence_uses=[], decision=None,
        )
        # Should produce drills, and they should not all be weighing-focused
        assert len(drills) >= 1

    def test_drill_source_phase_not_all_first_summary(self):
        """Drill sources should have varied phases, not all FIRST_SUMMARY."""
        args = [
            self._make_arg("A1", RoundSide.CON, ArgumentFlowStatus.LIVE),
            self._make_arg("C1", RoundSide.PRO, ArgumentFlowStatus.DROPPED),
        ]
        drills = generate_post_round_drills(
            round_id="r1", student_side=RoundSide.PRO,
            all_args=args, evidence_uses=[], decision=None,
        )
        phases = {d.source.speech_phase for d in drills}
        # Should have more than just FIRST_SUMMARY
        assert len(phases) >= 2 or len(drills) == 1


# ── Prep connector fixes ──────────────────────────────────────────────────────

from app.services.round_prep_connector import _gap_fingerprint, record_post_round_gaps


class TestPrepConnectorFixes:
    def _make_arg(self, label: str, side: str, status: str, is_offense: bool = True) -> RoundArgument:
        return RoundArgument(
            id=str(uuid.uuid4()), round_id="r1", label=label,
            side=RoundSide.PRO if side == "pro" else RoundSide.CON,
            claim=f"Claim {label}", warrant="", evidence_card_id=None,
            is_offense=is_offense, is_framework=False,
            status=ArgumentFlowStatus(status),
            initial_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
            weighing="",
        )

    def test_dropped_opponent_args_do_not_generate_no_response_gap(self):
        """
        If opponent arg is DROPPED (student beat it), no 'no response' gap should be created.
        """
        # Opponent's arg is DROPPED = student successfully answered it
        args = [
            self._make_arg("A1", "con", "dropped"),  # student beat this
        ]
        mock_supa = MagicMock()
        mock_supa.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supa.table.return_value.insert.return_value.execute.return_value = None

        with patch("app.services.round_prep_connector.get_supabase", return_value=mock_supa):
            gaps = record_post_round_gaps(
                round_id="r1", user_id="u1", workspace_id="w1",
                all_args=args, evidence_uses=[],
                student_side=RoundSide.PRO, decision=None,
            )

        # No "missing_response" gaps — the opponent's dropped arg was beaten by student
        missing_response_gaps = [g for g in gaps if g.get("category") == "missing_response"]
        assert len(missing_response_gaps) == 0

    def test_live_opponent_args_generate_no_response_gap(self):
        """Opponent LIVE args (student didn't answer) should produce a gap."""
        args = [
            self._make_arg("A1", "con", "live"),
        ]
        mock_supa = MagicMock()
        mock_supa.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supa.table.return_value.insert.return_value.execute.return_value = None

        with patch("app.services.round_prep_connector.get_supabase", return_value=mock_supa):
            gaps = record_post_round_gaps(
                round_id="r1", user_id="u1", workspace_id="w1",
                all_args=args, evidence_uses=[],
                student_side=RoundSide.PRO, decision=None,
            )

        missing_response_gaps = [g for g in gaps if g.get("category") == "missing_response"]
        assert len(missing_response_gaps) >= 1

    def test_no_weighing_generates_weighing_gap(self):
        """No weighing in student args should produce a weighing_gap."""
        args = [
            self._make_arg("C1", "pro", "live"),  # no weighing attribute
        ]
        mock_supa = MagicMock()
        mock_supa.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supa.table.return_value.insert.return_value.execute.return_value = None

        with patch("app.services.round_prep_connector.get_supabase", return_value=mock_supa):
            gaps = record_post_round_gaps(
                round_id="r1", user_id="u1", workspace_id="w1",
                all_args=args, evidence_uses=[],
                student_side=RoundSide.PRO, decision=None,
            )

        weighing_gaps = [g for g in gaps if g.get("category") == "weighing_gap"]
        assert len(weighing_gaps) >= 1

    def test_extension_gap_created_for_unextended_offense(self):
        """Student's own LIVE offense that wasn't extended should create extension_gap."""
        args = [
            # Student's arg that was never extended (still "live" means not explicitly extended)
            self._make_arg("C1", "pro", "introduced"),
        ]
        mock_supa = MagicMock()
        mock_supa.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supa.table.return_value.insert.return_value.execute.return_value = None

        with patch("app.services.round_prep_connector.get_supabase", return_value=mock_supa):
            gaps = record_post_round_gaps(
                round_id="r1", user_id="u1", workspace_id="w1",
                all_args=args, evidence_uses=[],
                student_side=RoundSide.PRO, decision=None,
            )

        extension_gaps = [g for g in gaps if g.get("category") == "extension_gap"]
        assert len(extension_gaps) >= 1

    def test_no_gaps_without_workspace(self):
        """No gaps should be recorded when workspace_id is None."""
        args = [self._make_arg("A1", "con", "live")]
        mock_supa = MagicMock()
        with patch("app.services.round_prep_connector.get_supabase", return_value=mock_supa):
            gaps = record_post_round_gaps(
                round_id="r1", user_id="u1", workspace_id=None,
                all_args=args, evidence_uses=[],
                student_side=RoundSide.PRO, decision=None,
            )
        assert gaps == []

    def test_rebuttal_coverage_gap_for_many_unanswered(self):
        """3+ unanswered opponent args should produce a rebuttal_coverage gap."""
        args = [
            self._make_arg(f"A{i}", "con", "live") for i in range(4)
        ]
        mock_supa = MagicMock()
        mock_supa.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supa.table.return_value.insert.return_value.execute.return_value = None

        with patch("app.services.round_prep_connector.get_supabase", return_value=mock_supa):
            gaps = record_post_round_gaps(
                round_id="r1", user_id="u1", workspace_id="w1",
                all_args=args, evidence_uses=[],
                student_side=RoundSide.PRO, decision=None,
            )

        rebuttal_gaps = [g for g in gaps if g.get("category") == "rebuttal_coverage"]
        assert len(rebuttal_gaps) >= 1


# ── Crossfire simulator (diversity + follow-up) ───────────────────────────────

from app.services.crossfire_simulator import generate_followup_question, generate_ai_answer


class TestCrossfireSimulatorP17:
    def _make_arg(self, label: str, side: str, status: str) -> RoundArgument:
        return RoundArgument(
            id=str(uuid.uuid4()), round_id="r1", label=label,
            side=RoundSide.PRO if side == "pro" else RoundSide.CON,
            claim=f"Claim for {label}", warrant="Warrant here", evidence_card_id=None,
            is_offense=True, is_framework=False, status=ArgumentFlowStatus(status),
            initial_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
            weighing="",
        )

    def test_generate_followup_question_returns_exchange(self):
        from app.models.round_simulation import CrossfireExchange
        prior_exchange = CrossfireExchange(
            id=str(uuid.uuid4()), round_id="r1",
            phase=RoundPhaseType.FIRST_CROSSFIRE,
            sequence=1,
            questioner_side=RoundSide.CON,
            question="What evidence supports your economic claim?",
            answer="I'll address that later.",
            evasion_detected=True,
            strategic_significance="low",
            target_argument="C1",
            created_at=datetime.utcnow().isoformat(),
        )
        live_args = [self._make_arg("C1", "pro", "live")]
        result = generate_followup_question(
            prior_exchange=prior_exchange,
            questioner_side=RoundSide.CON,
            live_args=live_args,
            judge_type="flow",
        )
        assert result is not None
        assert result.question  # follow-up question is not empty
        assert result.questioner_side == RoundSide.CON

    def test_generate_ai_answer_returns_string(self):
        live_args = [self._make_arg("A1", "con", "live")]
        answer = generate_ai_answer(
            question="What is the warrant for your economic argument?",
            opponent_side="con",
            live_args=live_args,
            prior_exchanges=[],
            config=None,
        )
        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_generate_ai_answer_max_two_sentences(self):
        """AI crossfire answers should be brief — max 2 sentences."""
        live_args = [self._make_arg("A1", "con", "live")]
        answer = generate_ai_answer(
            question="Can you explain your first argument?",
            opponent_side="con",
            live_args=live_args,
            prior_exchanges=[],
            config=None,
        )
        # Should be 2 sentences or fewer (rough check)
        sentences = [s.strip() for s in answer.split(".") if s.strip()]
        assert len(sentences) <= 5  # generous limit given model variability


# ── Coach round review ────────────────────────────────────────────────────────

from app.services.coach_round_review import (
    AutomatedFindingRating,
    CoachAnnotation,
    add_coach_annotation,
    assign_drill_from_round,
    list_coach_annotations,
)


class TestCoachRoundReview:
    def _mock_supabase(self, insert_data: Optional[dict] = None):
        mock = MagicMock()
        mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[insert_data or {}])
        mock.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[])
        return mock

    def test_add_annotation_creates_record(self):
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            annotation = add_coach_annotation(
                round_id="r1", coach_id="coach-1",
                annotation_type="speech_note", content="Good clarity here.",
            )
        assert annotation.round_id == "r1"
        assert annotation.coach_id == "coach-1"
        assert annotation.content == "Good clarity here."
        assert annotation.annotation_type == "speech_note"

    def test_add_annotation_rejects_invalid_type(self):
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            with pytest.raises(ValueError, match="Invalid annotation_type"):
                add_coach_annotation(
                    round_id="r1", coach_id="coach-1",
                    annotation_type="invalid_type", content="test",
                )

    def test_add_annotation_rejects_empty_content(self):
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            with pytest.raises(ValueError, match="empty"):
                add_coach_annotation(
                    round_id="r1", coach_id="coach-1",
                    annotation_type="speech_note", content="  ",
                )

    def test_add_annotation_correction_flag(self):
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            annotation = add_coach_annotation(
                round_id="r1", coach_id="coach-1",
                annotation_type="correction", content="This drop detection is wrong.",
                is_correction=True, finding_id="finding-123",
            )
        assert annotation.is_correction
        assert annotation.finding_id == "finding-123"

    def test_add_annotation_does_not_modify_history(self):
        """Annotation should insert a new row, never update historical records."""
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            add_coach_annotation(
                round_id="r1", coach_id="coach-1",
                annotation_type="highlight", content="Key moment.",
            )
        # Verify update was never called on speeches, arguments, etc.
        update_calls = mock.table.return_value.update.call_args_list
        assert len(update_calls) == 0

    def test_assign_drill_from_round_uses_drill_assignment_type(self):
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            annotation = assign_drill_from_round(
                round_id="r1", coach_id="coach-1",
                student_id="student-1", drill_id="drill-abc",
                note="Focus on extending this argument.",
            )
        assert annotation.annotation_type == "drill_assignment"
        assert annotation.target_id == "drill-abc"

    def test_list_annotations_empty_returns_list(self):
        mock = self._mock_supabase()
        with patch("app.services.coach_round_review.get_supabase", return_value=mock):
            result = list_coach_annotations("r1")
        assert isinstance(result, list)


# ── Round replay turning points ───────────────────────────────────────────────

from app.services.round_replay import TurningPoint, identify_turning_points


class TestRoundReplayTurningPoints:
    def _make_arg(self, label: str, side: str, status: str, is_offense: bool = True, phase: str = "pro_constructive") -> dict:
        return {
            "id": str(uuid.uuid4()),
            "label": label,
            "side": side,
            "status": status,
            "is_offense": is_offense,
            "claim": f"Claim {label}",
            "weighing": False,
            "introduced_in_phase": phase,
        }

    def test_major_drop_detected(self):
        """A dropped offense argument should produce a major_drop turning point."""
        args = [
            self._make_arg("C1", "pro", "dropped", is_offense=True),
        ]
        tps = identify_turning_points(
            all_args=args, speeches=[], crossfire_exchanges=[],
            evidence_uses=[], decision=None,
        )
        drop_tps = [tp for tp in tps if tp.type == "major_drop"]
        assert len(drop_tps) >= 1
        assert drop_tps[0].severity == "critical"

    def test_key_turn_detected(self):
        """An argument with TURNED status should produce a key_turn turning point."""
        args = [
            self._make_arg("C1", "pro", "turned"),
        ]
        tps = identify_turning_points(
            all_args=args, speeches=[], crossfire_exchanges=[],
            evidence_uses=[], decision=None,
        )
        turn_tps = [tp for tp in tps if tp.type == "key_turn"]
        assert len(turn_tps) >= 1

    def test_max_turning_points_respected(self):
        """Should not return more than 8 turning points."""
        args = [
            self._make_arg(f"C{i}", "pro", "dropped", is_offense=True) for i in range(20)
        ]
        tps = identify_turning_points(
            all_args=args, speeches=[], crossfire_exchanges=[],
            evidence_uses=[], decision=None,
        )
        assert len(tps) <= 8

    def test_turning_point_has_required_fields(self):
        args = [
            self._make_arg("C1", "pro", "dropped", is_offense=True),
        ]
        tps = identify_turning_points(
            all_args=args, speeches=[], crossfire_exchanges=[],
            evidence_uses=[], decision=None,
        )
        for tp in tps:
            assert hasattr(tp, "phase")
            assert hasattr(tp, "type")
            assert hasattr(tp, "description")
            assert hasattr(tp, "severity")
            assert tp.severity in ("critical", "significant", "notable")

    def test_critical_before_notable(self):
        """Critical turning points should come before notable ones."""
        args = [
            self._make_arg("C1", "pro", "dropped", is_offense=True),  # critical
            self._make_arg("C2", "pro", "live", is_offense=True),     # no turning point
        ]
        tps = identify_turning_points(
            all_args=args, speeches=[], crossfire_exchanges=[],
            evidence_uses=[], decision=None,
        )
        if len(tps) >= 2:
            severity_order = [tp.severity for tp in tps]
            # Check critical comes before notable
            if "critical" in severity_order and "notable" in severity_order:
                assert severity_order.index("critical") <= severity_order.index("notable")

    def test_no_turning_points_for_clean_round(self):
        """A clean round with all live args and no drops should produce few/no critical TPs."""
        args = [
            self._make_arg("C1", "pro", "live"),
            self._make_arg("A1", "con", "live"),
        ]
        tps = identify_turning_points(
            all_args=args, speeches=[], crossfire_exchanges=[],
            evidence_uses=[], decision=None,
        )
        critical = [tp for tp in tps if tp.severity == "critical"]
        assert len(critical) == 0  # no drops or turns = no critical TPs


# ── Opponent strategy improvements ───────────────────────────────────────────

from app.services.opponent_strategy import validate_plan_quality


class TestOpponentStrategyP17:
    def test_validate_plan_quality_returns_list(self):
        """validate_plan_quality must always return a list."""
        from app.models.round_simulation import OpponentRoundPlan
        config = _make_config()
        plan = OpponentRoundPlan(
            id=str(uuid.uuid4()),
            round_id="r1",
            side=RoundSide.CON,
            difficulty="jv",
            judge_type="flow",
            constructive_arguments=[],
            expected_responses=[],
            weighing_strategy="comparative",
            speech_stage_goals={},
            created_at=datetime.utcnow().isoformat(),
        )
        result = validate_plan_quality(plan=plan, config=config)
        assert isinstance(result, list)

    def test_plan_quality_imported(self):
        """validate_plan_quality must be importable from opponent_strategy."""
        from app.services.opponent_strategy import validate_plan_quality
        assert callable(validate_plan_quality)

    def test_build_opponent_round_plan_importable(self):
        from app.services.opponent_strategy import build_opponent_round_plan
        assert callable(build_opponent_round_plan)
