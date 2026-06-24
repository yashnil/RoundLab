"""
Health and readiness endpoints.

GET /health          — liveness probe (always 200 if app is running)
GET /health/supabase — Supabase DB connectivity check
GET /health/readiness — deep check: DB, LLM, Tavily, storage
GET /health/version  — app version and feature flags
"""
import logging
import time
from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

_APP_VERSION = "0.18.0"


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "roundlab-api", "version": _APP_VERSION}


@router.get("/health/supabase")
async def supabase_health_check() -> dict[str, str]:
    try:
        get_supabase().table("profiles").select("id").limit(1).execute()
        return {"status": "ok", "database": "reachable"}
    except Exception:
        return {"status": "error", "database": "unreachable"}


@router.get("/health/readiness")
async def readiness_check() -> dict[str, Any]:
    """
    Deep readiness probe. Checks all critical integrations.
    Returns 200 with per-service status even when checks fail, so
    the load balancer can stay warm. Check individual service status
    for alert routing.
    """
    results: dict[str, Any] = {"version": _APP_VERSION, "checks": {}}

    # 1. Supabase DB
    t0 = time.monotonic()
    try:
        get_supabase().table("profiles").select("id").limit(1).execute()
        results["checks"]["supabase"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as exc:
        results["checks"]["supabase"] = {
            "status": "error",
            "error": type(exc).__name__,
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }

    # 2. OpenAI connectivity (models list — no inference cost)
    t0 = time.monotonic()
    try:
        from app.config import get_openai_api_key
        key = get_openai_api_key()
        if not key:
            results["checks"]["openai"] = {"status": "not_configured"}
        else:
            import openai
            client = openai.OpenAI(api_key=key, timeout=5.0)
            client.models.list()
            results["checks"]["openai"] = {
                "status": "ok",
                "latency_ms": round((time.monotonic() - t0) * 1000, 1),
            }
    except Exception as exc:
        results["checks"]["openai"] = {
            "status": "error",
            "error": type(exc).__name__,
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }

    # 3. Tavily (minimal search to verify key works — 1 result)
    t0 = time.monotonic()
    try:
        from app.config import get_tavily_api_key
        import httpx
        key = get_tavily_api_key()
        if not key:
            results["checks"]["tavily"] = {"status": "not_configured"}
        else:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": "test", "max_results": 1},
                timeout=5.0,
            )
            results["checks"]["tavily"] = {
                "status": "ok" if resp.status_code < 500 else "error",
                "http_status": resp.status_code,
                "latency_ms": round((time.monotonic() - t0) * 1000, 1),
            }
    except Exception as exc:
        results["checks"]["tavily"] = {
            "status": "error",
            "error": type(exc).__name__,
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }

    # 4. Storage bucket accessibility
    t0 = time.monotonic()
    try:
        get_supabase().storage.list_buckets()
        results["checks"]["storage"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as exc:
        results["checks"]["storage"] = {
            "status": "error",
            "error": type(exc).__name__,
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }

    # Overall: degraded if any configured service errors
    failed = [k for k, v in results["checks"].items() if v.get("status") == "error"]
    results["status"] = "degraded" if failed else "ok"
    if failed:
        results["degraded_services"] = failed

    return results


@router.get("/health/version")
async def version_info() -> dict[str, Any]:
    """App version and feature flag state. Safe for public access."""
    return {
        "version": _APP_VERSION,
        "environment": settings.environment,
        "pilot_mode": settings.pilot_mode,
        "features": {
            "llm_refiner": settings.research_enable_llm_refiner,
            "semantic_reranker": settings.use_semantic_reranker,
            "academic_search": settings.research_enable_academic_search,
            "card_verification": settings.research_enable_card_verification,
            "slot_planner": settings.research_enable_slot_planner,
        },
    }
