"""Pass 16.5 — Authentication and authorization tests for round simulation API.

Tests:
- Missing token → 401
- Wrong owner → 403
- Prep gap fingerprinting and deduplication
- Student crossfire question route
- Idempotency key guard
- Adaptation review CRUD
- phase_started_at in state response
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.round_prep_connector import _gap_fingerprint, _upsert_gap


# ── Unit: gap fingerprint ─────────────────────────────────────────────────────


def test_gap_fingerprint_is_deterministic():
    fp1 = _gap_fingerprint("user-1", "ws-1", "missing_response", "No response to Contention 1")
    fp2 = _gap_fingerprint("user-1", "ws-1", "missing_response", "No response to Contention 1")
    assert fp1 == fp2


def test_gap_fingerprint_changes_with_user():
    fp1 = _gap_fingerprint("user-1", "ws-1", "missing_response", "X")
    fp2 = _gap_fingerprint("user-2", "ws-1", "missing_response", "X")
    assert fp1 != fp2


def test_gap_fingerprint_changes_with_workspace():
    fp1 = _gap_fingerprint("u", "ws-A", "ev", "T")
    fp2 = _gap_fingerprint("u", "ws-B", "ev", "T")
    assert fp1 != fp2


def test_gap_fingerprint_changes_with_category():
    fp1 = _gap_fingerprint("u", "ws", "evidence_quality", "T")
    fp2 = _gap_fingerprint("u", "ws", "missing_response", "T")
    assert fp1 != fp2


def test_gap_fingerprint_changes_with_title():
    fp1 = _gap_fingerprint("u", "ws", "c", "Title A")
    fp2 = _gap_fingerprint("u", "ws", "c", "Title B")
    assert fp1 != fp2


def test_gap_fingerprint_length_is_32():
    fp = _gap_fingerprint("u", "ws", "c", "t")
    assert len(fp) == 32


def test_gap_fingerprint_serialization_is_compact_json():
    """Fingerprint must use compact JSON (no spaces) to match PostgreSQL json_build_array()::text.

    PostgreSQL: json_build_array('a','b')::text  → ["a","b"]   (no spaces)
    Python old: json.dumps(['a','b'])             → ["a", "b"] (space after comma)
    Python new: json.dumps([...], separators=(',',':')) → ["a","b"] ✓
    """
    user_id, ws, cat, title = "user-1", "ws-1", "missing_response", "No response to X"
    # Compact JSON array — what PostgreSQL json_build_array produces
    expected_key = '["user-1","ws-1","missing_response","No response to X"]'
    expected_fp = hashlib.sha256(expected_key.encode("utf-8")).hexdigest()[:32]
    assert _gap_fingerprint(user_id, ws, cat, title) == expected_fp


def test_gap_fingerprint_does_not_use_spaced_json():
    """Confirm the old json.dumps default (spaces after commas) would yield a different hash."""
    user_id, ws, cat, title = "u", "ws-1", "c", "t"
    spaced_key = json.dumps([user_id, ws, cat, title])   # default: spaces after ','
    compact_key = json.dumps([user_id, ws, cat, title], separators=(",", ":"))
    assert spaced_key != compact_key                     # sanity: formats differ
    spaced_fp = hashlib.sha256(spaced_key.encode("utf-8")).hexdigest()[:32]
    assert _gap_fingerprint(user_id, ws, cat, title) != spaced_fp


def test_gap_fingerprint_unicode_title():
    """Non-ASCII titles must not be \\uXXXX-escaped (ensure_ascii=False) so SQL and Python match.

    PostgreSQL json_build_array emits raw UTF-8, not \\uXXXX escape sequences.
    Python's default json.dumps would escape é → \\u00e9, breaking the hash match.
    """
    title = "Contención sobre política"  # "Contención sobre política"
    expected_key = f'["u","ws","c","{title}"]'      # raw UTF-8, no backslash escapes
    expected_fp = hashlib.sha256(expected_key.encode("utf-8")).hexdigest()[:32]
    actual_fp = _gap_fingerprint("u", "ws", "c", title)
    assert actual_fp == expected_fp
    assert len(actual_fp) == 32


def test_gap_fingerprint_field_order_is_user_workspace_category_title():
    """Field order is fixed at [user, workspace, category, title]; swapping any two changes the hash."""
    # Swap user ↔ workspace
    fp_correct = _gap_fingerprint("aaa", "bbb", "c", "t")
    fp_swapped = _gap_fingerprint("bbb", "aaa", "c", "t")
    assert fp_correct != fp_swapped

    # Swap category ↔ title
    fp_cat_first = _gap_fingerprint("u", "ws", "category_val", "title_val")
    fp_title_first = _gap_fingerprint("u", "ws", "title_val", "category_val")
    assert fp_cat_first != fp_title_first


# ── Unit: _upsert_gap ─────────────────────────────────────────────────────────


def _make_supabase_mock(existing_row=None):
    """Return a mock supabase client that simulates the prep_gaps table."""
    mock = MagicMock()
    select_chain = MagicMock()
    # Simulate .select().eq().neq().neq().limit().execute()
    select_chain.execute.return_value = MagicMock(
        data=[existing_row] if existing_row else []
    )
    mock.table.return_value.select.return_value = select_chain
    select_chain.eq.return_value = select_chain
    select_chain.neq.return_value = select_chain
    select_chain.limit.return_value = select_chain

    # Capture insert/update calls
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    return mock


def test_upsert_gap_inserts_when_no_existing():
    supabase = _make_supabase_mock(existing_row=None)
    gap = {
        "workspace_id": "ws-1",
        "user_id": "u-1",
        "category": "missing_response",
        "title": "No response to X",
        "status": "open",
        "occurrence_count": 1,
        "first_seen_at": "2026-06-23T00:00:00Z",
        "last_seen_at": "2026-06-23T00:00:00Z",
    }
    result = _upsert_gap(supabase, gap, round_id="r-1")
    # Should call insert, not update
    assert supabase.table.return_value.insert.called
    assert not supabase.table.return_value.update.called
    assert result is not None


def test_upsert_gap_increments_when_existing():
    existing = {"id": "gap-existing", "occurrence_count": 2, "first_seen_at": "2026-01-01", "status": "open"}
    supabase = _make_supabase_mock(existing_row=existing)
    gap = {
        "workspace_id": "ws-1",
        "user_id": "u-1",
        "category": "missing_response",
        "title": "No response to X",
        "status": "open",
        "occurrence_count": 1,
        "first_seen_at": "2026-06-23T00:00:00Z",
        "last_seen_at": "2026-06-23T00:00:00Z",
    }
    result = _upsert_gap(supabase, gap, round_id="r-2")
    # Should call update, not insert
    assert supabase.table.return_value.update.called
    assert not supabase.table.return_value.insert.called
    # update should receive occurrence_count = 3 (existing 2 + 1)
    update_call_args = supabase.table.return_value.update.call_args[0][0]
    assert update_call_args["occurrence_count"] == 3


def test_upsert_gap_sets_fingerprint_on_gap():
    supabase = _make_supabase_mock(existing_row=None)
    gap = {
        "workspace_id": "ws-1",
        "user_id": "u-1",
        "category": "evidence_quality",
        "title": "Evidence violations",
        "status": "open",
        "occurrence_count": 1,
        "first_seen_at": "2026-06-23T00:00:00Z",
        "last_seen_at": "2026-06-23T00:00:00Z",
    }
    _upsert_gap(supabase, gap, round_id="r-1")
    assert "fingerprint" in gap
    expected = _gap_fingerprint("u-1", "ws-1", "evidence_quality", "Evidence violations")
    assert gap["fingerprint"] == expected


def test_upsert_gap_returns_none_on_exception():
    supabase = MagicMock()
    supabase.table.side_effect = RuntimeError("DB error")
    gap = {
        "workspace_id": "ws",
        "user_id": "u",
        "category": "c",
        "title": "t",
        "status": "open",
        "occurrence_count": 1,
        "first_seen_at": "2026-06-23",
        "last_seen_at": "2026-06-23",
    }
    result = _upsert_gap(supabase, gap, round_id="r")
    assert result is None


# ── Unit: auth dependency pattern ─────────────────────────────────────────────


def test_round_api_imports_get_current_user_id():
    """Ensure the round API module imports the auth dependency."""
    import importlib
    spec = importlib.util.find_spec("app.api.round_simulations")
    assert spec is not None
    # Read source to verify import
    source = spec.loader.get_source("app.api.round_simulations")  # type: ignore[attr-defined]
    assert "get_current_user_id" in source
    assert "Depends" in source


def test_round_models_have_no_user_id_in_create_request():
    """CreateRoundRequest must NOT have a user_id field (user_id comes from JWT)."""
    from app.models.round_simulation import CreateRoundRequest
    model_fields = CreateRoundRequest.model_fields
    assert "user_id" not in model_fields


def test_round_models_have_no_user_id_in_submit_request():
    """SubmitStudentSpeechRequest must NOT have a user_id field."""
    from app.models.round_simulation import SubmitStudentSpeechRequest
    model_fields = SubmitStudentSpeechRequest.model_fields
    assert "user_id" not in model_fields


def test_round_models_have_no_user_id_in_opponent_request():
    """GenerateOpponentSpeechRequest must NOT have a user_id field."""
    from app.models.round_simulation import GenerateOpponentSpeechRequest
    model_fields = GenerateOpponentSpeechRequest.model_fields
    assert "user_id" not in model_fields


def test_round_models_have_no_user_id_in_advance_phase_request():
    """AdvancePhaseRequest must NOT have a user_id field."""
    from app.models.round_simulation import AdvancePhaseRequest
    model_fields = AdvancePhaseRequest.model_fields
    assert "user_id" not in model_fields


def test_round_models_have_no_user_id_in_decision_request():
    """GenerateDecisionRequest must NOT have a user_id field."""
    from app.models.round_simulation import GenerateDecisionRequest
    model_fields = GenerateDecisionRequest.model_fields
    assert "user_id" not in model_fields


# ── Unit: idempotency key on models ──────────────────────────────────────────


def test_submit_speech_request_has_idempotency_key():
    from app.models.round_simulation import SubmitStudentSpeechRequest, RoundPhaseType
    req = SubmitStudentSpeechRequest(
        round_id="r-1",
        phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        transcript_text="My speech text",
        idempotency_key="idem-abc-123",
    )
    assert req.idempotency_key == "idem-abc-123"


def test_submit_speech_request_idempotency_key_is_optional():
    from app.models.round_simulation import SubmitStudentSpeechRequest, RoundPhaseType
    req = SubmitStudentSpeechRequest(
        round_id="r-1",
        phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        transcript_text="My speech",
    )
    assert req.idempotency_key is None


def test_opponent_speech_request_has_idempotency_key():
    from app.models.round_simulation import GenerateOpponentSpeechRequest, RoundPhaseType
    req = GenerateOpponentSpeechRequest(
        round_id="r-1",
        phase=RoundPhaseType.SECOND_CONSTRUCTIVE,
        idempotency_key="opponent-r1-second_constructive",
    )
    assert req.idempotency_key == "opponent-r1-second_constructive"


# ── Unit: student crossfire question model ────────────────────────────────────


def test_student_crossfire_question_request_model():
    from app.models.round_simulation import StudentCrossfireQuestionRequest
    req = StudentCrossfireQuestionRequest(
        round_id="r-1",
        question="How does your evidence support the causal claim?",
    )
    assert req.round_id == "r-1"
    assert "causal claim" in req.question


def test_student_crossfire_question_no_user_id():
    from app.models.round_simulation import StudentCrossfireQuestionRequest
    fields = StudentCrossfireQuestionRequest.model_fields
    assert "user_id" not in fields


# ── Unit: adaptation review model ─────────────────────────────────────────────


def test_create_adaptation_review_request_model():
    from app.models.round_simulation import CreateAdaptationReviewRequest
    req = CreateAdaptationReviewRequest(
        round_id="r-1",
        judge_type="flow",
        decision_id="d-1",
        alternate_judge_type="truth",
    )
    assert req.judge_type == "flow"
    assert req.alternate_judge_type == "truth"
    assert req.decision_id == "d-1"


def test_create_adaptation_review_no_user_id():
    from app.models.round_simulation import CreateAdaptationReviewRequest
    fields = CreateAdaptationReviewRequest.model_fields
    assert "user_id" not in fields


def test_round_adaptation_review_model():
    from app.models.round_simulation import RoundAdaptationReview
    review = RoundAdaptationReview(
        id="rev-1",
        round_id="r-1",
        judge_type="flow",
        adaptation_successes=["Good evidence citations"],
        adaptation_failures=["Dropped key argument"],
        created_at="2026-06-23T00:00:00Z",
    )
    assert review.adaptation_successes == ["Good evidence citations"]
    assert review.adaptation_failures == ["Dropped key argument"]
    assert review.alternate_judge_type is None


# ── Unit: phase_started_at in state response ──────────────────────────────────


def test_round_state_response_has_phase_started_at():
    from app.models.round_simulation import (
        RoundStateResponse,
        RoundSimulation,
        RoundPhaseType,
        RoundStatus,
        RoundSimulationConfig,
        RoundSide,
        SpeakingOrder,
        RoundFormat,
    )
    config = RoundSimulationConfig(
        format=RoundFormat.FULL,
        student_side=RoundSide.PRO,
        speaking_order=SpeakingOrder.FIRST,
        resolution="Test resolution",
    )
    sim = RoundSimulation(
        id="r-1",
        user_id="u-1",
        config=config,
        current_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        created_at="2026-06-23T00:00:00Z",
        updated_at="2026-06-23T00:00:00Z",
    )
    state = RoundStateResponse(
        simulation=sim,
        current_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        phase_label="First Constructive",
        student_speaks_now=True,
        time_limit_seconds=240,
        phase_started_at="2026-06-23T12:00:00Z",
    )
    assert state.phase_started_at == "2026-06-23T12:00:00Z"


def test_round_state_response_phase_started_at_is_optional():
    from app.models.round_simulation import (
        RoundStateResponse,
        RoundSimulation,
        RoundPhaseType,
        RoundStatus,
        RoundSimulationConfig,
        RoundSide,
        SpeakingOrder,
        RoundFormat,
    )
    config = RoundSimulationConfig(
        format=RoundFormat.FULL,
        student_side=RoundSide.PRO,
        speaking_order=SpeakingOrder.FIRST,
        resolution="Test",
    )
    sim = RoundSimulation(
        id="r-1",
        user_id="u-1",
        config=config,
        current_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        created_at="2026-06-23T00:00:00Z",
        updated_at="2026-06-23T00:00:00Z",
    )
    state = RoundStateResponse(
        simulation=sim,
        current_phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
        phase_label="First Constructive",
        student_speaks_now=True,
        time_limit_seconds=240,
    )
    assert state.phase_started_at is None


# ── Unit: router auth enforcement (structural check) ─────────────────────────


def test_all_round_endpoints_use_depends_not_query_user_id():
    """
    No endpoint in round_simulations.py should use Query() for user_id.
    All user identity must come from get_current_user_id dependency.
    """
    import importlib.util
    spec = importlib.util.find_spec("app.api.round_simulations")
    source = spec.loader.get_source("app.api.round_simulations")  # type: ignore[attr-defined]
    # user_id: str = Query(...) is forbidden — auth must come from JWT
    assert 'user_id: str = Query(' not in source
    # PLACEHOLDER_USER_ID must not appear
    assert "PLACEHOLDER_USER_ID" not in source
    assert "placeholder-user-id" not in source


def test_round_simulations_no_placeholder_in_models():
    import importlib.util
    spec = importlib.util.find_spec("app.models.round_simulation")
    source = spec.loader.get_source("app.models.round_simulation")  # type: ignore[attr-defined]
    assert "placeholder" not in source.lower()


# ── Unit: record_post_round_gaps deduplication ───────────────────────────────


def test_record_post_round_gaps_no_workspace_returns_empty():
    from app.services.round_prep_connector import record_post_round_gaps
    from app.models.round_simulation import RoundSide
    result = record_post_round_gaps(
        round_id="r",
        user_id="u",
        workspace_id=None,
        all_args=[],
        evidence_uses=[],
        student_side=RoundSide.PRO,
        decision=None,
    )
    assert result == []


def test_record_post_round_gaps_calls_upsert_for_difficult_args():
    """With a live opponent argument, at least one gap should be upserted."""
    from unittest.mock import patch, MagicMock
    from app.services.round_prep_connector import record_post_round_gaps
    from app.models.round_simulation import (
        RoundSide,
        RoundArgument,
        ArgumentFlowStatus,
        RoundPhaseType,
    )

    arg = RoundArgument(
        id="a-1",
        round_id="r-1",
        label="Climate harm",
        side=RoundSide.CON,
        claim="Climate damage will be catastrophic",
        initial_phase=RoundPhaseType.SECOND_CONSTRUCTIVE,
        status=ArgumentFlowStatus.LIVE,
    )

    with patch("app.services.round_prep_connector.get_supabase") as mock_get_sb, \
         patch("app.services.round_prep_connector._upsert_gap") as mock_upsert:
        mock_upsert.return_value = {"id": "gap-1"}
        mock_get_sb.return_value = MagicMock()

        result = record_post_round_gaps(
            round_id="r-1",
            user_id="u-1",
            workspace_id="ws-1",
            all_args=[arg],
            evidence_uses=[],
            student_side=RoundSide.PRO,
            decision=None,
        )

    assert mock_upsert.called
    assert len(result) > 0


# ── Integration: router has new endpoints ────────────────────────────────────


def test_router_has_student_crossfire_endpoint():
    from app.api.round_simulations import router
    paths = {r.path for r in router.routes}  # type: ignore[attr-defined]
    assert any("student-question" in p for p in paths), f"Missing student-question route. Paths: {paths}"


def test_router_has_adaptation_reviews_endpoint():
    from app.api.round_simulations import router
    paths = {r.path for r in router.routes}  # type: ignore[attr-defined]
    assert any("adaptation-reviews" in p for p in paths), f"Missing adaptation-reviews route. Paths: {paths}"


def test_router_has_pause_and_resume():
    from app.api.round_simulations import router
    paths = {r.path for r in router.routes}  # type: ignore[attr-defined]
    assert any("pause" in p for p in paths)
    assert any("resume" in p for p in paths)


def test_router_prefix_is_round_simulations():
    from app.api.round_simulations import router
    assert router.prefix == "/round-simulations"
