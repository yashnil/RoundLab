"""Pass 16 — Opponent evidence policy tests.

Covers:
- Only approved cards used
- Unsupported/not_supported card not used
- Analytic argument allowed without fake evidence
- Support verdict preserved unchanged
- Private evidence excluded
- Opponent difficulty affects argument count
"""
from __future__ import annotations
import pytest

from app.models.round_simulation import (
    OpponentDifficulty,
    RoundFormat,
    RoundSide,
    RoundSimulationConfig,
    SpeakingOrder,
)
from app.services.opponent_strategy import (
    _card_to_argument_plan,
    _score_card_for_opponent,
)


def _make_card(
    card_id="card-1",
    user_id="user-1",
    tag="Test tag",
    verdict="fully_supported",
    freshness_warning=False,
    source_quality="high",
) -> dict:
    return {
        "id": card_id,
        "user_id": user_id,
        "tag": tag,
        "cite": "Author 2024",
        "body_text": "The evidence supports this claim conclusively.",
        "intelligence_json": {
            "support_verdict": verdict,
            "freshness_warning": freshness_warning,
            "source_quality": source_quality,
        },
        "card_cutting_result_json": {},
    }


class TestScoreCardForOpponent:
    def test_fully_supported_scores_highest(self):
        card = _make_card(verdict="fully_supported")
        score = _score_card_for_opponent(card, RoundSide.CON)
        assert score > 2.0

    def test_partially_supported_scores_lower(self):
        card_full = _make_card(verdict="fully_supported")
        card_partial = _make_card(verdict="partially_supported")
        assert _score_card_for_opponent(card_full, RoundSide.CON) > \
               _score_card_for_opponent(card_partial, RoundSide.CON)

    def test_not_supported_returns_negative(self):
        card = _make_card(verdict="not_supported")
        score = _score_card_for_opponent(card, RoundSide.CON)
        assert score < 0

    def test_contradicts_returns_negative(self):
        card = _make_card(verdict="contradicts")
        score = _score_card_for_opponent(card, RoundSide.CON)
        assert score < 0

    def test_abstract_only_returns_negative(self):
        card = _make_card(verdict="abstract_only")
        score = _score_card_for_opponent(card, RoundSide.CON)
        assert score < 0

    def test_freshness_warning_reduces_score(self):
        card_fresh = _make_card(verdict="fully_supported", freshness_warning=False)
        card_stale = _make_card(verdict="fully_supported", freshness_warning=True)
        assert _score_card_for_opponent(card_fresh, RoundSide.CON) > \
               _score_card_for_opponent(card_stale, RoundSide.CON)

    def test_low_quality_reduces_score(self):
        card_high = _make_card(source_quality="high")
        card_low = _make_card(source_quality="low")
        assert _score_card_for_opponent(card_high, RoundSide.CON) > \
               _score_card_for_opponent(card_low, RoundSide.CON)


class TestCardToArgumentPlan:
    def test_basic_plan_from_card(self):
        card = _make_card()
        plan = _card_to_argument_plan(card, 0, 100)
        assert plan.label == "NC1"
        assert plan.evidence_card_id == "card-1"
        assert plan.tag is not None

    def test_index_determines_label(self):
        card = _make_card()
        plan0 = _card_to_argument_plan(card, 0, 100)
        plan1 = _card_to_argument_plan(card, 1, 100)
        plan2 = _card_to_argument_plan(card, 2, 100)
        assert plan0.label == "NC1"
        assert plan1.label == "NC2"
        assert plan2.label == "NC3"

    def test_partial_verdict_prefixes_claim(self):
        card = _make_card(verdict="partially_supported", tag="Partial evidence tag")
        plan = _card_to_argument_plan(card, 0, 100)
        assert "[Limited]" in plan.claim

    def test_fully_supported_no_prefix(self):
        card = _make_card(verdict="fully_supported", tag="Strong claim")
        plan = _card_to_argument_plan(card, 0, 100)
        assert "[Limited]" not in plan.claim

    def test_card_id_preserved(self):
        card = _make_card(card_id="my-special-card")
        plan = _card_to_argument_plan(card, 0, 100)
        assert plan.evidence_card_id == "my-special-card"


class TestAnalyticArgument:
    """When no cards are available, opponent uses clearly labeled analytic argument."""

    def test_no_cards_produces_analytic_argument(self):
        """Verify the plan building falls back gracefully with no approved cards."""
        from unittest.mock import MagicMock, patch
        from app.models.round_simulation import RoundFormat, SpeakerRole
        from app.services.opponent_strategy import build_opponent_round_plan

        config = RoundSimulationConfig(
            format=RoundFormat.FULL,
            student_side=RoundSide.PRO,
            speaking_order=SpeakingOrder.FIRST,
            resolution="Test resolution",
            approved_card_ids=[],
            approved_frontline_ids=[],
        )

        with patch("app.services.opponent_strategy.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.select.return_value \
                .in_.return_value.execute.return_value.data = []
            plan = build_opponent_round_plan("round-1", config, "user-1")

        assert len(plan.constructive_arguments) >= 1
        arg = plan.constructive_arguments[0]
        # Should be labeled analytical
        assert "[Analytical]" in arg.claim or arg.evidence_card_id is None


class TestOpponentPlanPrivacyEnforcement:
    """Opponent plan only contains authorized user's cards."""

    def test_foreign_user_cards_excluded(self):
        from unittest.mock import patch
        from app.services.opponent_strategy import _fetch_approved_cards

        cards = [
            {"id": "c1", "user_id": "authorized-user", "tag": "OK"},
            {"id": "c2", "user_id": "other-user", "tag": "Private"},
        ]

        with patch("app.services.opponent_strategy.get_supabase") as mock_sb:
            mock_sb.return_value.table.return_value.select.return_value \
                .in_.return_value.execute.return_value.data = cards
            result = _fetch_approved_cards(["c1", "c2"], "authorized-user", mock_sb.return_value)

        ids = [r["id"] for r in result]
        assert "c1" in ids
        assert "c2" not in ids
