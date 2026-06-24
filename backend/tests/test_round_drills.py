"""Pass 16 — Post-round drill generation tests.

Covers:
- Drills generated from dropped arguments
- Drills generated from evidence violations
- Drills linked to specific round/phase/argument
- Max drill limit respected
- Skill targets are valid
- Success criteria present
- Drills do not fabricate evidence
"""
from __future__ import annotations
import uuid
import pytest

from app.models.round_simulation import (
    ArgumentFlowStatus,
    RoundArgument,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
)
from app.services.round_drill_generator import (
    _DRILL_TEMPLATES,
    _choose_drill_types,
    generate_post_round_drills,
)


def _arg(
    label="AC1",
    side=RoundSide.PRO,
    status=ArgumentFlowStatus.LIVE,
) -> RoundArgument:
    return RoundArgument(
        id=str(uuid.uuid4()),
        round_id="r1",
        label=label,
        side=side,
        claim=f"Claim for {label}",
        initial_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        status=status,
    )


def _use(side=RoundSide.PRO, flagged=False, violations=None) -> RoundEvidenceUse:
    return RoundEvidenceUse(
        id=str(uuid.uuid4()),
        round_id="r1",
        speech_id="s1",
        card_id=str(uuid.uuid4()),
        speaker_side=side,
        phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        flagged=flagged,
        violations=violations or [],
        created_at="2026-06-23T00:00:00",
    )


# ── _choose_drill_types ────────────────────────────────────────────────────────

class TestChooseDrillTypes:
    def test_dropped_response_for_live_opponent_arg(self):
        opponent_arg = _arg("NC1", RoundSide.CON, ArgumentFlowStatus.LIVE)
        types = _choose_drill_types([opponent_arg], [], None, RoundSide.PRO, [])
        assert "dropped_response" in types

    def test_evidence_explanation_for_flagged_evidence(self):
        flagged = _use(RoundSide.PRO, flagged=True, violations=["missing_citation"])
        types = _choose_drill_types([], [flagged], None, RoundSide.PRO, [])
        assert "evidence_explanation" in types

    def test_weighing_drill_when_no_weighing_success(self):
        types = _choose_drill_types([], [], None, RoundSide.PRO, [])
        assert "weighing" in types

    def test_summary_extension_for_legality_violation(self):
        violations = [{"type": "dropped_offense", "description": "Offense dropped."}]
        types = _choose_drill_types([], [], None, RoundSide.PRO, violations)
        assert "summary_extension" in types

    def test_max_5_types_returned(self):
        args = [
            _arg("NC1", RoundSide.CON, ArgumentFlowStatus.LIVE),
            _arg("NC2", RoundSide.CON, ArgumentFlowStatus.EXTENDED),
        ]
        flagged = _use(RoundSide.PRO, flagged=True)
        types = _choose_drill_types(args, [flagged], None, RoundSide.PRO, [])
        assert len(types) <= 5


# ── generate_post_round_drills ─────────────────────────────────────────────────

class TestGeneratePostRoundDrills:
    def test_drills_generated_with_no_args(self):
        drills = generate_post_round_drills("r1", RoundSide.PRO, [], [], None)
        assert len(drills) > 0

    def test_max_drills_respected(self):
        args = [_arg(f"NC{i}", RoundSide.CON, ArgumentFlowStatus.LIVE) for i in range(5)]
        drills = generate_post_round_drills("r1", RoundSide.PRO, args, [], None, max_drills=3)
        assert len(drills) <= 3

    def test_drill_has_required_fields(self):
        drills = generate_post_round_drills("r1", RoundSide.PRO, [], [], None)
        for d in drills:
            assert d.id
            assert d.round_id == "r1"
            assert d.skill_target
            assert d.title
            assert d.prompt
            assert len(d.success_criteria) > 0
            assert d.time_limit_seconds >= 30

    def test_drill_source_links_round_id(self):
        drills = generate_post_round_drills("r1", RoundSide.PRO, [], [], None)
        for d in drills:
            assert d.source.round_id == "r1"

    def test_drill_for_dropped_arg_links_label(self):
        opponent_arg = _arg("NC1", RoundSide.CON, ArgumentFlowStatus.LIVE)
        drills = generate_post_round_drills("r1", RoundSide.PRO, [opponent_arg], [], None)
        dropped_drills = [d for d in drills if d.skill_target == "drops"]
        if dropped_drills:
            assert dropped_drills[0].source.argument_label == "NC1"

    def test_drill_for_evidence_violation_links_card(self):
        flagged = _use(RoundSide.PRO, flagged=True, violations=["missing_citation"])
        drills = generate_post_round_drills("r1", RoundSide.PRO, [], [flagged], None)
        evidence_drills = [d for d in drills if d.skill_target == "evidence"]
        if evidence_drills:
            assert evidence_drills[0].source.card_id is not None

    def test_skill_targets_are_valid(self):
        # Use the semantic skill_target values, not the template key names
        valid_targets = {
            "drops", "clash", "extensions", "evidence", "weighing",
            "judge_adaptation", "pacing_control",
        }
        drills = generate_post_round_drills("r1", RoundSide.PRO, [], [], None)
        for d in drills:
            assert d.skill_target in valid_targets, f"Unknown skill target: {d.skill_target}"

    def test_no_fabricated_evidence_in_prompt(self):
        """Drill prompts should not contain invented evidence or citations."""
        drills = generate_post_round_drills("r1", RoundSide.PRO, [], [], None)
        for d in drills:
            # Prompts should not reference specific fake studies
            assert "Harvard" not in d.prompt or "practice" in d.prompt.lower()
            assert "fake evidence" not in d.prompt.lower()


# ── Drill template completeness ────────────────────────────────────────────────

class TestDrillTemplates:
    def test_all_templates_have_required_fields(self):
        for name, tmpl in _DRILL_TEMPLATES.items():
            assert "skill_target" in tmpl, f"{name} missing skill_target"
            assert "title" in tmpl, f"{name} missing title"
            assert "prompt" in tmpl, f"{name} missing prompt"
            assert "success_criteria" in tmpl, f"{name} missing success_criteria"
            assert "time_limit_seconds" in tmpl, f"{name} missing time_limit_seconds"

    def test_time_limits_within_range(self):
        for name, tmpl in _DRILL_TEMPLATES.items():
            t = tmpl["time_limit_seconds"]
            assert 30 <= t <= 300, f"{name} time_limit {t} out of range"

    def test_success_criteria_non_empty(self):
        for name, tmpl in _DRILL_TEMPLATES.items():
            assert len(tmpl["success_criteria"]) >= 2, f"{name} needs at least 2 criteria"

    def test_all_skill_targets_are_known(self):
        known_targets = {
            "drops", "clash", "extensions", "evidence", "weighing",
            "judge_adaptation", "pacing_control",
        }
        for name, tmpl in _DRILL_TEMPLATES.items():
            assert tmpl["skill_target"] in known_targets, \
                f"{name} has unknown skill_target {tmpl['skill_target']}"
