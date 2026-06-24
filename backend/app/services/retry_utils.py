"""
Generic retry utilities for external provider calls.

All retry logic goes here so it can be tested independently of
the providers and easily adjusted without modifying call sites.

Public API:
    with_retry(fn, max_attempts, backoff_base, retryable_exceptions)
    is_retryable_status(status_code)
    RetryExhausted — raised when all attempts fail
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Optional, Sequence, Tuple, Type

logger = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """All retry attempts failed."""

    def __init__(self, last_exc: Exception, attempts: int) -> None:
        super().__init__(f"Failed after {attempts} attempts: {type(last_exc).__name__}: {last_exc}")
        self.last_exc = last_exc
        self.attempts = attempts


# Status codes that are safe to retry
_RETRYABLE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})


def is_retryable_status(status_code: int) -> bool:
    return status_code in _RETRYABLE_HTTP_CODES


def with_retry(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 3,
    backoff_base: float = 0.5,
    backoff_max: float = 8.0,
    retryable_exceptions: Sequence[Type[Exception]] = (Exception,),
    operation_name: str = "operation",
) -> Any:
    """
    Call fn() up to max_attempts times with exponential backoff.

    Raises RetryExhausted if all attempts fail.
    Does NOT retry on non-Exception subclass errors (e.g. KeyboardInterrupt).
    """
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except tuple(retryable_exceptions) as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt == max_attempts:
                break
            delay = min(backoff_base * (2 ** (attempt - 1)), backoff_max)
            logger.warning(
                "retry: %s | attempt=%d/%d | exc=%s | delay=%.1fs",
                operation_name,
                attempt,
                max_attempts,
                type(exc).__name__,
                delay,
            )
            time.sleep(delay)

    assert last_exc is not None
    raise RetryExhausted(last_exc=last_exc, attempts=max_attempts)


async def with_retry_async(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 3,
    backoff_base: float = 0.5,
    backoff_max: float = 8.0,
    retryable_exceptions: Sequence[Type[Exception]] = (Exception,),
    operation_name: str = "operation",
) -> Any:
    """Async variant of with_retry using asyncio.sleep for non-blocking backoff."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = fn()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except tuple(retryable_exceptions) as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt == max_attempts:
                break
            delay = min(backoff_base * (2 ** (attempt - 1)), backoff_max)
            logger.warning(
                "retry_async: %s | attempt=%d/%d | exc=%s | delay=%.1fs",
                operation_name,
                attempt,
                max_attempts,
                type(exc).__name__,
                delay,
            )
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise RetryExhausted(last_exc=last_exc, attempts=max_attempts)


def make_supabase_retry(
    fn: Callable[[], Any],
    operation_name: str = "supabase_query",
) -> Any:
    """Thin wrapper: retry Supabase calls with sensible defaults."""
    return with_retry(
        fn,
        max_attempts=3,
        backoff_base=0.3,
        backoff_max=4.0,
        operation_name=operation_name,
    )


def make_llm_retry(
    fn: Callable[[], Any],
    operation_name: str = "llm_call",
) -> Any:
    """Thin wrapper: retry LLM calls (OpenAI transient errors)."""
    from openai import RateLimitError, APIConnectionError, InternalServerError

    return with_retry(
        fn,
        max_attempts=3,
        backoff_base=1.0,
        backoff_max=10.0,
        retryable_exceptions=(RateLimitError, APIConnectionError, InternalServerError),
        operation_name=operation_name,
    )
