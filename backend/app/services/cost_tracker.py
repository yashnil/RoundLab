"""
Cost tracking for LLM and provider calls.

Estimates token costs per operation, logs them as product events,
and enforces daily per-user budget limits when pilot_mode is enabled.

Cost estimates are approximate — actual billing is determined by
the provider. Use these only for budgeting and monitoring.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Price table (USD per 1K tokens, as of 2026) ───────────────────────────────
# These are estimates — update when provider pricing changes.
_PRICE_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "whisper-1": {"input": 0.006, "output": 0.0},  # per minute not tokens; approximate
}

# Known per-call costs (USD) for non-token providers
_PROVIDER_CALL_COSTS: dict[str, float] = {
    "tavily_search": 0.005,    # per search request
    "exa_search": 0.005,
    "cohere_rerank": 0.001,
    "firecrawl_scrape": 0.003,
    "crossref_lookup": 0.0,    # free
    "openalex_search": 0.0,
    "semantic_scholar": 0.0,
}

# Per-operation token budget targets — used to estimate cost upfront
OPERATION_TOKEN_BUDGETS: dict[str, dict[str, int]] = {
    "card_cut": {"input": 2000, "output": 800},
    "card_verify": {"input": 1500, "output": 600},
    "card_refine": {"input": 1000, "output": 400},
    "speech_transcription": {"input": 0, "output": 0},  # flat per minute
    "speech_analysis": {"input": 3000, "output": 1000},
    "feedback_generation": {"input": 4000, "output": 1500},
    "crossfire_response": {"input": 1000, "output": 300},
    "opponent_speech": {"input": 2000, "output": 600},
    "ballot_generation": {"input": 3000, "output": 1000},
    "judge_adaptation": {"input": 2000, "output": 800},
    "evidence_role_classify": {"input": 500, "output": 150},
    "tag_generation": {"input": 400, "output": 150},
}

# Maximum estimated USD cost per operation — hard limit enforced in pilot_mode
OPERATION_COST_LIMITS: dict[str, float] = {
    "card_cut": 0.01,
    "card_verify": 0.005,
    "speech_analysis": 0.02,
    "feedback_generation": 0.03,
    "opponent_speech": 0.01,
    "ballot_generation": 0.02,
}


def estimate_token_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Return estimated USD cost for the given token counts."""
    prices = _PRICE_PER_1K.get(model, _PRICE_PER_1K["gpt-4o-mini"])
    cost = (input_tokens / 1000) * prices["input"] + (output_tokens / 1000) * prices["output"]
    return round(cost, 6)


def estimate_operation_cost(operation: str, model: str = "gpt-4o-mini") -> float:
    """Return estimated worst-case USD cost for an operation."""
    budget = OPERATION_TOKEN_BUDGETS.get(operation)
    if not budget:
        return 0.0
    return estimate_token_cost(model, budget["input"], budget["output"])


def estimate_provider_cost(provider: str, calls: int = 1) -> float:
    """Return estimated USD cost for provider API calls."""
    per_call = _PROVIDER_CALL_COSTS.get(provider, 0.0)
    return round(per_call * calls, 6)


def track_llm_cost(
    user_id: str,
    operation: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    round_id: Optional[str] = None,
    speech_id: Optional[str] = None,
) -> float:
    """
    Record actual LLM cost for an operation as a product event.

    Returns the cost estimate (USD). Never raises.
    """
    try:
        from app.services.product_events import track_product_event

        cost_usd = estimate_token_cost(model, input_tokens, output_tokens)
        metadata: dict[str, Any] = {
            "operation": operation,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }
        if round_id:
            metadata["round_id"] = round_id
        track_product_event(
            user_id=user_id,
            event_name="llm_cost_incurred",
            speech_id=speech_id,
            metadata=metadata,
        )
        return cost_usd
    except Exception as exc:
        logger.debug("track_llm_cost: failed silently | exc=%s", type(exc).__name__)
        return 0.0


def track_provider_cost(
    user_id: str,
    provider: str,
    calls: int = 1,
    speech_id: Optional[str] = None,
) -> float:
    """Record provider API cost as a product event. Never raises."""
    try:
        from app.services.product_events import track_product_event

        cost_usd = estimate_provider_cost(provider, calls)
        if cost_usd == 0.0:
            return 0.0
        track_product_event(
            user_id=user_id,
            event_name="provider_cost_incurred",
            speech_id=speech_id,
            metadata={"provider": provider, "calls": calls, "cost_usd": cost_usd},
        )
        return cost_usd
    except Exception as exc:
        logger.debug("track_provider_cost: failed silently | exc=%s", type(exc).__name__)
        return 0.0


def get_daily_cost_summary(user_id: str) -> dict[str, Any]:
    """
    Return today's estimated cost breakdown for a user.

    Returns empty summary if tracking data is unavailable.
    """
    try:
        from app.services.supabase_client import get_supabase

        supabase = get_supabase()
        res = (
            supabase.table("product_events")
            .select("event_name, metadata_json, created_at")
            .eq("user_id", user_id)
            .in_("event_name", ["llm_cost_incurred", "provider_cost_incurred"])
            .gte("created_at", _today_iso())
            .execute()
        )

        total_usd = 0.0
        by_operation: dict[str, float] = {}
        for row in res.data or []:
            meta = row.get("metadata_json") or {}
            cost = float(meta.get("cost_usd", 0))
            total_usd += cost
            key = meta.get("operation") or meta.get("provider") or "unknown"
            by_operation[key] = by_operation.get(key, 0.0) + cost

        return {
            "user_id": user_id,
            "date": _today_iso(),
            "total_usd": round(total_usd, 4),
            "by_operation": {k: round(v, 6) for k, v in by_operation.items()},
        }
    except Exception as exc:
        logger.debug("get_daily_cost_summary: failed | exc=%s", type(exc).__name__)
        return {"user_id": user_id, "date": _today_iso(), "total_usd": 0.0, "by_operation": {}}


def _today_iso() -> str:
    from datetime import date

    return date.today().isoformat()
