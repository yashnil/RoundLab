"""
Request correlation middleware.

Injects a per-request ID into every response header and into a
contextvariable that all log calls in the same request can read.
Also records wall-clock request duration.

Usage in main.py:
    from app.middleware.correlation import CorrelationMiddleware
    app.add_middleware(CorrelationMiddleware)
"""
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Request-scoped context: readable from any module during the request
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_request_start_var: ContextVar[float] = ContextVar("request_start", default=0.0)


def get_request_id() -> str:
    return _request_id_var.get()


def get_elapsed_ms() -> float:
    start = _request_start_var.get()
    return round((time.monotonic() - start) * 1000, 1) if start else 0.0


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.monotonic()

        _request_id_var.set(request_id)
        _request_start_var.set(start)

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)

        # Structured access log — safe fields only (no bodies, no auth headers)
        status = response.status_code
        method = request.method
        path = request.url.path
        log_fn = logger.warning if status >= 500 else logger.info
        log_fn(
            "request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": status,
                "elapsed_ms": elapsed_ms,
            },
        )

        return response
