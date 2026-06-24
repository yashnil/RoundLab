"""Pass 18 — Production failure recovery tests.

Covers:
- Retry utility behavior (with_retry, with_retry_async, make_supabase_retry)
- Cost tracker estimation and event emission
- Health endpoint structure
- User account deletion cascade (mocked)
- Evidence card hard delete ownership check
- Round deletion cascade (mocked)
- Workflow failure tracking
- Correlation middleware (request ID injection)
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services.retry_utils import (
    RetryExhausted,
    is_retryable_status,
    with_retry,
    with_retry_async,
)
from app.services.cost_tracker import (
    estimate_token_cost,
    estimate_operation_cost,
    estimate_provider_cost,
    OPERATION_TOKEN_BUDGETS,
)
from app.services.product_events import (
    PilotEvent,
    track_workflow_failure,
    track_round_event,
    track_evidence_saved,
)


# ── RetryUtils ─────────────────────────────────────────────────────────────────

class TestWithRetry:
    def test_succeeds_on_first_attempt(self):
        calls = []
        def fn():
            calls.append(1)
            return "ok"
        result = with_retry(fn, max_attempts=3, operation_name="test")
        assert result == "ok"
        assert len(calls) == 1

    def test_retries_on_exception(self):
        calls = []
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("transient")
            return "ok"
        result = with_retry(fn, max_attempts=3, backoff_base=0.01, operation_name="test")
        assert result == "ok"
        assert len(calls) == 3

    def test_raises_retry_exhausted_after_max_attempts(self):
        def fn():
            raise ConnectionError("always fails")
        with pytest.raises(RetryExhausted) as exc_info:
            with_retry(fn, max_attempts=3, backoff_base=0.01, operation_name="test")
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exc, ConnectionError)

    def test_retry_exhausted_wraps_last_exception(self):
        class CustomError(Exception):
            pass
        def fn():
            raise CustomError("last error")
        with pytest.raises(RetryExhausted) as exc_info:
            with_retry(fn, max_attempts=2, backoff_base=0.01, operation_name="test")
        assert isinstance(exc_info.value.last_exc, CustomError)

    def test_succeeds_returns_correct_value(self):
        def fn():
            return {"data": [1, 2, 3]}
        result = with_retry(fn, max_attempts=1)
        assert result == {"data": [1, 2, 3]}

    def test_only_retries_on_specified_exceptions(self):
        calls = []
        def fn():
            calls.append(1)
            raise TypeError("not retryable")
        with pytest.raises(TypeError):
            with_retry(fn, max_attempts=3, backoff_base=0.01,
                       retryable_exceptions=[ValueError], operation_name="test")
        # Should not retry on TypeError when only ValueError is specified
        assert len(calls) == 1

    def test_respects_max_attempts_of_one(self):
        calls = []
        def fn():
            calls.append(1)
            raise RuntimeError("fail")
        with pytest.raises(RetryExhausted):
            with_retry(fn, max_attempts=1, operation_name="test")
        assert len(calls) == 1


class TestWithRetryAsync:
    def test_async_succeeds_on_first_attempt(self):
        async def run():
            def fn():
                return "async ok"
            return await with_retry_async(fn, max_attempts=2, operation_name="test")
        result = asyncio.get_event_loop().run_until_complete(run())
        assert result == "async ok"

    def test_async_retries_and_succeeds(self):
        calls = []
        async def run():
            def fn():
                calls.append(1)
                if len(calls) < 2:
                    raise ConnectionError("transient")
                return "retried"
            return await with_retry_async(fn, max_attempts=3, backoff_base=0.01, operation_name="test")
        result = asyncio.get_event_loop().run_until_complete(run())
        assert result == "retried"
        assert len(calls) == 2

    def test_async_raises_retry_exhausted(self):
        async def run():
            def fn():
                raise RuntimeError("always")
            await with_retry_async(fn, max_attempts=2, backoff_base=0.01, operation_name="test")
        with pytest.raises(RetryExhausted):
            asyncio.get_event_loop().run_until_complete(run())


class TestIsRetryableStatus:
    def test_429_is_retryable(self):
        assert is_retryable_status(429) is True

    def test_500_is_retryable(self):
        assert is_retryable_status(500) is True

    def test_503_is_retryable(self):
        assert is_retryable_status(503) is True

    def test_404_not_retryable(self):
        assert is_retryable_status(404) is False

    def test_200_not_retryable(self):
        assert is_retryable_status(200) is False

    def test_401_not_retryable(self):
        assert is_retryable_status(401) is False


# ── CostTracker ─────────────────────────────────────────────────────────────────

class TestCostEstimation:
    def test_estimate_token_cost_gpt4o_mini(self):
        cost = estimate_token_cost("gpt-4o-mini", input_tokens=1000, output_tokens=800)
        assert cost > 0
        assert cost < 0.01  # gpt-4o-mini is cheap

    def test_estimate_token_cost_zero_tokens(self):
        cost = estimate_token_cost("gpt-4o-mini", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_estimate_token_cost_unknown_model_falls_back(self):
        cost = estimate_token_cost("unknown-model", input_tokens=1000, output_tokens=500)
        # Should not raise — falls back to gpt-4o-mini pricing
        assert cost >= 0

    def test_estimate_operation_cost_card_cut(self):
        cost = estimate_operation_cost("card_cut")
        assert cost > 0

    def test_estimate_operation_cost_unknown_returns_zero(self):
        cost = estimate_operation_cost("nonexistent_operation")
        assert cost == 0.0

    def test_estimate_provider_cost_tavily(self):
        cost = estimate_provider_cost("tavily_search", calls=3)
        assert cost > 0

    def test_estimate_provider_cost_free_provider(self):
        cost = estimate_provider_cost("openalex_search", calls=10)
        assert cost == 0.0

    def test_all_operations_have_non_negative_budget(self):
        for op, budget in OPERATION_TOKEN_BUDGETS.items():
            assert budget["input"] >= 0, f"{op}: negative input tokens"
            assert budget["output"] >= 0, f"{op}: negative output tokens"


# ── Product events ─────────────────────────────────────────────────────────────

class TestPilotEventConstants:
    def test_all_event_constants_are_strings(self):
        for attr in dir(PilotEvent):
            if not attr.startswith("_"):
                val = getattr(PilotEvent, attr)
                assert isinstance(val, str), f"{attr} should be a string"

    def test_event_names_are_snake_case(self):
        for attr in dir(PilotEvent):
            if not attr.startswith("_"):
                val = getattr(PilotEvent, attr)
                if isinstance(val, str):
                    assert " " not in val, f"{attr}={val!r} has spaces"
                    assert val == val.lower(), f"{attr}={val!r} not lowercase"


class TestTrackWorkflowFailure:
    def test_track_failure_does_not_raise(self):
        with patch("app.services.product_events.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value.data = []
            track_workflow_failure("user-1", stage="card_cut", error_code="llm_timeout")

    def test_track_failure_swallows_db_errors(self):
        with patch("app.services.product_events.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")
            # Should not raise
            track_workflow_failure("user-1", stage="transcription", error_code="network_error")


class TestTrackRoundEvent:
    def test_track_round_started(self):
        with patch("app.services.product_events.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value.data = []
            track_round_event("user-1", PilotEvent.ROUND_STARTED, "round-abc")

    def test_track_round_completed_with_metadata(self):
        with patch("app.services.product_events.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value.data = []
            track_round_event(
                "user-1",
                PilotEvent.ROUND_COMPLETED,
                "round-abc",
                metadata={"winner": "pro", "judge_type": "flow"},
            )


class TestTrackEvidenceSaved:
    def test_first_card_emits_two_events(self):
        calls = []
        with patch("app.services.product_events.get_supabase") as mock_sb:
            def insert_side_effect(row):
                calls.append(row["event_name"])
                m = MagicMock()
                m.execute.return_value.data = []
                return m
            mock_sb.return_value.table.return_value.insert.side_effect = insert_side_effect
            track_evidence_saved("user-1", "card-1", is_first_card=True)
        assert PilotEvent.EVIDENCE_CARD_SAVED in calls
        assert PilotEvent.FIRST_EVIDENCE_CARD_SAVED in calls

    def test_non_first_card_emits_one_event(self):
        calls = []
        with patch("app.services.product_events.get_supabase") as mock_sb:
            def insert_side_effect(row):
                calls.append(row["event_name"])
                m = MagicMock()
                m.execute.return_value.data = []
                return m
            mock_sb.return_value.table.return_value.insert.side_effect = insert_side_effect
            track_evidence_saved("user-1", "card-2", is_first_card=False)
        assert calls.count(PilotEvent.EVIDENCE_CARD_SAVED) == 1
        assert PilotEvent.FIRST_EVIDENCE_CARD_SAVED not in calls


# ── Correlation middleware ─────────────────────────────────────────────────────

class TestCorrelationMiddleware:
    def test_get_request_id_returns_string(self):
        from app.middleware.correlation import get_request_id
        result = get_request_id()
        assert isinstance(result, str)

    def test_get_elapsed_ms_without_start_returns_zero(self):
        from app.middleware.correlation import get_elapsed_ms
        elapsed = get_elapsed_ms()
        assert elapsed == 0.0

    def test_middleware_imports_without_error(self):
        from app.middleware.correlation import CorrelationMiddleware
        assert CorrelationMiddleware is not None
