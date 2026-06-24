"""Pass 16 — Round simulation API module tests.

These are import/structure tests since the API requires a live Supabase connection.
Tests verify: module importable, router has correct prefix, all expected routes exist.
"""
from __future__ import annotations
import pytest


def test_round_simulations_api_importable():
    from app.api import round_simulations
    assert hasattr(round_simulations, "router")


def test_router_prefix():
    from app.api.round_simulations import router
    assert router.prefix == "/round-simulations"


def test_router_tags():
    from app.api.round_simulations import router
    assert "round_simulations" in router.tags


def test_router_has_expected_routes():
    from app.api.round_simulations import router
    prefix = router.prefix  # "/round-simulations"
    full_paths = {r.path for r in router.routes}
    # Paths include the router prefix; strip it to get relative paths
    relative = {p[len(prefix):] for p in full_paths if p.startswith(prefix)}
    assert "" in relative or "/" in relative  # list rounds
    assert "/{round_id}" in relative
    assert "/{round_id}/start" in relative
    assert "/{round_id}/speeches/student" in relative
    assert "/{round_id}/speeches/opponent" in relative
    assert "/{round_id}/advance-phase" in relative
    assert "/{round_id}/decision" in relative
    assert "/{round_id}/drills" in relative
    assert "/{round_id}/flow" in relative
    assert "/{round_id}/crossfire/question" in relative
    assert "/{round_id}/crossfire/answer" in relative
    assert "/{round_id}/rejudge" in relative


def test_main_includes_round_simulations_router():
    """Verify that main.py registers the round_simulations router."""
    from app.main import app
    prefixes = [r.path for r in app.routes]
    assert any("round-simulations" in p for p in prefixes)


def test_round_simulation_models_importable():
    from app.models.round_simulation import (
        RoundSimulation,
        RoundSimulationConfig,
        RoundPhaseType,
        RoundSide,
        RoundSpeech,
        RoundArgument,
        RoundDecision,
        RoundFlowEvent,
        RoundEvidenceUse,
        OpponentRoundPlan,
        CrossfireExchange,
    )


def test_round_services_importable():
    from app.services.round_state_machine import (
        get_phase_order,
        next_phase,
        validate_phase_transition,
        phase_speaker,
        student_speaks_in_phase,
    )
    from app.services.round_flow_tracker import (
        apply_event,
        reconstruct_flow_status,
    )
    from app.services.speech_legality_checker import check_speech_legality
    from app.services.round_decision_engine import run_decision_engine
    from app.services.round_drill_generator import generate_post_round_drills
    from app.services.evidence_use_tracker import create_evidence_use_record
    from app.services.opponent_strategy import build_opponent_round_plan
    from app.services.opponent_speech_generator import generate_opponent_speech
    from app.services.crossfire_simulator import generate_crossfire_question
    from app.services.round_prep_connector import get_pre_round_readiness_warnings
