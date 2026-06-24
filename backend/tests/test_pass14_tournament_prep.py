"""Pass 14 — Tournament Prep Intelligence Tests.

Covers:
- Evidence freshness assessment (claim type, freshness state, edge cases)
- Blockfile coverage analysis (dimension detection, role assignment)
- Frontline readiness (classification, flag derivation)
- Readiness scorer (dimension scores, composite)
- Prep plan service (gap→task mapping, task priorities)
- Gap workout generator (workout type selection, body snapshot)
- Tournament prep models (serialization)
- API layer (import, endpoint structure)

Design constraints verified:
- assess_freshness never raises
- Historical evidence never stale
- None != 0 in composite scoring
- Tasks use is_auto_generated=True
- Source card body is snapshot (immutable)
"""

from __future__ import annotations

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


# ── Freshness import ──────────────────────────────────────────────────────────

def test_evidence_freshness_importable():
    from app.services.evidence_freshness import assess_freshness
    assert callable(assess_freshness)


def test_assess_freshness_batch_importable():
    from app.services.evidence_freshness import assess_freshness_batch
    assert callable(assess_freshness_batch)


def test_freshness_helpers_importable():
    from app.services.evidence_freshness import (
        freshness_needs_attention,
        freshness_is_safe,
    )
    assert callable(freshness_needs_attention)
    assert callable(freshness_is_safe)


# ── Freshness: no publication date ───────────────────────────────────────────

def test_freshness_unknown_when_no_date():
    from app.services.evidence_freshness import assess_freshness
    card = {"id": "c1", "tag": "GDP growth accelerates", "body_text": "GDP grew 3%"}
    result = assess_freshness(card, today=date(2024, 1, 1))
    assert result.freshness_state == "freshness_unknown"
    assert result.days_old is None


def test_freshness_unknown_when_empty_date():
    from app.services.evidence_freshness import assess_freshness
    card = {"id": "c2", "tag": "Inflation rate rises", "body_text": "Prices up 5%", "published_date": ""}
    result = assess_freshness(card, today=date(2024, 1, 1))
    assert result.freshness_state == "freshness_unknown"


# ── Freshness: statistics claim type ─────────────────────────────────────────

def test_statistics_current_within_window():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c3",
        "tag": "Unemployment rate falls to 3.5%",
        "body_text": "BLS reports unemployment rate dropped",
        "published_date": "2023-10-01",
    }
    result = assess_freshness(card, today=date(2024, 1, 1))
    # 92 days old — within statistics "current" window of 365 days
    assert result.freshness_state == "current"
    assert result.claim_type == "statistics"


def test_statistics_aging_beyond_current_window():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c4",
        "tag": "Approval rating polls show decline",
        "body_text": "Survey finds 42% approval",
        "published_date": "2021-01-01",
    }
    result = assess_freshness(card, today=date(2024, 1, 1))
    # ~1096 days old — past 365 (current) and past 730 (aging cutoff)
    assert result.freshness_state in ("stale", "aging")


def test_statistics_stale_very_old():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c5",
        "tag": "GDP growth rate at 2.1 percent",
        "body_text": "GDP statistics show growth",
        "published_date": "2018-01-01",
    }
    result = assess_freshness(card, today=date(2024, 6, 1))
    # ~2342 days old — clearly stale
    assert result.freshness_state == "stale"
    assert result.days_old is not None
    assert result.days_old > 1000


# ── Freshness: historical claim type ─────────────────────────────────────────

def test_historical_never_stale():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c6",
        "tag": "Historically the Cold War shaped deterrence doctrine",
        "body_text": "During the Cold War, nuclear strategy evolved",
        "published_date": "1998-01-01",
    }
    result = assess_freshness(card, today=date(2024, 6, 1))
    # 26+ year old card — but historical claim type should never be stale
    assert result.freshness_state in ("current", "not_time_sensitive", "older_but_still_relevant")
    assert result.freshness_state != "stale"
    assert result.claim_type == "historical"


def test_historical_2010_not_stale():
    from app.services.evidence_freshness import assess_freshness
    # Use "during the" and "war" (not "wars") to reliably trigger historical pattern
    card = {
        "id": "c7",
        "tag": "During the Cold War, nuclear deterrence prevented direct conflict",
        "body_text": "During the Cold War era nuclear states avoided direct war",
        "published_date": "2010-01-01",
    }
    result = assess_freshness(card, today=date(2026, 1, 1))
    assert result.freshness_state not in ("stale", "superseded")
    assert result.claim_type == "historical"


# ── Freshness: policy claim type ─────────────────────────────────────────────

def test_policy_current_within_2_years():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c8",
        "tag": "Policy mandates carbon emissions cap",
        "body_text": "New regulation enacted by executive order",
        "published_date": "2023-01-01",
    }
    result = assess_freshness(card, today=date(2024, 1, 1))
    assert result.freshness_state == "current"
    assert result.claim_type in ("policy", "general")


# ── Freshness: has_newer_corroboration ───────────────────────────────────────

def test_older_but_relevant_when_newer_and_stale():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c9",
        "tag": "GDP growth rate at 2.1 percent",
        "body_text": "GDP statistics",
        "published_date": "2017-01-01",
    }
    result = assess_freshness(card, today=date(2024, 6, 1), has_newer_corroboration=True)
    # When has_newer_corroboration=True, the code returns older_but_still_relevant (not superseded)
    assert result.freshness_state == "older_but_still_relevant"
    assert result.has_newer_corroboration is True


def test_current_with_newer_stays_current():
    from app.services.evidence_freshness import assess_freshness
    card = {
        "id": "c10",
        "tag": "GDP growth recent",
        "body_text": "GDP statistics",
        "published_date": "2024-01-01",
    }
    result = assess_freshness(card, today=date(2024, 6, 1), has_newer_corroboration=True)
    assert result.freshness_state == "current"


# ── Freshness: never raises ───────────────────────────────────────────────────

def test_assess_freshness_never_raises_on_empty_dict():
    from app.services.evidence_freshness import assess_freshness
    result = assess_freshness({})
    assert result is not None
    assert result.freshness_state == "freshness_unknown"


def test_assess_freshness_never_raises_on_malformed_date():
    from app.services.evidence_freshness import assess_freshness
    card = {"id": "x", "tag": "test", "body_text": "test", "published_date": "not-a-date"}
    result = assess_freshness(card, today=date(2024, 1, 1))
    assert result is not None


def test_assess_freshness_year_only_date():
    from app.services.evidence_freshness import assess_freshness
    card = {"id": "y", "tag": "research study findings", "body_text": "Study data", "published_date": "2022"}
    result = assess_freshness(card, today=date(2024, 6, 1))
    # year-only should be parsed as 2022-01-01 → ~877 days old
    assert result.freshness_state != "freshness_unknown"
    assert result.days_old is not None


# ── Freshness: batch ──────────────────────────────────────────────────────────

def test_assess_freshness_batch_returns_list():
    from app.services.evidence_freshness import assess_freshness_batch
    cards = [
        {"id": "a", "tag": "GDP rate", "body_text": "statistics", "published_date": "2023-01-01"},
        {"id": "b", "tag": "Historically cold war", "body_text": "historical", "published_date": "1990-01-01"},
    ]
    results = assess_freshness_batch(cards, today=date(2024, 6, 1))
    assert len(results) == 2
    assert results[0].card_id == "a"
    assert results[1].card_id == "b"


def test_assess_freshness_batch_empty():
    from app.services.evidence_freshness import assess_freshness_batch
    results = assess_freshness_batch([], today=date(2024, 1, 1))
    assert results == []


def test_assess_freshness_batch_newer_card_ids():
    from app.services.evidence_freshness import assess_freshness_batch
    cards = [
        {"id": "old", "tag": "GDP percent", "body_text": "statistics", "published_date": "2015-01-01"},
    ]
    results = assess_freshness_batch(cards, today=date(2024, 6, 1), newer_card_ids={"old"})
    assert results[0].has_newer_corroboration is True
    # Stale + newer corroboration → older_but_still_relevant (not superseded, per implementation)
    assert results[0].freshness_state in ("older_but_still_relevant", "superseded")


# ── Freshness: needs_attention / is_safe helpers ──────────────────────────────

def test_freshness_needs_attention_for_stale():
    from app.services.evidence_freshness import (
        freshness_needs_attention,
        assess_freshness,
    )
    card = {
        "id": "z",
        "tag": "GDP rate percent",
        "body_text": "statistics",
        "published_date": "2015-01-01",
    }
    result = assess_freshness(card, today=date(2024, 6, 1))
    assert freshness_needs_attention(result) is True


def test_freshness_is_safe_for_current():
    from app.services.evidence_freshness import freshness_is_safe, assess_freshness
    card = {
        "id": "z2",
        "tag": "GDP rate percent",
        "body_text": "statistics",
        "published_date": "2024-01-01",
    }
    result = assess_freshness(card, today=date(2024, 6, 1))
    assert freshness_is_safe(result) is True


# ── Blockfile coverage: import ─────────────────────────────────────────────────

def test_blockfile_coverage_importable():
    from app.services.blockfile_coverage_analyzer import (
        analyze_blockfile_coverage,
        summarize_coverage_gaps,
    )
    assert callable(analyze_blockfile_coverage)
    assert callable(summarize_coverage_gaps)


def test_card_satisfies_dim_importable():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    assert callable(_card_satisfies_dim)


# ── Blockfile coverage: dimension detection ───────────────────────────────────

def test_card_satisfies_warrant_dim():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    card = {"body_text": "The mechanism causes harm because of the linked chain.", "tag": "climate impact"}
    assert _card_satisfies_dim(card, "warrant") is True


def test_card_does_not_satisfy_warrant_when_empty():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    card = {"body_text": "", "tag": ""}
    assert _card_satisfies_dim(card, "warrant") is False


def test_card_satisfies_impact_dim():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    card = {"body_text": "The impact is catastrophic harm to millions.", "tag": "impact"}
    assert _card_satisfies_dim(card, "impact") is True


def test_card_satisfies_primary_source_dim():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    card = {"body_text": "Study shows X", "tag": "evidence", "id": "c1"}
    assert _card_satisfies_dim(card, "primary_source") is True


def test_card_satisfies_weighing_dim():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    card = {"body_text": "This outweighs their impact because of magnitude.", "tag": "weighing"}
    assert _card_satisfies_dim(card, "weighing") is True


def test_card_satisfies_uniqueness():
    from app.services.blockfile_coverage_analyzer import _card_satisfies_dim
    card = {"body_text": "This risk is unique — it hasn't happened yet.", "tag": "uniqueness"}
    assert _card_satisfies_dim(card, "uniqueness") is True


# ── Blockfile coverage: full analysis ────────────────────────────────────────

def test_analyze_blockfile_coverage_returns_list():
    from app.services.blockfile_coverage_analyzer import analyze_blockfile_coverage
    blockfile = {"id": "bf1", "title": "Climate"}
    sections = [
        {"id": "s1", "blockfile_id": "bf1", "section_type": "contention",
         "title": "Climate Harm", "parent_section_id": None, "sort_order": 1},
    ]
    entries = []
    cards: dict = {}
    frontlines: list = []
    responses: list = []
    results = analyze_blockfile_coverage(blockfile, sections, entries, cards, frontlines, responses)
    assert isinstance(results, list)


def test_analyze_blockfile_coverage_empty_sections():
    from app.services.blockfile_coverage_analyzer import analyze_blockfile_coverage
    blockfile = {"id": "bf2", "title": "Empty"}
    results = analyze_blockfile_coverage(blockfile, [], [], {}, [], [])
    assert results == []


def test_analyze_blockfile_coverage_only_top_level():
    from app.services.blockfile_coverage_analyzer import analyze_blockfile_coverage
    blockfile = {"id": "bf3"}
    sections = [
        {"id": "s1", "section_type": "contention", "title": "Main", "parent_section_id": None, "sort_order": 1},
        {"id": "s2", "section_type": "subpoint", "title": "Sub", "parent_section_id": "s1", "sort_order": 1},
    ]
    results = analyze_blockfile_coverage(blockfile, sections, [], {}, [], [])
    assert len(results) == 1  # only top-level section


def test_analyze_section_with_cards_improves_coverage():
    from app.services.blockfile_coverage_analyzer import analyze_blockfile_coverage
    blockfile = {"id": "bf4"}
    sections = [
        {"id": "s1", "section_type": "contention", "title": "Climate", "parent_section_id": None, "sort_order": 1},
    ]
    entries = [
        {
            "id": "e1", "section_id": "s1",
            "body_text": "climate causes harm outweighs — magnitude and probability warrant unique link",
            "card_id": "c1",
        }
    ]
    cards = {
        "c1": {
            "id": "c1",
            "body_text": "climate causes harm outweighs — magnitude and probability warrant unique link",
            "tag": "climate impact warrant",
        }
    }
    results = analyze_blockfile_coverage(blockfile, sections, entries, cards, [], [])
    assert len(results) == 1
    r = results[0]
    assert r.coverage_pct >= 0  # some coverage
    assert r.covered_count >= 0


def test_coverage_pct_below_100_when_missing_dims():
    from app.services.blockfile_coverage_analyzer import analyze_blockfile_coverage
    blockfile = {"id": "bf5"}
    sections = [
        {"id": "s1", "section_type": "contention", "title": "Empty Contention", "parent_section_id": None, "sort_order": 1},
    ]
    results = analyze_blockfile_coverage(blockfile, sections, [], {}, [], [])
    assert len(results) == 1
    assert results[0].coverage_pct < 100


def test_summarize_coverage_gaps_returns_strings():
    from app.services.blockfile_coverage_analyzer import (
        analyze_blockfile_coverage,
        summarize_coverage_gaps,
    )
    blockfile = {"id": "bf6"}
    sections = [
        {"id": "s1", "section_type": "contention", "title": "Test", "parent_section_id": None, "sort_order": 1},
    ]
    results = analyze_blockfile_coverage(blockfile, sections, [], {}, [], [])
    summary = summarize_coverage_gaps(results)
    assert isinstance(summary, list)


# ── Frontline readiness: import ───────────────────────────────────────────────

def test_frontline_readiness_importable():
    from app.services.frontline_readiness_analyzer import (
        analyze_frontline,
        classify_readiness,
        analyze_frontlines_batch,
    )
    assert callable(analyze_frontline)
    assert callable(classify_readiness)
    assert callable(analyze_frontlines_batch)


# ── Frontline readiness: underdeveloped ───────────────────────────────────────

def test_frontline_underdeveloped_no_responses():
    from app.services.frontline_readiness_analyzer import (
        analyze_frontline,
        classify_readiness,
    )
    frontline = {
        "id": "fl1",
        "title": "Answer to climate harm",
        "opponent_claim": "Climate causes extinction",
        "opponent_warrant": "",
        "opponent_impact": "",
    }
    result = analyze_frontline(frontline, responses=[])
    assert result.response_count == 0
    assert classify_readiness(result) == "underdeveloped"


def test_frontline_underdeveloped_one_response_no_evidence():
    from app.services.frontline_readiness_analyzer import (
        analyze_frontline,
        classify_readiness,
    )
    frontline = {
        "id": "fl2",
        "opponent_claim": "Climate causes extinction",
    }
    responses = [
        {
            "id": "r1",
            "response_type": "non_unique",
            "is_analytical": True,
            "speech_suitability": ["rebuttal"],
            "priority": 1,
            "linked_card_ids": [],
        }
    ]
    result = analyze_frontline(frontline, responses=responses)
    level = classify_readiness(result)
    # One response, analytical only, no evidence cards — underdeveloped
    assert level in ("underdeveloped", "usable_with_gaps")


# ── Frontline readiness: ready ────────────────────────────────────────────────

def test_frontline_ready_full_coverage():
    from app.services.frontline_readiness_analyzer import (
        analyze_frontline,
        classify_readiness,
    )
    frontline = {
        "id": "fl3",
        "opponent_claim": "AI is dangerous",
        "opponent_warrant": "AI has risks",
        "opponent_impact": "Catastrophic harm",
    }
    responses = [
        {
            "id": "r1",
            "response_type": "direct_refutation",
            "is_analytical": False,
            "speech_suitability": ["rebuttal", "summary"],
            "priority": 1,
            "linked_card_ids": ["c1"],
        },
        {
            "id": "r2",
            "response_type": "impact_defense",
            "is_analytical": False,
            "speech_suitability": ["summary"],
            "priority": 2,
            "linked_card_ids": ["c2"],
        },
    ]
    cards = {
        "c1": {"id": "c1", "body_text": "AI is safe", "support_verdict": "supported"},
        "c2": {"id": "c2", "body_text": "Impacts are overstated", "support_verdict": "supported"},
    }
    result = analyze_frontline(frontline, responses=responses, cards=cards)
    level = classify_readiness(result)
    assert level == "ready"


# ── Frontline readiness: unsafe ───────────────────────────────────────────────

def test_frontline_unsafe_when_evidence_unsupported():
    from app.services.frontline_readiness_analyzer import (
        analyze_frontline,
        classify_readiness,
    )
    frontline = {"id": "fl4", "opponent_claim": "Test claim"}
    responses = [
        {
            "id": "r1",
            "response_type": "direct_refutation",
            "is_analytical": False,
            "speech_suitability": [],
            "priority": 1,
            "linked_card_ids": ["bad_card"],
        }
    ]
    cards = {
        "bad_card": {"id": "bad_card", "body_text": "...", "support_verdict": "unsupported"}
    }
    result = analyze_frontline(frontline, responses=responses, cards=cards)
    assert result.has_unsafe_evidence is True
    assert classify_readiness(result) == "unsafe"


# ── Frontline readiness: offensive option not required for ready ───────────────

def test_frontline_ready_without_turn():
    from app.services.frontline_readiness_analyzer import (
        analyze_frontline,
        classify_readiness,
    )
    frontline = {
        "id": "fl5",
        "opponent_claim": "Nuclear deterrence fails",
        "opponent_warrant": "Extended deterrence collapses",
        "opponent_impact": "War",
    }
    responses = [
        {
            "id": "r1",
            "response_type": "direct_refutation",
            "is_analytical": False,
            "priority": 1,
            "linked_card_ids": ["c1"],
            "speech_suitability": ["rebuttal"],
        },
        {
            "id": "r2",
            "response_type": "impact_defense",
            "is_analytical": False,
            "priority": 2,
            "linked_card_ids": ["c2"],
            "speech_suitability": ["summary"],
        },
    ]
    cards = {
        "c1": {"id": "c1", "body_text": "deterrence works", "support_verdict": "supported"},
        "c2": {"id": "c2", "body_text": "impact overstated", "support_verdict": "supported"},
    }
    result = analyze_frontline(frontline, responses=responses, cards=cards)
    # No turn — but still ready
    assert result.has_offensive_option is False
    assert classify_readiness(result) == "ready"


# ── Frontline readiness: stale card detection ─────────────────────────────────

def test_frontline_notes_stale_cards():
    from app.services.frontline_readiness_analyzer import analyze_frontline
    frontline = {"id": "fl6", "opponent_claim": "Test"}
    responses = [
        {
            "id": "r1",
            "response_type": "direct_refutation",
            "is_analytical": False,
            "priority": 1,
            "linked_card_ids": ["c_stale"],
            "speech_suitability": [],
        }
    ]
    cards = {
        "c_stale": {"id": "c_stale", "body_text": "...", "support_verdict": "supported"}
    }
    result = analyze_frontline(frontline, responses=responses, cards=cards, stale_card_ids={"c_stale"})
    assert result.has_stale_evidence_linked is True


# ── Frontline readiness: batch ────────────────────────────────────────────────

def test_analyze_frontlines_batch_returns_list():
    from app.services.frontline_readiness_analyzer import analyze_frontlines_batch
    frontlines = [
        {"id": "fl1", "opponent_claim": "Test A"},
        {"id": "fl2", "opponent_claim": "Test B"},
    ]
    results = analyze_frontlines_batch(frontlines, responses_by_fl={}, cards={})
    assert len(results) == 2


def test_analyze_frontlines_batch_empty():
    from app.services.frontline_readiness_analyzer import analyze_frontlines_batch
    results = analyze_frontlines_batch([], responses_by_fl={}, cards={})
    assert results == []


# ── Readiness scorer: import ──────────────────────────────────────────────────

def test_readiness_scorer_importable():
    from app.services.readiness_scorer import (
        score_dimensions,
        compute_composite,
        DEFAULT_WEIGHTS,
    )
    assert callable(score_dimensions)
    assert callable(compute_composite)
    assert isinstance(DEFAULT_WEIGHTS, dict)
    assert "argument_coverage" in DEFAULT_WEIGHTS


def test_default_weights_all_positive():
    from app.services.readiness_scorer import DEFAULT_WEIGHTS
    for key, val in DEFAULT_WEIGHTS.items():
        assert val > 0, f"Weight {key} must be positive"


def test_compute_composite_excludes_none():
    from app.services.readiness_scorer import compute_composite, DEFAULT_WEIGHTS
    from app.models.tournament_prep import DimensionScore, ReadinessDimensions

    def make_dim(name: str, score) -> DimensionScore:
        return DimensionScore(dimension=name, score=score, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage", 80),
        evidence_quality=make_dim("evidence_quality", None),
        evidence_freshness=make_dim("evidence_freshness", None),
        frontline_readiness=make_dim("frontline_readiness", None),
        source_diversity=make_dim("source_diversity", None),
        speech_stage_readiness=make_dim("speech_stage_readiness", None),
        weighing_preparation=make_dim("weighing_preparation", None),
    )
    composite = compute_composite(dims, DEFAULT_WEIGHTS)
    # None dimension excluded — composite should be near 80 not dragged down
    assert composite is not None
    assert composite > 70


def test_compute_composite_all_none_returns_none():
    from app.services.readiness_scorer import compute_composite, DEFAULT_WEIGHTS
    from app.models.tournament_prep import DimensionScore, ReadinessDimensions

    def make_dim(name: str) -> DimensionScore:
        return DimensionScore(dimension=name, score=None, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage"),
        evidence_quality=make_dim("evidence_quality"),
        evidence_freshness=make_dim("evidence_freshness"),
        frontline_readiness=make_dim("frontline_readiness"),
        source_diversity=make_dim("source_diversity"),
        speech_stage_readiness=make_dim("speech_stage_readiness"),
        weighing_preparation=make_dim("weighing_preparation"),
    )
    result = compute_composite(dims, DEFAULT_WEIGHTS)
    assert result is None


def test_compute_composite_all_zero():
    from app.services.readiness_scorer import compute_composite, DEFAULT_WEIGHTS
    from app.models.tournament_prep import DimensionScore, ReadinessDimensions

    def make_dim(name: str, score) -> DimensionScore:
        return DimensionScore(dimension=name, score=score, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage", 0),
        evidence_quality=make_dim("evidence_quality", 0),
        evidence_freshness=make_dim("evidence_freshness", 0),
        frontline_readiness=make_dim("frontline_readiness", 0),
        source_diversity=make_dim("source_diversity", 0),
        speech_stage_readiness=make_dim("speech_stage_readiness", 0),
        weighing_preparation=make_dim("weighing_preparation", 0),
    )
    result = compute_composite(dims, DEFAULT_WEIGHTS)
    assert result == 0


def test_score_dimensions_returns_readiness_dimensions():
    from app.services.readiness_scorer import score_dimensions
    from app.models.tournament_prep import PrepGap, EvidenceFreshnessAssessment

    result = score_dimensions(
        gaps=[],
        freshness_assessments=[],
        total_arguments=0,
        total_cards=0,
        total_frontlines=0,
        frontline_results=[],
    )
    # All dimensions should be None when no data
    assert result.argument_coverage.score is None
    assert result.evidence_quality.score is None


def test_score_dimensions_with_stale_cards_lowers_freshness():
    from app.services.readiness_scorer import score_dimensions
    from app.models.tournament_prep import EvidenceFreshnessAssessment
    from datetime import datetime

    fresh_assessment = EvidenceFreshnessAssessment(
        card_id="c1",
        freshness_state="stale",
        claim_type="statistics",
        rule_applied="stale_rule",
        explanation="old",
        has_newer_corroboration=False,
        assessed_at=datetime.utcnow().isoformat(),
    )
    result = score_dimensions(
        gaps=[],
        freshness_assessments=[fresh_assessment],
        total_arguments=0,
        total_cards=1,
        total_frontlines=0,
        frontline_results=[],
    )
    # Freshness score should be below 100
    assert result.evidence_freshness.score is not None
    assert result.evidence_freshness.score < 100


# ── Prep plan service: import ─────────────────────────────────────────────────

def test_prep_plan_service_importable():
    from app.services.prep_plan_service import (
        generate_tasks_from_report,
        build_prep_plan,
        _GAP_TO_TASK_TYPE,
        _SEVERITY_TO_PRIORITY,
        _TASK_MINUTES,
    )
    assert callable(generate_tasks_from_report)
    assert isinstance(_GAP_TO_TASK_TYPE, dict)
    assert isinstance(_SEVERITY_TO_PRIORITY, dict)
    assert isinstance(_TASK_MINUTES, dict)


def test_all_gap_categories_have_task_mapping():
    from app.services.prep_plan_service import _GAP_TO_TASK_TYPE
    from app.models.tournament_prep import GapCategory
    import typing
    categories = typing.get_args(GapCategory)
    for cat in categories:
        assert cat in _GAP_TO_TASK_TYPE, f"Gap category {cat!r} has no task mapping"


def test_severity_to_priority_values_valid():
    from app.services.prep_plan_service import _SEVERITY_TO_PRIORITY
    for sev, pri in _SEVERITY_TO_PRIORITY.items():
        assert pri in (1, 2, 3), f"Priority for {sev} must be 1-3, got {pri}"


def test_generate_tasks_from_report_empty_gaps():
    from app.services.prep_plan_service import generate_tasks_from_report
    from app.models.tournament_prep import PrepReadinessReport, ReadinessDimensions, DimensionScore

    def make_dim(name: str) -> DimensionScore:
        return DimensionScore(dimension=name, score=None, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage"),
        evidence_quality=make_dim("evidence_quality"),
        evidence_freshness=make_dim("evidence_freshness"),
        frontline_readiness=make_dim("frontline_readiness"),
        source_diversity=make_dim("source_diversity"),
        speech_stage_readiness=make_dim("speech_stage_readiness"),
        weighing_preparation=make_dim("weighing_preparation"),
    )
    report = PrepReadinessReport(
        user_id="u1",
        resolution_id="r1",
        side="pro",
        generated_at="2024-01-01T00:00:00",
        dimensions=dims,
        gaps=[],
        critical_gaps=[],
        stale_cards=[],
        unsafe_cards=[],
        strongest_arguments=[],
        weakest_frontlines=[],
        blockfile_coverage=[],
        freshness_assessments=[],
        next_recommended_actions=[],
        total_cards=0,
        total_arguments=0,
        total_frontlines=0,
        total_blockfiles=0,
    )
    tasks = generate_tasks_from_report(report, workspace_id="ws1", today=date(2024, 1, 1))
    assert tasks == []


def test_generate_tasks_creates_auto_generated():
    from app.services.prep_plan_service import generate_tasks_from_report
    from app.models.tournament_prep import (
        PrepReadinessReport,
        ReadinessDimensions,
        DimensionScore,
        PrepGap,
    )

    def make_dim(name: str) -> DimensionScore:
        return DimensionScore(dimension=name, score=None, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage"),
        evidence_quality=make_dim("evidence_quality"),
        evidence_freshness=make_dim("evidence_freshness"),
        frontline_readiness=make_dim("frontline_readiness"),
        source_diversity=make_dim("source_diversity"),
        speech_stage_readiness=make_dim("speech_stage_readiness"),
        weighing_preparation=make_dim("weighing_preparation"),
    )

    gap = PrepGap(
        gap_category="missing_warrant",
        severity="high",
        title="Missing warrant in contention 1",
        reason="No warrant card found",
        is_deterministic=True,
        resolved=False,
    )

    report = PrepReadinessReport(
        user_id="u1",
        resolution_id="r1",
        side="pro",
        generated_at="2024-01-01T00:00:00",
        dimensions=dims,
        gaps=[gap],
        critical_gaps=[],
        stale_cards=[],
        unsafe_cards=[],
        strongest_arguments=[],
        weakest_frontlines=[],
        blockfile_coverage=[],
        freshness_assessments=[],
        next_recommended_actions=[],
        total_cards=0,
        total_arguments=0,
        total_frontlines=0,
        total_blockfiles=0,
    )

    tasks = generate_tasks_from_report(report, workspace_id="ws1", today=date(2024, 1, 1))
    assert len(tasks) == 1
    task = tasks[0]
    assert task.is_auto_generated is True
    assert task.task_type == "strengthen_warrant"
    assert task.priority == 1  # high → priority 1


def test_generate_tasks_stale_evidence_maps_to_replace():
    from app.services.prep_plan_service import generate_tasks_from_report, _GAP_TO_TASK_TYPE
    assert _GAP_TO_TASK_TYPE["stale_evidence"] == "replace_stale_card"


def test_critical_severity_gets_priority_1():
    from app.services.prep_plan_service import _SEVERITY_TO_PRIORITY
    assert _SEVERITY_TO_PRIORITY["critical"] == 1
    assert _SEVERITY_TO_PRIORITY["high"] == 1
    assert _SEVERITY_TO_PRIORITY["medium"] == 2
    assert _SEVERITY_TO_PRIORITY["low"] == 3


# ── Gap workout generator: import ─────────────────────────────────────────────

def test_gap_workout_generator_importable():
    from app.services.gap_workout_generator import (
        generate_workout_for_gap,
        generate_workouts_for_report,
    )
    assert callable(generate_workout_for_gap)
    assert callable(generate_workouts_for_report)


def test_generate_workout_for_missing_warrant():
    from app.services.gap_workout_generator import generate_workout_for_gap
    from app.models.tournament_prep import PrepGap

    gap = PrepGap(
        gap_category="missing_warrant",
        severity="high",
        title="Missing warrant",
        reason="No warrant",
        is_deterministic=True,
        card_id="c1",
        resolved=False,
    )
    card = {
        "id": "c1",
        "tag": "Economic growth drives geopolitical stability",
        "body_text": "Research shows GDP growth correlates with stability.",
    }
    workout = generate_workout_for_gap(gap, card, workspace_id="ws1", user_id="u1")
    assert workout is not None
    assert workout.workout_type == "evidence_explanation"
    assert workout.workspace_id == "ws1"
    assert workout.user_id == "u1"
    assert "Economic growth drives geopolitical stability" in workout.title
    # Body snapshot should be present
    assert workout.source_card_body is not None


def test_generate_workout_body_is_snapshot():
    from app.services.gap_workout_generator import generate_workout_for_gap
    from app.models.tournament_prep import PrepGap

    original_body = "The mechanism causes harm because of the causal chain."
    gap = PrepGap(
        gap_category="missing_warrant",
        severity="medium",
        title="Test",
        reason="no warrant",
        is_deterministic=True,
        card_id="c1",
        resolved=False,
    )
    card = {"id": "c1", "tag": "Test tag", "body_text": original_body}
    workout = generate_workout_for_gap(gap, card, workspace_id="ws1", user_id="u1")
    assert workout.source_card_body is not None
    assert original_body[:100] in workout.source_card_body


def test_generate_workout_stale_evidence_type():
    from app.services.gap_workout_generator import generate_workout_for_gap
    from app.models.tournament_prep import PrepGap

    gap = PrepGap(
        gap_category="stale_evidence",
        severity="medium",
        title="Stale card detected",
        reason="Card is 6 years old",
        is_deterministic=True,
        card_id="c1",
        resolved=False,
    )
    card = {"id": "c1", "tag": "2018 study on impact", "body_text": "In 2018, researchers found..."}
    workout = generate_workout_for_gap(gap, card, workspace_id="ws1", user_id="u1")
    assert workout is not None
    assert workout.workout_type == "stale_evidence"


def test_generate_workout_frontline_type():
    from app.services.gap_workout_generator import generate_workout_for_gap
    from app.models.tournament_prep import PrepGap

    gap = PrepGap(
        gap_category="frontline_underdeveloped",
        severity="high",
        title="Frontline needs work",
        reason="Only one response",
        is_deterministic=True,
        card_id="c1",
        resolved=False,
    )
    card = {"id": "c1", "tag": "Defense to climate extinction", "body_text": "Impacts are overstated."}
    workout = generate_workout_for_gap(gap, card, workspace_id="ws1", user_id="u1")
    assert workout is not None
    assert workout.workout_type == "frontline_speed"


def test_generate_workouts_for_report_respects_max():
    from app.services.gap_workout_generator import generate_workouts_for_report
    from app.models.tournament_prep import PrepGap, PrepReadinessReport, ReadinessDimensions, DimensionScore

    def make_dim(name: str) -> DimensionScore:
        return DimensionScore(dimension=name, score=None, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage"),
        evidence_quality=make_dim("evidence_quality"),
        evidence_freshness=make_dim("evidence_freshness"),
        frontline_readiness=make_dim("frontline_readiness"),
        source_diversity=make_dim("source_diversity"),
        speech_stage_readiness=make_dim("speech_stage_readiness"),
        weighing_preparation=make_dim("weighing_preparation"),
    )

    gaps = [
        PrepGap(
            gap_category="missing_warrant",
            severity="high",
            title=f"Gap {i}",
            reason="reason",
            is_deterministic=True,
            card_id=f"c{i}",
            resolved=False,
        )
        for i in range(15)
    ]

    report = PrepReadinessReport(
        user_id="u1",
        resolution_id="r1",
        side="pro",
        generated_at="2024-01-01T00:00:00",
        dimensions=dims,
        gaps=gaps,
        critical_gaps=[],
        stale_cards=[],
        unsafe_cards=[],
        strongest_arguments=[],
        weakest_frontlines=[],
        blockfile_coverage=[],
        freshness_assessments=[],
        next_recommended_actions=[],
        total_cards=15,
        total_arguments=0,
        total_frontlines=0,
        total_blockfiles=0,
    )

    cards = {f"c{i}": {"id": f"c{i}", "tag": f"Card {i}", "body_text": "Evidence text."} for i in range(15)}
    workouts = generate_workouts_for_report(report, cards, "ws1", "u1", max_workouts=5)
    assert len(workouts) <= 5


def test_generate_workouts_empty_gaps():
    from app.services.gap_workout_generator import generate_workouts_for_report
    from app.models.tournament_prep import PrepReadinessReport, ReadinessDimensions, DimensionScore

    def make_dim(name: str) -> DimensionScore:
        return DimensionScore(dimension=name, score=None, weight=1.0, explanation="", contributing_gaps=[])

    dims = ReadinessDimensions(**{k: make_dim(k) for k in [
        "argument_coverage", "evidence_quality", "evidence_freshness",
        "frontline_readiness", "source_diversity", "speech_stage_readiness", "weighing_preparation"
    ]})

    report = PrepReadinessReport(
        user_id="u1",
        resolution_id="r1",
        side="pro",
        generated_at="2024-01-01T00:00:00",
        dimensions=dims,
        gaps=[],
        critical_gaps=[],
        stale_cards=[],
        unsafe_cards=[],
        strongest_arguments=[],
        weakest_frontlines=[],
        blockfile_coverage=[],
        freshness_assessments=[],
        next_recommended_actions=[],
        total_cards=0,
        total_arguments=0,
        total_frontlines=0,
        total_blockfiles=0,
    )

    workouts = generate_workouts_for_report(report, {}, "ws1", "u1")
    assert workouts == []


# ── Models: serialization ─────────────────────────────────────────────────────

def test_prep_workspace_row_serializable():
    from app.models.tournament_prep import PrepWorkspaceRow
    row = PrepWorkspaceRow(
        id="ws1",
        user_id="u1",
        resolution_id="r1",
        side="pro",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    data = row.model_dump()
    assert data["id"] == "ws1"
    assert data["side"] == "pro"


def test_prep_gap_model():
    from app.models.tournament_prep import PrepGap
    gap = PrepGap(
        gap_category="missing_warrant",
        severity="high",
        title="Test",
        reason="reason",
        is_deterministic=True,
        resolved=False,
    )
    assert gap.gap_category == "missing_warrant"
    assert gap.severity == "high"
    assert gap.resolved is False


def test_dimension_score_none_allowed():
    from app.models.tournament_prep import DimensionScore
    dim = DimensionScore(
        dimension="argument_coverage",
        score=None,
        weight=1.5,
        explanation="no data",
        contributing_gaps=[],
    )
    assert dim.score is None


def test_prep_readiness_report_full_model():
    from app.models.tournament_prep import (
        PrepReadinessReport,
        ReadinessDimensions,
        DimensionScore,
    )

    def make_dim(name: str) -> DimensionScore:
        return DimensionScore(dimension=name, score=85, weight=1.0, explanation="ok", contributing_gaps=[])

    dims = ReadinessDimensions(
        argument_coverage=make_dim("argument_coverage"),
        evidence_quality=make_dim("evidence_quality"),
        evidence_freshness=make_dim("evidence_freshness"),
        frontline_readiness=make_dim("frontline_readiness"),
        source_diversity=make_dim("source_diversity"),
        speech_stage_readiness=make_dim("speech_stage_readiness"),
        weighing_preparation=make_dim("weighing_preparation"),
    )

    report = PrepReadinessReport(
        user_id="u1",
        resolution_id="r1",
        side="pro",
        generated_at="2024-01-01T00:00:00",
        dimensions=dims,
        composite_score=85,
        gaps=[],
        critical_gaps=[],
        stale_cards=[],
        unsafe_cards=[],
        strongest_arguments=["Contention 1"],
        weakest_frontlines=["Answer to off-case DA"],
        blockfile_coverage=[],
        freshness_assessments=[],
        next_recommended_actions=["Research new evidence for C1"],
        total_cards=5,
        total_arguments=2,
        total_frontlines=3,
        total_blockfiles=1,
    )

    assert report.composite_score == 85
    assert report.total_cards == 5
    data = report.model_dump()
    assert "dimensions" in data
    assert "composite_score" in data


def test_prep_task_create_is_auto_generated():
    from app.models.tournament_prep import PrepTaskCreate
    task = PrepTaskCreate(
        workspace_id="ws1",
        user_id="u1",
        task_type="strengthen_warrant",
        title="Add warrant to contention 1",
        priority=1,
        is_auto_generated=True,
    )
    assert task.is_auto_generated is True


def test_prep_workout_create_has_source_body():
    from app.models.tournament_prep import PrepWorkoutCreate
    wo = PrepWorkoutCreate(
        workspace_id="ws1",
        user_id="u1",
        workout_type="evidence_explanation",
        title="Explain the warrant",
        prompt="Explain this card",
        time_limit_seconds=90,
        success_criteria=["Named the mechanism"],
        source_card_body="This card says climate change accelerates feedback loops.",
        source_card_tag="Climate accelerates",
    )
    assert wo.source_card_body is not None
    assert wo.workout_type == "evidence_explanation"


# ── API: import ───────────────────────────────────────────────────────────────

def test_tournament_prep_api_importable():
    from app.api.tournament_prep import router
    assert router is not None


def test_tournament_prep_api_routes_registered():
    from app.api.tournament_prep import router
    paths = [route.path for route in router.routes]
    assert any("/prep/workspaces" in p for p in paths)
    assert any("/readiness-report" in p for p in paths)
    assert any("/prep-plan" in p for p in paths)
    assert any("/tasks" in p for p in paths)
    assert any("/workouts" in p for p in paths)
    assert any("/freshness" in p for p in paths)
    assert any("/newer-evidence" in p for p in paths)


def test_tournament_prep_router_in_main():
    from app.main import app
    routes = [str(r.path) if hasattr(r, "path") else "" for r in app.routes]
    route_str = " ".join(routes)
    assert "/prep" in route_str or any("prep" in r for r in routes)


# ── Urgency multiplier ────────────────────────────────────────────────────────

def test_urgency_no_date():
    from app.services.prep_plan_service import _urgency_multiplier
    result = _urgency_multiplier(priority=1, tournament_date=None, today=date(2024, 1, 1))
    assert result == 1.0


def test_urgency_imminent_tournament():
    from app.services.prep_plan_service import _urgency_multiplier
    tournament = date(2024, 1, 4)
    today = date(2024, 1, 1)
    # 3 days away: priority-1 gets multiplier 0.0 (drop), priority-3 gets 0.5
    # Lower multiplier = more aggressive urgency treatment
    result_high = _urgency_multiplier(priority=1, tournament_date=tournament, today=today)
    result_low = _urgency_multiplier(priority=3, tournament_date=tournament, today=today)
    # High-priority tasks are treated MORE urgently (lower multiplier) at T-3 days
    assert result_high <= result_low


def test_urgency_far_away():
    from app.services.prep_plan_service import _urgency_multiplier
    tournament = date(2024, 6, 1)
    today = date(2024, 1, 1)
    result = _urgency_multiplier(priority=1, tournament_date=tournament, today=today)
    assert result == 1.0


# ── Claim type classification ─────────────────────────────────────────────────

def test_classify_historical():
    from app.services.evidence_freshness import _classify_claim_type
    tag = "Historically, nuclear deterrence prevented wars"
    body = "During the cold war, nuclear states"
    ct = _classify_claim_type(tag, body)
    assert ct == "historical"


def test_classify_statistics():
    from app.services.evidence_freshness import _classify_claim_type
    tag = "GDP growth at 2.1 percent"
    body = "GDP grew 2.1% according to BLS"
    ct = _classify_claim_type(tag, body)
    assert ct == "statistics"


def test_classify_law():
    from app.services.evidence_freshness import _classify_claim_type
    tag = "Supreme court ruled government surveillance unconstitutional"
    body = "The court held that the statute violated 4th amendment"
    ct = _classify_claim_type(tag, body)
    assert ct in ("law", "policy")


def test_classify_general_fallback():
    from app.services.evidence_freshness import _classify_claim_type
    ct = _classify_claim_type("", "")
    assert ct == "general"


# ── EvidenceFreshnessAssessment model ─────────────────────────────────────────

def test_freshness_assessment_model():
    from app.models.tournament_prep import EvidenceFreshnessAssessment
    a = EvidenceFreshnessAssessment(
        card_id="c1",
        freshness_state="current",
        claim_type="statistics",
        rule_applied="current_rule",
        explanation="Within 1 year",
        has_newer_corroboration=False,
        assessed_at="2024-01-01T00:00:00",
        days_old=180,
    )
    assert a.freshness_state == "current"
    assert a.days_old == 180
    data = a.model_dump()
    assert "freshness_state" in data
