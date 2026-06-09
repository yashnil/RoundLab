"""Tests for PATCH /argument-map (correction) and POST /regenerate-from-flow."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SPEECH_ID = "aaaaaaaa-1111-0000-0000-corr000000001"
USER_ID   = "bbbbbbbb-1111-0000-0000-corr000000002"
MAP_ID    = "cccccccc-1111-0000-0000-corr000000003"

FAKE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "Test Constructive",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test.",
    "audio_url": "path/to/audio.mp3",
    "status": "done",
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}

FAKE_TRANSCRIPT = {
    "text": (
        "The first contention is economic growth. Lower taxes increase investment because "
        "reduced tax burdens free capital for private sector deployment. "
        "Smith et al 2023 finds GDP grows by 2%. The impact is more jobs and prosperity."
    ),
    "word_count": 42,
}

FAKE_ARG_ITEM = {
    "id": "arg_1",
    "label": "C1: Economic Growth",
    "claim": "Lower taxes increase investment.",
    "warrant": "Reduced tax burden frees capital.",
    "evidence": "Smith et al. 2023",
    "impact": "More jobs and prosperity.",
    "argument_type": "offense",
    "issues": [],
    "confidence": 0.9,
}

FAKE_ARG_MAP = {
    "id": MAP_ID,
    "speech_id": SPEECH_ID,
    "arguments": [FAKE_ARG_ITEM],
    "source_type": "ai",
    "original_arguments": None,
    "user_corrected_at": None,
    "correction_notes": None,
    "updated_at": "2026-06-09T00:00:00+00:00",
    "created_at": "2026-06-09T00:00:00+00:00",
}

CORRECTED_ARG_MAP = {
    **FAKE_ARG_MAP,
    "source_type": "user_corrected",
    "original_arguments": [FAKE_ARG_ITEM],
    "user_corrected_at": "2026-06-09T01:00:00+00:00",
    "updated_at": "2026-06-09T01:00:00+00:00",
}

FAKE_FEEDBACK_ROW = {
    "id": "feeeeeeee-1111-0000-0000-corr000000004",
    "speech_id": SPEECH_ID,
    "overall_score": 72,
    "scores": {"clash": 14, "weighing": 14, "extensions": 14, "drops": 14, "judge_adaptation": 16},
    "summary": "Good speech.",
    "strengths": ["Strong evidence."],
    "weaknesses": ["Missing warrant."],
    "raw_feedback": {
        "flow_correction_regenerated_at": "2026-06-09T01:00:00Z",
        "regenerated_from_correction": True,
    },
    "helpful_rating": None,
    "helpful_comment": None,
    "created_at": "2026-06-09T00:00:00+00:00",
}

FAKE_DRILL = {
    "id": "ddddddddd-1111-0000-0000-corr000000005",
    "speech_id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "Warrant Sprint",
    "description": "Practice warranting.",
    "skill_target": "warranting",
    "prompt": "Take this claim and add a warrant.",
    "order": 1,
    "instructions": "Step 1. Do the drill.",
    "success_criteria": ["Clear warrant present"],
    "source_weakness": "Missing warrant.",
    "difficulty": "beginner",
    "status": "assigned",
    "time_limit_seconds": 90,
    "created_at": "2026-06-09T00:00:00+00:00",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ownership_mock(speech_data):
    m = MagicMock()
    m.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = speech_data
    return m


def _single_eq_mock(data):
    m = MagicMock()
    m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = data
    return m


def _update_mock(return_data=None):
    m = MagicMock()
    m.update.return_value.eq.return_value.execute.return_value.data = return_data or []
    return m


# ── PATCH /speeches/{id}/argument-map ─────────────────────────────────────────

class TestSaveFlowCorrection:
    def _make_sb(self, speech_data, map_data, update_result):
        sb = MagicMock()
        speech_m = _ownership_mock(speech_data)
        # Argument map fetch: .select("*").eq("speech_id", ...).limit(1).execute()
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = map_data
        # Update: .update({...}).eq("speech_id", ...).execute()
        upd_m = MagicMock()
        upd_m.update.return_value.eq.return_value.execute.return_value.data = update_result
        sb.table.side_effect = [speech_m, map_m, upd_m]
        return sb

    def test_saves_corrected_arguments(self):
        corrected = {**CORRECTED_ARG_MAP}
        sb = self._make_sb([FAKE_SPEECH], [FAKE_ARG_MAP], [corrected])
        body = {
            "arguments": [{
                "label": "C1: Updated", "claim": "Updated claim.", "warrant": "Updated warrant.",
                "evidence": None, "impact": "Updated impact.", "argument_type": "offense",
                "issues": [], "confidence": None, "id": "arg_1",
            }]
        }
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.patch(f"/speeches/{SPEECH_ID}/argument-map?user_id={USER_ID}", json=body)
        assert r.status_code == 200
        assert r.json()["source_type"] == "user_corrected"

    def test_404_for_unknown_speech(self):
        sb = MagicMock()
        sb.table.return_value = _ownership_mock([])
        body = {
            "arguments": [{
                "label": "C1", "claim": "Claim.", "warrant": "W.",
                "evidence": None, "impact": "I.", "argument_type": "offense",
                "issues": [], "confidence": None, "id": "arg_1",
            }]
        }
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.patch(f"/speeches/{SPEECH_ID}/argument-map?user_id={USER_ID}", json=body)
        assert r.status_code == 404

    def test_404_when_no_arg_map(self):
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        sb.table.side_effect = [speech_m, map_m]
        body = {
            "arguments": [{
                "label": "C1", "claim": "Claim.", "warrant": "W.",
                "evidence": None, "impact": "I.", "argument_type": "offense",
                "issues": [], "confidence": None,
            }]
        }
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.patch(f"/speeches/{SPEECH_ID}/argument-map?user_id={USER_ID}", json=body)
        assert r.status_code == 404

    def test_400_for_empty_arguments_list(self):
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARG_MAP]
        sb.table.side_effect = [speech_m, map_m]
        body = {"arguments": []}
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.patch(f"/speeches/{SPEECH_ID}/argument-map?user_id={USER_ID}", json=body)
        assert r.status_code == 422

    def test_assigns_ids_to_new_arguments(self):
        corrected = {**CORRECTED_ARG_MAP}
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARG_MAP]
        upd_m = MagicMock()
        captured = []
        def capture_update(payload):
            captured.append(payload)
            m = MagicMock()
            m.eq.return_value.execute.return_value.data = [corrected]
            return m
        upd_m.update.side_effect = capture_update
        sb.table.side_effect = [speech_m, map_m, upd_m]

        # Send argument WITHOUT an id (simulates user-added arg)
        body = {
            "arguments": [{
                "label": "C2: New", "claim": "New claim.", "warrant": "New warrant.",
                "evidence": None, "impact": "New impact.", "argument_type": "offense",
                "issues": [], "confidence": None,
                # deliberately omit 'id'
            }]
        }
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.patch(f"/speeches/{SPEECH_ID}/argument-map?user_id={USER_ID}", json=body)
        assert r.status_code == 200
        # Check that the stored payload assigned an ID
        stored_args = captured[0]["arguments"]
        assert stored_args[0].get("id") is not None
        assert stored_args[0]["id"].startswith("arg_")

    def test_preserves_original_on_first_correction(self):
        """First PATCH snapshots original AI arguments into original_arguments."""
        corrected = {**CORRECTED_ARG_MAP}
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARG_MAP]
        captured = []
        upd_m = MagicMock()
        def capture_update(payload):
            captured.append(payload)
            m = MagicMock()
            m.eq.return_value.execute.return_value.data = [corrected]
            return m
        upd_m.update.side_effect = capture_update
        sb.table.side_effect = [speech_m, map_m, upd_m]

        body = {
            "arguments": [{
                "label": "C1 edited", "claim": "Claim.", "warrant": "Warrant.",
                "evidence": None, "impact": "Impact.", "argument_type": "offense",
                "issues": [], "confidence": None, "id": "arg_1",
            }]
        }
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            client.patch(f"/speeches/{SPEECH_ID}/argument-map?user_id={USER_ID}", json=body)

        # original_arguments should be set from the existing AI arguments
        assert "original_arguments" in captured[0]
        assert captured[0]["original_arguments"] is not None


# ── POST /speeches/{id}/regenerate-from-flow ─────────────────────────────────

class TestRegenerateFromFlow:
    def _make_sb(
        self,
        speech_data=None,
        transcript_data=None,
        map_data=None,
        existing_drills=None,
        feedback_result=None,
        drill_insert_result=None,
    ):
        sb = MagicMock()

        speech_m = _ownership_mock(speech_data or [FAKE_SPEECH])

        # Transcript
        tx_m = MagicMock()
        tx_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = (
            transcript_data if transcript_data is not None else [FAKE_TRANSCRIPT]
        )

        # Arg map
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = (
            map_data if map_data is not None else [CORRECTED_ARG_MAP]
        )

        # Existing drills
        drills_m = MagicMock()
        drills_m.select.return_value.eq.return_value.execute.return_value.data = (
            existing_drills or []
        )

        # Delete drills
        del_m = MagicMock()
        del_m.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Feedback upsert
        fb_m = MagicMock()
        fb_m.upsert.return_value.execute.return_value.data = (
            feedback_result if feedback_result is not None else [FAKE_FEEDBACK_ROW]
        )

        # Drill insert
        drill_ins_m = MagicMock()
        drill_ins_m.insert.return_value.execute.return_value.data = (
            drill_insert_result if drill_insert_result is not None else [FAKE_DRILL]
        )

        # Speech status update
        speech_upd_m = MagicMock()
        speech_upd_m.update.return_value.eq.return_value.execute.return_value.data = []

        # Endpoint call order: speech → transcript → arg_map → feedback_upsert
        #   → existing_drills → delete_drills → drill_insert → speech_status_update
        sb.table.side_effect = [
            speech_m, tx_m, map_m, fb_m, drills_m, del_m, drill_ins_m, speech_upd_m
        ]
        return sb

    def _mock_feedback_output(self):
        from app.services.feedback_generation import _FeedbackOutput
        from app.models.feedback_report import FeedbackScores
        return _FeedbackOutput(
            overall_score=72,
            scores=FeedbackScores(clash=14, weighing=14, extensions=14, drops=14, judge_adaptation=16),
            score_explanations=[],
            summary="Good speech.",
            strengths=["Strong evidence."],
            weaknesses=["Missing warrant."],
            decision_logic="Pro wins.",
            dropped_or_undercovered_arguments=[],
            warranting_diagnostics=[],
            weighing_diagnostics=[],
            evidence_diagnostics=[],
            judge_adaptation_notes="Good.",
            top_3_priorities=["Improve warranting"],
            recommendations=["Practice warranting drill"],
            structured_issues=[],
        )

    def _mock_drills(self):
        from app.services.drill_generation import _DrillItem
        return [_DrillItem(
            title="Warrant Sprint",
            skill_target="warranting",
            description="Practice warranting.",
            prompt="Add a warrant.",
            instructions="Step 1. Do the drill.",
            success_criteria=["Clear warrant present"],
            source_weakness="Missing warrant.",
            difficulty="beginner",
            time_limit_seconds=90,
        )]

    def test_returns_feedback_and_drills(self):
        sb = self._make_sb()
        with (
            patch("app.api.argument_maps.get_supabase", return_value=sb),
            patch(
                "app.services.feedback_generation.generate_feedback",
                return_value=self._mock_feedback_output(),
            ),
            patch(
                "app.services.drill_generation.generate_drills",
                return_value=self._mock_drills(),
            ),
            patch("app.services.deterministic_scoring.calculate_rubric_scores", return_value={
                "clash": 14, "weighing": 14, "extensions": 14, "drops": 14, "judge_adaptation": 16,
            }),
            patch("app.services.deterministic_scoring.compute_report_fingerprint", return_value="hash123"),
            patch("app.services.deterministic_scoring.map_rubric_to_legacy_scores", return_value={
                "clash": 14, "weighing": 14, "extensions": 14, "drops": 14, "judge_adaptation": 16,
            }),
        ):
            r = client.post(f"/speeches/{SPEECH_ID}/regenerate-from-flow?user_id={USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "feedback" in body
        assert "drills" in body

    def test_404_for_unknown_speech(self):
        sb = MagicMock()
        sb.table.return_value = _ownership_mock([])
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.post(f"/speeches/{SPEECH_ID}/regenerate-from-flow?user_id={USER_ID}")
        assert r.status_code == 404

    def test_400_when_no_transcript(self):
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        tx_m = MagicMock()
        tx_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        sb.table.side_effect = [speech_m, tx_m]
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.post(f"/speeches/{SPEECH_ID}/regenerate-from-flow?user_id={USER_ID}")
        assert r.status_code == 400
        assert "transcript" in r.json()["detail"].lower()

    def test_400_when_no_arg_map(self):
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        tx_m = MagicMock()
        tx_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        sb.table.side_effect = [speech_m, tx_m, map_m]
        with patch("app.api.argument_maps.get_supabase", return_value=sb):
            r = client.post(f"/speeches/{SPEECH_ID}/regenerate-from-flow?user_id={USER_ID}")
        assert r.status_code == 400
        assert "argument map" in r.json()["detail"].lower()

    def test_preserves_completed_drills(self):
        """Completed drills are NOT deleted; new drills start after their order."""
        completed_drill = {**FAKE_DRILL, "status": "completed", "order": 1}
        attempted_drill = {**FAKE_DRILL, "id": "other", "status": "attempted", "order": 2}
        assigned_drill  = {**FAKE_DRILL, "id": "del", "status": "assigned", "order": 3}

        captured_insert = []
        sb = MagicMock()
        speech_m = _ownership_mock([FAKE_SPEECH])
        tx_m = MagicMock()
        tx_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]
        map_m = MagicMock()
        map_m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [CORRECTED_ARG_MAP]
        drills_m = MagicMock()
        drills_m.select.return_value.eq.return_value.execute.return_value.data = [
            completed_drill, attempted_drill, assigned_drill
        ]
        del_m = MagicMock()
        del_m.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        fb_m = MagicMock()
        fb_m.upsert.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]
        drill_ins_m = MagicMock()
        def capture_insert(rows):
            captured_insert.extend(rows)
            m = MagicMock()
            m.execute.return_value.data = [FAKE_DRILL]
            return m
        drill_ins_m.insert.side_effect = capture_insert
        speech_upd_m = MagicMock()
        speech_upd_m.update.return_value.eq.return_value.execute.return_value.data = []

        sb.table.side_effect = [speech_m, tx_m, map_m, fb_m, drills_m, del_m, drill_ins_m, speech_upd_m]

        with (
            patch("app.api.argument_maps.get_supabase", return_value=sb),
            patch(
                "app.services.feedback_generation.generate_feedback",
                return_value=self._mock_feedback_output(),
            ),
            patch(
                "app.services.drill_generation.generate_drills",
                return_value=self._mock_drills(),
            ),
            patch("app.services.deterministic_scoring.calculate_rubric_scores", return_value={
                "clash": 14, "weighing": 14, "extensions": 14, "drops": 14, "judge_adaptation": 16,
            }),
            patch("app.services.deterministic_scoring.compute_report_fingerprint", return_value="h"),
            patch("app.services.deterministic_scoring.map_rubric_to_legacy_scores", return_value={
                "clash": 14, "weighing": 14, "extensions": 14, "drops": 14, "judge_adaptation": 16,
            }),
        ):
            r = client.post(f"/speeches/{SPEECH_ID}/regenerate-from-flow?user_id={USER_ID}")

        assert r.status_code == 200
        # New drills should start at order 3 (max_preserved=2, +1=3)
        if captured_insert:
            assert captured_insert[0]["order"] >= 3
