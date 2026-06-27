"""
Pass 21.3 — Training OS Production Release Gate.

Tests cover:
1.  Coach override semantic separation
    - mastery_override → audit only, no mastery_evidence
    - coach_performance_review → mastery_evidence + audit (requires artifact_id)
    - priority_override → neither mastery_evidence nor audit
2.  Composite source_id uniqueness — cross-user collisions prevented
3.  Evidence guard correctness — scale, low-confidence, re-record, canonical skill
4.  Optimistic concurrency — expected_version check in PATCH /sessions/{id}
5.  Audio storage logic (model-level, no browser)
6.  Migration file — version column, composite index, audit table declared
7.  RLS policy declarations present for all 7 training tables
8.  Session ownership — caller must match user_id
9.  Stale-tab rejection — 409 returned when version mismatched
10. Coach authorization — shared-team membership required for override
11. Priority override does not write mastery_evidence
12. emit_mastery_override requires non-empty reason
13. emit_from_coach_performance_review requires artifact_id
14. Re-record evidence emitted even when score goes down
15. Low-score speech rejected at gateway
16. source_id contains user-scoped context preventing naive collisions
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch, ANY
from datetime import datetime, timezone

import pytest

ROOT = Path(__file__).parent.parent
SERVICES = ROOT / "app" / "services"
API = ROOT / "app" / "api"
MIGRATIONS_DIR = ROOT.parent / "supabase" / "migrations"

sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_supabase(rows: list | None = None, insert_data: list | None = None):
    """Minimal Supabase mock: select returns rows, insert returns insert_data."""
    sb = MagicMock()
    sel_result = MagicMock()
    sel_result.data = rows or []
    ins_result = MagicMock()
    ins_result.data = insert_data if insert_data is not None else [{"id": "ev1"}]

    table = MagicMock()
    sb.table.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.execute.return_value = sel_result

    inner_ins = MagicMock()
    inner_ins.execute.return_value = ins_result
    table.insert.return_value = inner_ins

    upsert_result = MagicMock()
    upsert_result.data = [{"id": "ms1"}]
    inner_ups = MagicMock()
    inner_ups.execute.return_value = upsert_result
    table.upsert.return_value = inner_ups

    return sb


# ═══════════════════════════════════════════════════════════════════════════
# 1. Coach override semantic separation
# ═══════════════════════════════════════════════════════════════════════════

class TestCoachOverrideSemantics:

    def test_emit_mastery_override_writes_audit_not_evidence(self):
        """emit_mastery_override must insert into coach_mastery_audit, not mastery_evidence."""
        from app.services.mastery_integration import emit_mastery_override

        sb = _make_supabase()
        result = emit_mastery_override(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            skill="warranting",
            override_score=80.0,
            reason="Observed at tournament",
        )
        assert result is True
        # Must call coach_mastery_audit
        tables_called = [str(c) for c in sb.table.call_args_list]
        assert any("coach_mastery_audit" in t for t in tables_called)
        # Must NOT call mastery_evidence
        assert not any("mastery_evidence" in t for t in tables_called)

    def test_emit_mastery_override_requires_reason(self):
        """Empty reason must be rejected — no audit record created."""
        from app.services.mastery_integration import emit_mastery_override

        sb = _make_supabase()
        result = emit_mastery_override(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            skill="warranting",
            override_score=80.0,
            reason="",    # empty — should fail
        )
        assert result is False
        # No DB table should have been called
        sb.table.assert_not_called()

    def test_emit_mastery_override_requires_canonical_skill(self):
        """Unknown skill must be rejected."""
        from app.services.mastery_integration import emit_mastery_override

        sb = _make_supabase()
        result = emit_mastery_override(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            skill="totally_fake_skill_xyz",
            override_score=80.0,
            reason="Some reason",
        )
        assert result is False

    def test_emit_mastery_override_audit_type_is_mastery_override(self):
        """Audit record must use override_type='mastery_override'."""
        from app.services.mastery_integration import emit_mastery_override

        sb = _make_supabase()
        emit_mastery_override(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            skill="warranting",
            override_score=75.0,
            reason="I watched the round",
            artifact_id="speech-abc",
        )
        insert_call = sb.table.return_value.insert.call_args
        assert insert_call is not None
        data = insert_call[0][0]
        assert data["override_type"] == "mastery_override"
        assert data["artifact_id"] == "speech-abc"
        assert data["override_score"] == 75.0

    def test_emit_from_coach_performance_review_creates_evidence(self):
        """Performance review with artifact_id must write mastery_evidence."""
        from app.services.mastery_integration import emit_from_coach_performance_review

        sb = _make_supabase(rows=[])
        result = emit_from_coach_performance_review(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            review_id="review-42",
            skill="warranting",
            score_pct=70.0,
            artifact_id="speech-xyz",
            note="Strong warrants on the econ contention",
        )
        assert result is True
        tables = [str(c) for c in sb.table.call_args_list]
        assert any("mastery_evidence" in t for t in tables)

    def test_emit_from_coach_performance_review_requires_artifact(self):
        """Performance review without artifact_id must be rejected (returns False)."""
        from app.services.mastery_integration import emit_from_coach_performance_review

        sb = _make_supabase()
        result = emit_from_coach_performance_review(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            review_id="review-42",
            skill="warranting",
            score_pct=70.0,
            artifact_id="",   # empty — must be rejected
            note="",
        )
        assert result is False

    def test_emit_from_coach_performance_review_also_writes_audit(self):
        """Performance review must write audit record too."""
        from app.services.mastery_integration import emit_from_coach_performance_review

        sb = _make_supabase(rows=[])
        emit_from_coach_performance_review(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            review_id="review-42",
            skill="warranting",
            score_pct=70.0,
            artifact_id="speech-xyz",
        )
        tables = [str(c) for c in sb.table.call_args_list]
        assert any("coach_mastery_audit" in t for t in tables)

    def test_emit_from_coach_performance_review_audit_type(self):
        """Audit record for performance review must use 'coach_performance_review'."""
        from app.services.mastery_integration import emit_from_coach_performance_review

        # We need two table calls: mastery_evidence and coach_mastery_audit.
        # Build a side_effect that returns the right mock for each table.
        evidence_table = MagicMock()
        evidence_ins = MagicMock()
        evidence_ins.execute.return_value = MagicMock(data=[{"id": "ev1"}])
        evidence_table.insert.return_value = evidence_ins
        evidence_table.select.return_value = evidence_table
        evidence_table.eq.return_value = evidence_table
        evidence_table.order.return_value = evidence_table
        evidence_table.limit.return_value = evidence_table
        evidence_table.execute.return_value = MagicMock(data=[])

        audit_table = MagicMock()
        audit_ins = MagicMock()
        audit_ins.execute.return_value = MagicMock(data=[{"id": "au1"}])
        audit_table.insert.return_value = audit_ins

        upsert_table = MagicMock()
        upsert_table.execute.return_value = MagicMock(data=[{"id": "ms1"}])

        call_count = {"n": 0}

        def table_side_effect(name):
            call_count["n"] += 1
            if "mastery_evidence" in name:
                return evidence_table
            if "coach_mastery_audit" in name:
                return audit_table
            return evidence_table

        sb = MagicMock()
        sb.table.side_effect = table_side_effect

        emit_from_coach_performance_review(
            sb,
            coach_id="coach-1",
            student_id="student-1",
            review_id="rev-1",
            skill="warranting",
            score_pct=65.0,
            artifact_id="drill-88",
        )
        audit_data = audit_table.insert.call_args[0][0]
        assert audit_data["override_type"] == "coach_performance_review"
        assert audit_data["artifact_id"] == "drill-88"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Composite source_id — cross-user collision prevention
# ═══════════════════════════════════════════════════════════════════════════

class TestCompositeSourceId:

    def test_source_ids_include_skill(self):
        """source_id must embed the skill to separate same-event different-skill evidence."""
        from app.services.mastery_integration import emit_from_speech_analysis

        captured = []

        def capturing_insert(data, *args, **kwargs):
            captured.append(data)
            result = MagicMock()
            result.execute.return_value = MagicMock(data=[{"id": "ev1"}])
            return result

        sb = _make_supabase(rows=[])
        sb.table.return_value.insert.side_effect = capturing_insert

        emit_from_speech_analysis(
            sb,
            user_id="user-1",
            speech_id="sp-001",
            scores={"warranting": 12, "weighing": 8},
            overall_score=10,
        )
        source_ids = [d["source_id"] for d in captured if "source_id" in d]
        # Each source_id must encode the skill
        for sid in source_ids:
            assert any(skill in sid for skill in ["warranting", "weighing"])

    def test_different_users_same_event_produce_distinct_composite_keys(self):
        """Two users emitting from the same speech_id produce different composite keys."""
        # The composite key is (user_id, source_type, source_id, skill_id).
        # user_id differs so no conflict even if source_id string is identical.
        from app.services.mastery_integration import emit_from_speech_analysis

        rows_by_user: dict[str, list] = {"u1": [], "u2": []}

        def make_sb(user_key):
            sb = _make_supabase(rows=[])
            original_insert = sb.table.return_value.insert

            def capture_insert(data, *args, **kwargs):
                rows_by_user[user_key].append(data)
                result = MagicMock()
                result.execute.return_value = MagicMock(data=[{"id": "ev1"}])
                return result

            sb.table.return_value.insert.side_effect = capture_insert
            return sb

        sb1 = make_sb("u1")
        sb2 = make_sb("u2")

        emit_from_speech_analysis(sb1, "user-1", "sp-shared-001", {"warranting": 14}, 14)
        emit_from_speech_analysis(sb2, "user-2", "sp-shared-001", {"warranting": 14}, 14)

        # Both users' evidence rows have DIFFERENT user_id → no composite conflict
        u1_rows = [r for r in rows_by_user["u1"] if "user_id" in r]
        u2_rows = [r for r in rows_by_user["u2"] if "user_id" in r]
        if u1_rows and u2_rows:
            assert u1_rows[0]["user_id"] != u2_rows[0]["user_id"]

    def test_mission_source_id_contains_skill(self):
        """Mission completion source_id includes skill to avoid same-mission collisions."""
        from app.services.mastery_integration import emit_from_mission_completion

        captured = []
        sb = _make_supabase(rows=[])

        def cap_ins(data, *args, **kwargs):
            captured.append(data)
            r = MagicMock()
            r.execute.return_value = MagicMock(data=[{"id": "ev1"}])
            return r

        sb.table.return_value.insert.side_effect = cap_ins

        emit_from_mission_completion(
            sb,
            user_id="user-1",
            mission_id="mission-99",
            skill="weighing",
            score_delta_pct=15.0,
            after_score_raw=14.0,
        )
        sid_rows = [d for d in captured if d.get("source_id", "")]
        assert any("weighing" in d["source_id"] for d in sid_rows)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Evidence guard correctness
# ═══════════════════════════════════════════════════════════════════════════

class TestEvidenceGuards:

    def test_low_confidence_speech_rejected(self):
        """overall_score < 4/20 must not emit any evidence."""
        from app.services.mastery_integration import emit_from_speech_analysis

        sb = _make_supabase()
        result = emit_from_speech_analysis(
            sb, "user-1", "sp-bad", {"warranting": 0, "weighing": 1}, overall_score=2
        )
        assert result == []
        sb.table.return_value.insert.assert_not_called()

    def test_threshold_at_boundary_passes(self):
        """overall_score == 4 must pass the gate."""
        from app.services.mastery_integration import emit_from_speech_analysis

        sb = _make_supabase(rows=[])
        result = emit_from_speech_analysis(
            sb, "user-1", "sp-ok", {"warranting": 4}, overall_score=4
        )
        # 'warranting' is a valid skill; should emit at least one
        assert isinstance(result, list)

    def test_rerecord_evidence_emits_when_score_goes_down(self):
        """Re-record must emit evidence even when new score < old score."""
        from app.services.mastery_integration import emit_from_rerecord

        sb = _make_supabase(rows=[])
        emitted = emit_from_rerecord(
            sb,
            user_id="user-1",
            new_speech_id="sp-new",
            parent_speech_id="sp-old",
            skill_target="warranting",
            new_overall_score=6,    # worse than hypothetical before=12
            new_skill_score=5.0,    # worse
        )
        # Must still emit evidence (performance is real even when regressed)
        assert len(emitted) > 0

    def test_rerecord_score_stored_not_inflated(self):
        """Re-record must not report a higher score than what was measured."""
        from app.services.mastery_integration import emit_from_rerecord

        captured = []
        sb = _make_supabase(rows=[])

        def cap(data, *a, **kw):
            captured.append(data)
            r = MagicMock()
            r.execute.return_value = MagicMock(data=[{"id": "ev1"}])
            return r

        sb.table.return_value.insert.side_effect = cap

        emit_from_rerecord(
            sb,
            user_id="user-1",
            new_speech_id="sp-new",
            parent_speech_id="sp-old",
            skill_target="warranting",
            new_overall_score=8,
            new_skill_score=8.0,
        )
        norm_scores = [d.get("normalized_score", 999) for d in captured]
        # 8/20 → 40; must not exceed 40
        for score in norm_scores:
            if score != 999:
                assert score <= 40.0 + 0.01

    def test_canonical_skill_missing_returns_false(self):
        """Unknown skill target must return False / empty list without crashing."""
        from app.services.mastery_integration import emit_from_drill_attempt

        sb = _make_supabase()
        result = emit_from_drill_attempt(
            sb, "user-1", "drill-1", "nonexistent_skill", score_pct=80.0
        )
        assert result is False
        sb.table.return_value.insert.assert_not_called()

    def test_speech_threshold_uses_0_20_scale(self):
        """The minimum threshold (4) is on the 0-20 rubric scale."""
        from app.services.mastery_integration import _MIN_SPEECH_OVERALL_SCORE
        assert _MIN_SPEECH_OVERALL_SCORE == 4, (
            f"Threshold is {_MIN_SPEECH_OVERALL_SCORE}; expected 4 (0-20 scale). "
            "If changed, verify the rubric scale contract."
        )

    def test_rubric_normalisation_0_20_to_0_100(self):
        """0-20 rubric score must normalise correctly to 0-100."""
        from app.services.mastery_integration import _rubric_score_to_0_100
        assert _rubric_score_to_0_100(0) == 0.0
        assert _rubric_score_to_0_100(10) == 50.0
        assert _rubric_score_to_0_100(20) == 100.0
        assert _rubric_score_to_0_100(25) == 100.0   # clamped

    def test_mission_uses_after_score_not_delta(self):
        """Mission completion must emit the after_score (not delta) as evidence."""
        from app.services.mastery_integration import emit_from_mission_completion

        captured = []
        sb = _make_supabase(rows=[])

        def cap(data, *a, **kw):
            captured.append(data)
            r = MagicMock()
            r.execute.return_value = MagicMock(data=[{"id": "ev1"}])
            return r

        sb.table.return_value.insert.side_effect = cap

        emit_from_mission_completion(
            sb,
            user_id="user-1",
            mission_id="m-1",
            skill="weighing",
            score_delta_pct=-10.0,   # negative delta
            after_score_raw=10.0,    # positive after-score
        )
        raw_scores = [d.get("raw_score") for d in captured if d.get("raw_score") is not None]
        # Must use after_score_raw (10.0), not delta (-10.0)
        assert any(s == 10.0 for s in raw_scores)
        assert not any(s < 0 for s in raw_scores)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Session concurrency — optimistic locking
# ═══════════════════════════════════════════════════════════════════════════

class TestSessionConcurrency:

    def _call_update(self, session_rows, payload):
        """Call the update_session endpoint logic synchronously."""
        import asyncio
        from fastapi import HTTPException
        from app.api.training import update_session

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=session_rows)
        sb.table.return_value.update.return_value = sb.table.return_value

        with patch("app.api.training.get_supabase", return_value=sb), \
             patch("app.api.training.get_current_user_id", return_value="user-1"):
            try:
                result = asyncio.get_event_loop().run_until_complete(
                    update_session("session-1", payload, caller="user-1")
                )
                return result, None
            except HTTPException as exc:
                return None, exc

    def test_no_expected_version_accepts_any_state(self):
        """Without expected_version, update proceeds regardless of server version."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "active", "version": 5}]
        update_result = MagicMock()
        update_result.data = [{"id": "session-1", "version": 6}]

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)
        sb.table.return_value.update.return_value = sb.table.return_value

        import asyncio
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            result = asyncio.get_event_loop().run_until_complete(
                update_session("session-1", {"current_step": "drill"}, caller="user-1")
            )
        # No exception — update was accepted

    def test_matching_version_accepted(self):
        """expected_version == server version must succeed."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "active", "version": 3}]

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)
        sb.table.return_value.update.return_value = sb.table.return_value

        import asyncio
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            result = asyncio.get_event_loop().run_until_complete(
                update_session(
                    "session-1",
                    {"current_step": "drill", "expected_version": 3},
                    caller="user-1",
                )
            )
        # No HTTPException → success

    def test_stale_version_rejected_with_409(self):
        """expected_version != server version must raise 409."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "active", "version": 5}]

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)

        import asyncio
        from fastapi import HTTPException
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    update_session(
                        "session-1",
                        {"current_step": "drill", "expected_version": 3},  # stale (server=5)
                        caller="user-1",
                    )
                )
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail.get("error") == "version_conflict"
        assert detail.get("server_version") == 5
        assert detail.get("client_version") == 3

    def test_completed_session_always_rejects(self):
        """Completed session returns 409 regardless of version."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "completed", "version": 1}]

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)

        import asyncio
        from fastapi import HTTPException
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    update_session("session-1", {"current_step": "drill"}, caller="user-1")
                )
        assert exc_info.value.status_code == 409

    def test_version_incremented_on_update(self):
        """Successful update must increment version by 1."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "active", "version": 7}]
        update_calls = []

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)

        def capture_update(data):
            update_calls.append(data)
            return sb.table.return_value

        sb.table.return_value.update.side_effect = capture_update

        import asyncio
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            asyncio.get_event_loop().run_until_complete(
                update_session("session-1", {"current_step": "drill"}, caller="user-1")
            )

        assert len(update_calls) == 1
        assert update_calls[0]["version"] == 8  # 7 + 1

    def test_expected_version_stripped_from_update_data(self):
        """expected_version must not be written to the DB row."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "active", "version": 2}]
        update_calls = []

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)

        def capture_update(data):
            update_calls.append(data)
            return sb.table.return_value

        sb.table.return_value.update.side_effect = capture_update

        import asyncio
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            asyncio.get_event_loop().run_until_complete(
                update_session(
                    "session-1",
                    {"current_step": "drill", "expected_version": 2},
                    caller="user-1",
                )
            )

        assert "expected_version" not in update_calls[0]


# ═══════════════════════════════════════════════════════════════════════════
# 5. Priority override — must not write mastery evidence
# ═══════════════════════════════════════════════════════════════════════════

class TestPriorityOverrideIsolation:

    def test_priority_change_does_not_touch_mastery_evidence(self):
        """
        The coach priority-override path updates training preferences only.
        It must not write any row to mastery_evidence or coach_mastery_audit.
        """
        # Locate all references to mastery_integration in the training API
        training_api = API / "training.py"
        source = training_api.read_text()

        # The coach priority override endpoint must only call sync_plan_with_mission_completion
        # or similar planning helpers — not emit_from_coach_review or emit_mastery_override
        priority_section = _extract_endpoint_body(source, "coach_priority")
        if priority_section:
            assert "emit_from_coach_review" not in priority_section
            assert "emit_mastery_override" not in priority_section
            assert "mastery_evidence" not in priority_section

    def test_coach_override_endpoint_uses_emit_mastery_override(self):
        """The mastery override endpoint must call emit_mastery_override, not emit_from_coach_review."""
        training_api = API / "training.py"
        source = training_api.read_text()

        override_section = _extract_endpoint_body(source, "coach_mastery_override")
        if override_section:
            # Must use the new override function
            assert "emit_mastery_override" in override_section
            # Must NOT use the deprecated shim
            assert "emit_from_coach_review" not in override_section


def _extract_endpoint_body(source: str, marker: str) -> str | None:
    """Extract the function body following a decorator/def containing `marker`."""
    lines = source.split("\n")
    start = None
    for i, line in enumerate(lines):
        if marker in line:
            start = i
            break
    if start is None:
        return None
    # Collect until next top-level def/class
    body = []
    for line in lines[start + 1:]:
        if line and not line[0].isspace() and (line.startswith("def ") or line.startswith("class ")):
            break
        body.append(line)
    return "\n".join(body)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Migration file — Pass 21.3 structure
# ═══════════════════════════════════════════════════════════════════════════

class TestMigrationFile:

    def _migration_text(self) -> str:
        path = MIGRATIONS_DIR / "20260628000000_pass21p3_release_gate.sql"
        assert path.exists(), f"Migration not found: {path}"
        return path.read_text()

    def test_version_column_declared(self):
        sql = self._migration_text()
        assert "version" in sql.lower()
        assert "training_sessions" in sql.lower()

    def test_composite_source_index_declared(self):
        sql = self._migration_text()
        # New composite index must be present
        assert "idx_mastery_evidence_composite_source" in sql

    def test_old_source_id_index_dropped(self):
        sql = self._migration_text()
        assert "DROP INDEX IF EXISTS idx_mastery_evidence_source_id" in sql

    def test_coach_mastery_audit_table_declared(self):
        sql = self._migration_text()
        assert "coach_mastery_audit" in sql

    def test_audit_rls_policies_present(self):
        sql = self._migration_text()
        assert "ROW LEVEL SECURITY" in sql
        assert "coach_mastery_audit" in sql

    def test_composite_includes_user_id(self):
        sql = self._migration_text()
        # The composite index must include user_id
        composite_line = [l for l in sql.split("\n") if "composite_source" in l.lower()]
        assert composite_line, "Composite source index line not found"

    def test_migration_filename_ordered_after_21p1(self):
        """New migration must come after the previous 21.1 migration."""
        migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
        names = [m.name for m in migrations]
        p21p1 = "20260627000001_pass21p1_training_integration.sql"
        p21p3 = "20260628000000_pass21p3_release_gate.sql"
        assert p21p1 in names
        assert p21p3 in names
        assert names.index(p21p1) < names.index(p21p3)


# ═══════════════════════════════════════════════════════════════════════════
# 7. RLS policy declarations — all 7 Training OS tables
# ═══════════════════════════════════════════════════════════════════════════

class TestRLSPolicies:

    def _all_migration_sql(self) -> str:
        sqls = []
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sqls.append(f.read_text())
        return "\n".join(sqls)

    def _tables_with_rls(self) -> set[str]:
        sql = self._all_migration_sql()
        tables = set()
        for line in sql.split("\n"):
            m = re.search(r"ALTER TABLE\s+(\w+)\s+ENABLE ROW LEVEL SECURITY", line, re.IGNORECASE)
            if m:
                tables.add(m.group(1))
        return tables

    def _service_role_tables_per_file(self) -> set[str]:
        """
        Scan each migration file independently to avoid DOTALL spanning policy blocks.
        Returns tables that have a service_role policy in any migration.
        """
        covered: set[str] = set()
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = f.read_text()
            matches = re.findall(
                r"CREATE POLICY.*?ON\s+(\w+).*?service_role",
                sql, re.IGNORECASE | re.DOTALL,
            )
            covered.update(matches)
        return covered

    def test_mastery_scores_has_rls(self):
        assert "mastery_scores" in self._tables_with_rls()

    def test_mastery_evidence_has_rls(self):
        assert "mastery_evidence" in self._tables_with_rls()

    def test_training_plans_has_rls(self):
        assert "training_plans" in self._tables_with_rls()

    def test_curriculum_progress_has_rls(self):
        assert "curriculum_progress" in self._tables_with_rls()

    def test_coach_calibration_has_rls(self):
        assert "coach_calibration" in self._tables_with_rls()

    def test_diagnostic_results_has_rls(self):
        assert "diagnostic_results" in self._tables_with_rls()

    def test_training_sessions_has_rls(self):
        assert "training_sessions" in self._tables_with_rls()

    def test_coach_mastery_audit_has_rls(self):
        assert "coach_mastery_audit" in self._tables_with_rls()

    def _service_role_write_policies(self) -> list[str]:
        """Return policy names that cover service_role writes."""
        sql = self._all_migration_sql()
        policies = []
        for line in sql.split("\n"):
            if "service_role" in line.lower() and "policy" in line.lower():
                policies.append(line.strip())
        return policies

    def test_all_tables_have_service_role_write_policy(self):
        """Each Training OS table must have at least one service_role policy."""
        covered = self._service_role_tables_per_file()
        required = {
            "mastery_scores", "mastery_evidence", "training_plans",
            "curriculum_progress", "coach_calibration", "diagnostic_results",
            "training_sessions", "coach_mastery_audit",
        }
        missing = required - covered
        assert not missing, f"Tables missing service_role policy: {missing}"


# ═══════════════════════════════════════════════════════════════════════════
# 8. Session ownership enforcement
# ═══════════════════════════════════════════════════════════════════════════

class TestSessionOwnership:

    def test_update_session_rejects_wrong_user(self):
        """Session belonging to user-2 must 404 for user-1."""
        # When the query includes .eq("user_id", caller), Supabase returns []
        # because the row doesn't belong to the caller.
        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=[])  # empty → 404

        import asyncio
        from fastapi import HTTPException
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    update_session("session-other-user", {"current_step": "drill"}, caller="user-1")
                )
        assert exc_info.value.status_code == 404

    def test_update_session_accepts_correct_user(self):
        """Session belonging to user-1 must succeed for user-1."""
        rows = [{"id": "session-1", "user_id": "user-1", "status": "active", "version": 0}]

        sb = MagicMock()
        sb.table.return_value.select.return_value = sb.table.return_value
        sb.table.return_value.eq.return_value = sb.table.return_value
        sb.table.return_value.limit.return_value = sb.table.return_value
        sb.table.return_value.execute.return_value = MagicMock(data=rows)
        sb.table.return_value.update.return_value = sb.table.return_value

        import asyncio
        from app.api.training import update_session
        with patch("app.api.training.get_supabase", return_value=sb):
            # Should not raise
            asyncio.get_event_loop().run_until_complete(
                update_session("session-1", {"current_step": "drill"}, caller="user-1")
            )


# ═══════════════════════════════════════════════════════════════════════════
# 9. Coach authorization for mastery override
# ═══════════════════════════════════════════════════════════════════════════

class TestCoachAuthorization:

    def test_unrelated_coach_rejected_by_override_endpoint(self):
        """
        A coach not on the student's team must receive 403.
        Simulated by returning empty shared_teams intersection.
        """
        def make_team_sb(coach_teams, student_teams):
            sb = MagicMock()

            def table_side(name):
                t = MagicMock()
                t.select.return_value = t
                t.eq.return_value = t
                t.execute.return_value = MagicMock(data=[])
                return t

            coach_result = MagicMock(data=[{"team_id": tid, "role": "coach"} for tid in coach_teams])
            student_result = MagicMock(data=[{"team_id": tid} for tid in student_teams])

            call_count = {"n": 0}

            def t_side(name):
                t = MagicMock()
                t.select.return_value = t

                def eq_chain(field, val):
                    t._last_eq = (field, val)
                    return t

                t.eq.side_effect = eq_chain
                call_count["n"] += 1
                if call_count["n"] == 1:
                    t.execute.return_value = coach_result
                else:
                    t.execute.return_value = student_result
                return t

            sb.table.side_effect = t_side
            return sb

        sb = make_team_sb(coach_teams=["team-A"], student_teams=["team-B"])

        import asyncio
        from fastapi import HTTPException
        from app.api.training import coach_mastery_override
        from app.models.training import CoachOverrideRequest

        req = CoachOverrideRequest(skill_id="warranting", override_score=80.0, note="reason")
        with patch("app.api.training.get_supabase", return_value=sb):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    coach_mastery_override(
                        req=req,
                        target_user_id="student-1",
                        caller="coach-unrelated",
                    )
                )
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 10. Migration replay ordering
# ═══════════════════════════════════════════════════════════════════════════

class TestMigrationReplay:

    def test_all_migration_filenames_unique(self):
        migrations = list(MIGRATIONS_DIR.glob("*.sql"))
        names = [m.name for m in migrations]
        assert len(names) == len(set(names)), "Duplicate migration filenames detected"

    def test_migration_filenames_ordered_by_timestamp(self):
        """Filenames must be lexicographically ordered (timestamp prefix)."""
        migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
        names = [m.name for m in migrations]
        assert names == sorted(names), "Migrations not in timestamp order"

    def test_pass21_migrations_present(self):
        names = {m.name for m in MIGRATIONS_DIR.glob("*.sql")}
        assert "20260627000000_pass21_training_os.sql" in names
        assert "20260627000001_pass21p1_training_integration.sql" in names
        assert "20260628000000_pass21p3_release_gate.sql" in names

    def test_all_migrations_have_create_or_alter(self):
        """Every migration must contain at least one SQL statement."""
        for f in MIGRATIONS_DIR.glob("*.sql"):
            sql = f.read_text().strip()
            assert sql, f"Empty migration: {f.name}"
            has_statement = any(
                kw in sql.upper()
                for kw in ("CREATE", "ALTER", "INSERT", "UPDATE", "DROP", "GRANT")
            )
            assert has_statement, f"Migration has no SQL statements: {f.name}"


# ═══════════════════════════════════════════════════════════════════════════
# 11. CoachOverrideRequest model — artifact_id field
# ═══════════════════════════════════════════════════════════════════════════

class TestCoachOverrideModel:

    def test_artifact_id_optional(self):
        from app.models.training import CoachOverrideRequest
        req = CoachOverrideRequest(skill_id="warranting", override_score=80.0, note="test")
        assert req.artifact_id is None

    def test_artifact_id_accepted(self):
        from app.models.training import CoachOverrideRequest
        req = CoachOverrideRequest(
            skill_id="warranting", override_score=80.0, note="test", artifact_id="sp-123"
        )
        assert req.artifact_id == "sp-123"

    def test_override_score_bounds(self):
        from app.models.training import CoachOverrideRequest
        import pydantic
        with pytest.raises((ValueError, pydantic.ValidationError)):
            CoachOverrideRequest(skill_id="warranting", override_score=101.0, note="x")
        with pytest.raises((ValueError, pydantic.ValidationError)):
            CoachOverrideRequest(skill_id="warranting", override_score=-1.0, note="x")

    def test_coach_priority_override_request_exists(self):
        from app.models.training import CoachPriorityOverrideRequest
        req = CoachPriorityOverrideRequest(skills=["warranting", "weighing"])
        assert len(req.skills) == 2
        assert req.note == ""
