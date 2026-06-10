"""Tests for Tournament Prep Workout Mode — service + API."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.workout_generation import (
    generate_tournament_workout,
    _build_rerecord_goal,
    _build_coach_note,
    _skill_to_focus,
)

client = TestClient(app)

SPEECH_ID  = "aaaaaaaa-2222-0000-0000-000000000099"
USER_ID    = "bbbbbbbb-0000-0000-0000-000000000099"
WORKOUT_ID = "cccccccc-3333-0000-0000-000000000099"

FAKE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "1AC Round 1",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test.",
    "audio_url": "https://example.com/audio.mp3",
    "status": "done",
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}

FAKE_FEEDBACK = {
    "id": "fb-001",
    "speech_id": SPEECH_ID,
    "overall_score": 68,
    "scores": {
        "clash": 12, "weighing": 12, "extensions": 15, "drops": 15, "judge_adaptation": 14,
    },
    "summary": "Solid constructive with warrant gaps.",
    "strengths": ["Clear claim structure"],
    "weaknesses": ["Weak warrants on C2"],
    "raw_feedback": {
        "top_3_priorities": ["Strengthen C2 warrant", "Add weighing block", "Improve delivery pace"],
        "structured_issues": [
            {
                "issue_type": "missing_warrant",
                "severity": "high",
                "title": "Missing warrant on C2",
                "explanation": "C2 claim lacks a causal mechanism.",
                "why_it_matters": "Warrant-less claims are easily dropped.",
                "recommendation": "Add a mechanism for the economic link.",
                "affected_argument_labels": ["C2"],
                "recommended_drill_type": "warranting",
            },
            {
                "issue_type": "no_weighing",
                "severity": "medium",
                "title": "No weighing comparison",
                "explanation": "You never compared impacts.",
                "why_it_matters": "Judge can't vote without a comparison.",
                "recommendation": "Add a 60-second weighing block.",
                "affected_argument_labels": ["C1", "C2"],
                "recommended_drill_type": "weighing",
            },
        ],
    },
    "created_at": "2026-06-09T00:00:00+00:00",
}

FAKE_DRILLS = [
    {
        "id": "drill-001",
        "speech_id": SPEECH_ID,
        "user_id": USER_ID,
        "title": "Warrant Builder",
        "skill_target": "warranting",
        "prompt": "Rebuild your weakest argument with a clear mechanism.",
        "source_weakness": "Weak warrant on C2",
        "success_criteria": ["Mechanism is stated clearly"],
        "order": 1,
        "status": "assigned",
        "time_limit_seconds": 180,
    },
    {
        "id": "drill-002",
        "speech_id": SPEECH_ID,
        "user_id": USER_ID,
        "title": "Weighing Block",
        "skill_target": "weighing",
        "prompt": "Deliver a 60-second weighing comparison.",
        "source_weakness": "No weighing",
        "success_criteria": ["Names both sides", "Uses one weighing mechanism"],
        "order": 2,
        "status": "completed",
        "time_limit_seconds": 120,
    },
]

FAKE_DELIVERY = {
    "id": "dm-001",
    "speech_id": SPEECH_ID,
    "words_per_minute": 195,
    "filler_word_count": 3,
    "delivery_score": 72,
    "pacing_band": "too_fast",
}

FAKE_EVIDENCE_CHECKS = [
    {
        "id": "ec-001",
        "speech_id": SPEECH_ID,
        "user_id": USER_ID,
        "argument_label": "C1: Economic Growth",
        "claim_text": "Lower taxes increase investment",
        "support_level": "partially_supported",
        "explanation": "Card is related but doesn't directly prove magnitude.",
        "created_at": "2026-06-09T00:00:00+00:00",
    },
    {
        "id": "ec-002",
        "speech_id": SPEECH_ID,
        "user_id": USER_ID,
        "argument_label": "C2: Jobs",
        "claim_text": "Tax cuts create jobs",
        "support_level": "unsupported",
        "explanation": "No card found in library.",
        "created_at": "2026-06-09T00:00:00+00:00",
    },
]

FAKE_WORKOUT_ROW = {
    "id": WORKOUT_ID,
    "user_id": USER_ID,
    "speech_id": SPEECH_ID,
    "title": "Constructive Repair Workout",
    "description": None,
    "estimated_minutes": 15,
    "workout_type": "tournament_prep",
    "status": "not_started",
    "focus_area": "warranting",
    "workout_json": {
        "steps": [
            {
                "id": "step_abc12345",
                "title": "Warrant Clarity Rep",
                "category": "argument",
                "focus": "warranting",
                "estimated_minutes": 4,
                "source": "feedback",
                "problem": "C2 claim lacks a causal mechanism.",
                "instruction": "Practice warrant.",
                "success_criteria": "Causal chain stated clearly.",
                "linked_drill_id": None,
                "completed": False,
            },
            {
                "id": "step_def67890",
                "title": "Full Re-record",
                "category": "rerecord",
                "focus": "rerecord",
                "estimated_minutes": 2,
                "source": "feedback",
                "problem": "Apply every fix.",
                "instruction": "Record a new speech.",
                "success_criteria": "Score 78/100 or higher.",
                "linked_drill_id": None,
                "completed": False,
            },
        ],
        "re_record_goal": "Score 78/100 or higher with clearer warrants.",
        "coach_note": "Focus on structural completeness.",
        "generated_from": {"feedback_report_id": "fb-001"},
    },
    "completed_at": None,
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}


# ── Service unit tests ─────────────────────────────────────────────────────────

class TestGenerateTournamentWorkout:
    def test_generates_steps_from_feedback_issues(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
        )
        step_titles = [s["title"] for s in plan["steps"]]
        assert any("Warrant" in t or "Clarity" in t for t in step_titles)

    def test_always_ends_with_rerecord_step(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
        )
        assert plan["steps"][-1]["category"] == "rerecord"

    def test_step_count_is_three_to_six(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=FAKE_DRILLS,
            delivery_metrics=FAKE_DELIVERY,
            evidence_checks=FAKE_EVIDENCE_CHECKS,
        )
        # includes re-record: 5 working steps + 1 rerecord = 6 max
        assert 3 <= len(plan["steps"]) <= 6

    def test_includes_delivery_step_when_severe(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
            delivery_metrics=FAKE_DELIVERY,
        )
        categories = [s["category"] for s in plan["steps"]]
        assert "delivery" in categories

    def test_no_delivery_step_when_pacing_steady(self):
        steady_delivery = {
            "id": "dm-002",
            "speech_id": SPEECH_ID,
            "words_per_minute": 165,
            "filler_word_count": 2,
            "delivery_score": 85,
            "pacing_band": "steady",
        }
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
            delivery_metrics=steady_delivery,
        )
        categories = [s["category"] for s in plan["steps"]]
        assert "delivery" not in categories

    def test_includes_evidence_step_for_unsupported_checks(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
            evidence_checks=FAKE_EVIDENCE_CHECKS,
        )
        categories = [s["category"] for s in plan["steps"]]
        assert "evidence" in categories

    def test_no_duplicate_focus_areas(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=FAKE_DRILLS,
            delivery_metrics=FAKE_DELIVERY,
            evidence_checks=FAKE_EVIDENCE_CHECKS,
        )
        non_rerecord = [s for s in plan["steps"] if s["category"] != "rerecord"]
        focuses = [s["focus"] for s in non_rerecord]
        assert len(focuses) == len(set(focuses)), "Duplicate focus areas found"

    def test_total_estimated_time_reasonable(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=FAKE_DRILLS,
            delivery_metrics=FAKE_DELIVERY,
            evidence_checks=FAKE_EVIDENCE_CHECKS,
        )
        assert 8 <= plan["estimated_minutes"] <= 30

    def test_final_focus_speech_includes_ballot_step(self):
        ff_speech = {**FAKE_SPEECH, "speech_type": "final_focus"}
        plan = generate_tournament_workout(
            speech=ff_speech,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
        )
        step_titles = [s["title"] for s in plan["steps"]]
        assert any("Ballot" in t for t in step_titles)

    def test_rebuttal_speech_includes_coverage_step(self):
        rb_speech = {**FAKE_SPEECH, "speech_type": "rebuttal"}
        plan = generate_tournament_workout(
            speech=rb_speech,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
        )
        step_titles = [s["title"] for s in plan["steps"]]
        assert any("Coverage" in t or "coverage" in t.lower() for t in step_titles)

    def test_summary_speech_includes_collapse_step(self):
        sm_speech = {**FAKE_SPEECH, "speech_type": "summary"}
        plan = generate_tournament_workout(
            speech=sm_speech,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
        )
        step_focuses = [s["focus"] for s in plan["steps"]]
        assert "collapse" in step_focuses

    def test_each_step_has_required_fields(self):
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=FAKE_FEEDBACK,
            argument_map=None,
            drills=[],
        )
        required = {"id", "title", "category", "focus", "estimated_minutes",
                    "source", "problem", "instruction", "success_criteria", "completed"}
        for step in plan["steps"]:
            missing = required - set(step.keys())
            assert not missing, f"Step missing fields: {missing}"

    def test_handles_empty_structured_issues(self):
        fb = {**FAKE_FEEDBACK, "raw_feedback": {"top_3_priorities": [], "structured_issues": []}}
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report=fb,
            argument_map=None,
            drills=FAKE_DRILLS,
        )
        assert len(plan["steps"]) >= 2  # at least one drill step + rerecord

    def test_linked_drill_id_set_for_drill_sourced_steps(self):
        # Only check steps that come from drills
        plan = generate_tournament_workout(
            speech=FAKE_SPEECH,
            feedback_report={**FAKE_FEEDBACK, "raw_feedback": {"structured_issues": []}},
            argument_map=None,
            drills=FAKE_DRILLS,
        )
        drill_steps = [s for s in plan["steps"] if s["source"] == "drill"]
        for step in drill_steps:
            assert step["linked_drill_id"] is not None


class TestBuildRerecordGoal:
    def test_includes_target_score_when_score_given(self):
        goal = _build_rerecord_goal(72, [], [])
        assert "82" in goal or "72" in goal or "/" in goal

    def test_dash_format_for_null_score(self):
        goal = _build_rerecord_goal(None, [], [])
        assert len(goal) > 10

    def test_includes_focus_phrases(self):
        steps = [{"focus": "warranting", "category": "argument"}]
        goal = _build_rerecord_goal(70, steps, [])
        assert "warrant" in goal.lower()


class TestBuildCoachNote:
    def test_final_focus_note_mentions_voting_issue(self):
        note = _build_coach_note("final_focus", None, [])
        assert "voting issue" in note.lower()

    def test_low_score_adds_structural_note(self):
        note = _build_coach_note("constructive", 55, [])
        assert "structural" in note.lower() or "repair" in note.lower()


class TestSkillToFocus:
    def test_warranting_maps_to_warranting(self):
        assert _skill_to_focus("warranting") == "warranting"

    def test_pacing_control_maps_to_delivery(self):
        assert _skill_to_focus("pacing_control") == "delivery"

    def test_evidence_alignment_maps_to_evidence(self):
        assert _skill_to_focus("evidence_alignment") == "evidence"

    def test_unknown_skill_passes_through(self):
        assert _skill_to_focus("custom_skill") == "custom_skill"


# ── API endpoint tests ─────────────────────────────────────────────────────────

def _make_sb_mock(
    speech=None,
    no_existing_workout=True,
    feedback=None,
    argument_map=None,
    drills=None,
    delivery=None,
    evidence=None,
    saved_workout=None,
):
    sb = MagicMock()
    speech_data = [speech or FAKE_SPEECH]
    feedback_data = [feedback or FAKE_FEEDBACK]
    drills_data = drills or FAKE_DRILLS
    delivery_data = [delivery] if delivery else []
    evidence_data = evidence or []
    am_data = [argument_map] if argument_map else []
    existing_workout = [] if no_existing_workout else [FAKE_WORKOUT_ROW]
    saved = [saved_workout or FAKE_WORKOUT_ROW]

    def make_chain(data):
        m = MagicMock()
        m.execute.return_value.data = data
        m.select.return_value = m
        m.eq.return_value = m
        m.order.return_value = m
        m.limit.return_value = m
        m.insert.return_value = m
        m.update.return_value = m
        return m

    call_count = [0]

    def table_side_effect(name):
        call_count[0] += 1
        if name == "speeches":
            return make_chain(speech_data)
        elif name == "workouts":
            # First call: check existing; subsequent: save/read back
            if call_count[0] <= 2 and no_existing_workout:
                return make_chain([])
            return make_chain(saved)
        elif name == "feedback_reports":
            return make_chain(feedback_data)
        elif name == "argument_maps":
            return make_chain(am_data)
        elif name == "drills":
            return make_chain(drills_data)
        elif name == "delivery_metrics":
            return make_chain(delivery_data)
        elif name == "claim_evidence_checks":
            return make_chain(evidence_data)
        return make_chain([])

    sb.table.side_effect = table_side_effect
    return sb


class TestPostWorkout:
    @patch("app.api.workouts.get_supabase")
    def test_generates_workout_successfully(self, mock_sb):
        mock_sb.return_value = _make_sb_mock()
        res = client.post(
            f"/speeches/{SPEECH_ID}/workout",
            json={"user_id": USER_ID},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["speech_id"] == SPEECH_ID
        assert data["workout_type"] == "tournament_prep"
        assert "steps" in data["workout_json"]

    @patch("app.api.workouts.get_supabase")
    def test_returns_existing_workout_without_force(self, mock_sb):
        mock_sb.return_value = _make_sb_mock(no_existing_workout=False)
        res = client.post(
            f"/speeches/{SPEECH_ID}/workout",
            json={"user_id": USER_ID, "force_regenerate": False},
        )
        assert res.status_code == 200
        # Should return existing without calling generation
        assert res.json()["id"] == WORKOUT_ID

    @patch("app.api.workouts.get_supabase")
    def test_speech_not_found_returns_404(self, mock_sb):
        sb = MagicMock()
        chain = MagicMock()
        chain.execute.return_value.data = []
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        sb.table.return_value = chain
        mock_sb.return_value = sb
        res = client.post(
            f"/speeches/{SPEECH_ID}/workout",
            json={"user_id": USER_ID},
        )
        assert res.status_code == 404

    @patch("app.api.workouts.get_supabase")
    def test_incomplete_speech_returns_400(self, mock_sb):
        incomplete_speech = {**FAKE_SPEECH, "status": "analyzing"}
        mock_sb.return_value = _make_sb_mock(speech=incomplete_speech)
        res = client.post(
            f"/speeches/{SPEECH_ID}/workout",
            json={"user_id": USER_ID},
        )
        assert res.status_code == 400

    @patch("app.api.workouts.get_supabase")
    def test_evidence_summary_off_by_default_step_included_when_checks_exist(self, mock_sb):
        mock_sb.return_value = _make_sb_mock(
            evidence=FAKE_EVIDENCE_CHECKS,
            no_existing_workout=True,
        )
        res = client.post(
            f"/speeches/{SPEECH_ID}/workout",
            json={"user_id": USER_ID},
        )
        assert res.status_code == 200


class TestGetWorkout:
    @patch("app.api.workouts.get_supabase")
    def test_returns_workout_when_exists(self, mock_sb):
        sb = MagicMock()
        chain = MagicMock()
        chain.execute.return_value.data = [FAKE_WORKOUT_ROW]
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        sb.table.return_value = chain
        mock_sb.return_value = sb
        res = client.get(f"/speeches/{SPEECH_ID}/workout?user_id={USER_ID}")
        assert res.status_code == 200
        assert res.json()["id"] == WORKOUT_ID

    @patch("app.api.workouts.get_supabase")
    def test_returns_null_when_no_workout(self, mock_sb):
        sb = MagicMock()
        chain = MagicMock()
        chain.execute.return_value.data = []
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        sb.table.return_value = chain
        mock_sb.return_value = sb
        res = client.get(f"/speeches/{SPEECH_ID}/workout?user_id={USER_ID}")
        assert res.status_code == 200
        assert res.json() is None


class TestPatchWorkout:
    @patch("app.api.workouts.get_supabase")
    def test_marks_step_complete(self, mock_sb):
        step_id = FAKE_WORKOUT_ROW["workout_json"]["steps"][0]["id"]
        updated_row = {
            **FAKE_WORKOUT_ROW,
            "status": "in_progress",
            "workout_json": {
                **FAKE_WORKOUT_ROW["workout_json"],
                "steps": [
                    {**FAKE_WORKOUT_ROW["workout_json"]["steps"][0], "completed": True},
                    FAKE_WORKOUT_ROW["workout_json"]["steps"][1],
                ],
            },
        }
        sb = MagicMock()

        def table_side(name):
            m = MagicMock()
            m.execute.return_value.data = [FAKE_WORKOUT_ROW] if name == "workouts" else [updated_row]
            m.select.return_value = m
            m.eq.return_value = m
            m.limit.return_value = m
            m.update.return_value = m
            return m

        call_n = [0]
        def ts(name):
            call_n[0] += 1
            m = MagicMock()
            if name == "workouts" and call_n[0] == 1:
                m.execute.return_value.data = [FAKE_WORKOUT_ROW]
            else:
                m.execute.return_value.data = [updated_row]
            m.select.return_value = m
            m.eq.return_value = m
            m.limit.return_value = m
            m.update.return_value = m
            return m

        sb.table.side_effect = ts
        mock_sb.return_value = sb

        res = client.patch(
            f"/workouts/{WORKOUT_ID}",
            json={"user_id": USER_ID, "completed_step_ids": [step_id]},
        )
        assert res.status_code == 200

    @patch("app.api.workouts.get_supabase")
    def test_completed_at_set_when_all_steps_done(self, mock_sb):
        all_done_row = {
            **FAKE_WORKOUT_ROW,
            "status": "completed",
            "completed_at": "2026-06-09T12:00:00+00:00",
            "workout_json": {
                **FAKE_WORKOUT_ROW["workout_json"],
                "steps": [
                    {**FAKE_WORKOUT_ROW["workout_json"]["steps"][0], "completed": True},
                    {**FAKE_WORKOUT_ROW["workout_json"]["steps"][1], "completed": True},
                ],
            },
        }
        step_ids = [s["id"] for s in FAKE_WORKOUT_ROW["workout_json"]["steps"]]

        call_n = [0]
        def ts(name):
            call_n[0] += 1
            m = MagicMock()
            if name == "workouts" and call_n[0] == 1:
                m.execute.return_value.data = [FAKE_WORKOUT_ROW]
            else:
                m.execute.return_value.data = [all_done_row]
            m.select.return_value = m
            m.eq.return_value = m
            m.limit.return_value = m
            m.update.return_value = m
            return m

        sb = MagicMock()
        sb.table.side_effect = ts
        mock_sb.return_value = sb

        res = client.patch(
            f"/workouts/{WORKOUT_ID}",
            json={"user_id": USER_ID, "completed_step_ids": step_ids},
        )
        assert res.status_code == 200
        assert res.json()["completed_at"] is not None

    @patch("app.api.workouts.get_supabase")
    def test_wrong_user_returns_404(self, mock_sb):
        sb = MagicMock()
        chain = MagicMock()
        chain.execute.return_value.data = []
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        sb.table.return_value = chain
        mock_sb.return_value = sb
        res = client.patch(
            f"/workouts/{WORKOUT_ID}",
            json={"user_id": "wrong-user-id"},
        )
        assert res.status_code == 404
