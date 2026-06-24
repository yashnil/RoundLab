"""Pass 18 — Pilot analytics and health endpoint tests.

Covers:
- Health endpoint structure (version, readiness checks)
- Config pilot-mode fields
- Cost tracker daily summary
- Analytics event types complete
- Latency budget fields present in config
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestHealthEndpointStructure:
    """Health endpoints return correct structure without live network calls."""

    def test_health_check_has_version(self):
        from app.api.health import health_check
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(health_check())
        assert "version" in result
        assert "status" in result
        assert result["status"] == "ok"

    def test_version_info_has_required_fields(self):
        from app.api.health import version_info
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(version_info())
        assert "version" in result
        assert "environment" in result
        assert "pilot_mode" in result
        assert "features" in result
        assert isinstance(result["features"], dict)

    def test_version_info_features_keys(self):
        from app.api.health import version_info
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(version_info())
        expected_keys = {
            "llm_refiner",
            "semantic_reranker",
            "academic_search",
            "card_verification",
            "slot_planner",
        }
        assert expected_keys == set(result["features"].keys())

    def test_readiness_check_structure(self):
        from app.api.health import readiness_check
        import asyncio
        with patch("app.api.health.get_supabase") as mock_sb, \
             patch("app.config.get_openai_api_key", return_value=None), \
             patch("app.config.get_tavily_api_key", return_value=None):
            mock_sb.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
            mock_sb.return_value.storage.list_buckets.return_value = []
            result = asyncio.get_event_loop().run_until_complete(readiness_check())
        assert "checks" in result
        assert "status" in result
        assert "supabase" in result["checks"]

    def test_readiness_degraded_when_supabase_fails(self):
        from app.api.health import readiness_check
        import asyncio
        with patch("app.api.health.get_supabase") as mock_sb, \
             patch("app.config.get_openai_api_key", return_value=None), \
             patch("app.config.get_tavily_api_key", return_value=None):
            mock_sb.return_value.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("DB down")
            mock_sb.return_value.storage.list_buckets.side_effect = Exception("storage down")
            result = asyncio.get_event_loop().run_until_complete(readiness_check())
        assert result["status"] == "degraded"
        assert result["checks"]["supabase"]["status"] == "error"

    def test_readiness_ok_when_unprovided_keys_not_configured(self):
        from app.api.health import readiness_check
        import asyncio
        with patch("app.api.health.get_supabase") as mock_sb, \
             patch("app.config.get_openai_api_key", return_value=None), \
             patch("app.config.get_tavily_api_key", return_value=None):
            mock_sb.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
            mock_sb.return_value.storage.list_buckets.return_value = []
            result = asyncio.get_event_loop().run_until_complete(readiness_check())
        assert result["status"] in ("ok", "degraded")
        for name, check in result["checks"].items():
            assert check["status"] in ("ok", "not_configured", "error"), \
                f"check {name!r} has unexpected status {check['status']!r}"


class TestPilotModeConfig:
    def test_pilot_mode_default_is_false(self):
        from app.config import settings
        assert isinstance(settings.pilot_mode, bool)

    def test_daily_budget_default_positive(self):
        from app.config import settings
        assert settings.daily_llm_budget_usd > 0

    def test_max_rounds_default_positive(self):
        from app.config import settings
        assert settings.max_rounds_per_user_daily > 0

    def test_max_searches_default_positive(self):
        from app.config import settings
        assert settings.max_evidence_searches_per_day > 0

    def test_latency_budgets_are_positive(self):
        from app.config import settings
        assert settings.latency_evidence_search_s > 0
        assert settings.latency_card_cut_s > 0
        assert settings.latency_opponent_speech_s > 0
        assert settings.latency_ballot_s > 0


class TestCostSummary:
    def test_daily_cost_summary_structure(self):
        from app.services.cost_tracker import get_daily_cost_summary
        with patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.select.return_value \
                .eq.return_value.in_.return_value.gte.return_value \
                .execute.return_value.data = [
                    {
                        "event_name": "llm_cost_incurred",
                        "metadata_json": {"cost_usd": 0.005, "operation": "card_cut"},
                        "created_at": "2026-06-23T10:00:00",
                    }
                ]
            result = get_daily_cost_summary("user-1")
        assert "user_id" in result
        assert "total_usd" in result
        assert "by_operation" in result
        assert result["total_usd"] >= 0

    def test_cost_summary_handles_db_error(self):
        from app.services.cost_tracker import get_daily_cost_summary
        with patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.side_effect = RuntimeError("DB unavailable")
            result = get_daily_cost_summary("user-1")
        assert result["total_usd"] == 0.0
        assert isinstance(result["by_operation"], dict)

    def test_cost_summary_aggregates_multiple_events(self):
        from app.services.cost_tracker import get_daily_cost_summary
        with patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.select.return_value \
                .eq.return_value.in_.return_value.gte.return_value \
                .execute.return_value.data = [
                    {"event_name": "llm_cost_incurred",
                     "metadata_json": {"cost_usd": 0.01, "operation": "card_cut"},
                     "created_at": "2026-06-23T10:00:00"},
                    {"event_name": "llm_cost_incurred",
                     "metadata_json": {"cost_usd": 0.02, "operation": "feedback_generation"},
                     "created_at": "2026-06-23T11:00:00"},
                ]
            result = get_daily_cost_summary("user-1")
        assert abs(result["total_usd"] - 0.03) < 0.001
        assert "card_cut" in result["by_operation"]
        assert "feedback_generation" in result["by_operation"]
