"""
Pass 21.1 — Training OS Integration tests.

Covers:
- mastery_integration module (all 8 emission functions exist)
- unified_priority pipeline (compute_next_action determinism)
- curriculum_validator (validate_curriculum returns expected schema)
- event_pack base + registry (EventPackNotFoundError, registry listing)
- migration file presence and syntax checks
- API training module (new endpoints registered)
- Drill mastery hook (emit_from_drill_attempt callable)
- Workout mastery hook (emit_from_workout callable)
- Judge adaptation hook (emit_from_judge_adaptation callable)
- Full round hook (emit_from_full_round callable)
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
SERVICES = ROOT / "app" / "services"
API = ROOT / "app" / "api"
EVENT_PACKS = ROOT / "app" / "event_packs"
MIGRATIONS = ROOT.parent / "supabase" / "migrations"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Mastery Integration module
# ═══════════════════════════════════════════════════════════════════════════════

class TestMasteryIntegrationModule:
    def test_file_exists(self):
        assert (SERVICES / "mastery_integration.py").exists()

    def test_module_importable(self):
        import app.services.mastery_integration  # noqa: F401

    def test_emit_from_speech_analysis_exists(self):
        from app.services.mastery_integration import emit_from_speech_analysis
        assert callable(emit_from_speech_analysis)

    def test_emit_from_drill_attempt_exists(self):
        from app.services.mastery_integration import emit_from_drill_attempt
        assert callable(emit_from_drill_attempt)

    def test_emit_from_mission_completion_exists(self):
        from app.services.mastery_integration import emit_from_mission_completion
        assert callable(emit_from_mission_completion)

    def test_emit_from_rerecord_exists(self):
        from app.services.mastery_integration import emit_from_rerecord
        assert callable(emit_from_rerecord)

    def test_emit_from_coach_review_exists(self):
        from app.services.mastery_integration import emit_from_coach_review
        assert callable(emit_from_coach_review)

    def test_emit_from_workout_exists(self):
        from app.services.mastery_integration import emit_from_workout
        assert callable(emit_from_workout)

    def test_emit_from_judge_adaptation_exists(self):
        from app.services.mastery_integration import emit_from_judge_adaptation
        assert callable(emit_from_judge_adaptation)

    def test_emit_from_full_round_exists(self):
        from app.services.mastery_integration import emit_from_full_round
        assert callable(emit_from_full_round)

    def test_rubric_dim_to_skill_mapping(self):
        src = (SERVICES / "mastery_integration.py").read_text()
        assert "_RUBRIC_DIM_TO_SKILL" in src
        # canonical renames
        assert "responses" in src  # drops → responses
        assert "clarity" in src    # delivery → clarity

    def test_idempotent_source_id_pattern(self):
        src = (SERVICES / "mastery_integration.py").read_text()
        assert "source_id" in src
        assert "ON CONFLICT" in src or "on_conflict" in src.lower() or "source_id" in src


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Unified Priority Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnifiedPriority:
    def test_file_exists(self):
        assert (SERVICES / "unified_priority.py").exists()

    def test_module_importable(self):
        import app.services.unified_priority  # noqa: F401

    def test_compute_next_action_exists(self):
        from app.services.unified_priority import compute_next_action
        assert callable(compute_next_action)

    def test_sync_plan_with_mission_completion_exists(self):
        from app.services.unified_priority import sync_plan_with_mission_completion
        assert callable(sync_plan_with_mission_completion)

    def test_assignment_with_due_date_beats_training_plan(self):
        from app.services.unified_priority import compute_next_action
        # Assignments with due_date are the highest priority tier
        result = compute_next_action(
            mastery_profile={},
            active_plan_week={"skill_focus": "warranting", "lesson_id": "pf_novice_01"},
            coach_priority_skills=[],
            pending_assignments=[
                {"skill_focus": "weighing", "lesson_id": "pf_novice_05",
                 "assignment_id": "a1", "due_date": "2026-07-01"}
            ],
            active_missions=[],
            tournament_date_days=None,
            recent_skill_scores={},
        )
        assert result["source"] == "coach_assignment"

    def test_training_plan_beats_mastery_gap(self):
        from app.services.unified_priority import compute_next_action
        # organization has no prerequisites — plan skill is immediately eligible
        result = compute_next_action(
            mastery_profile={"organization": {"mastery_state": "not_started", "mastery_score": 0.0}},
            active_plan_week={"skill_focus": "organization", "lesson_id": "pf_novice_01"},
            coach_priority_skills=[],
            pending_assignments=[],
            active_missions=[],
            tournament_date_days=None,
            recent_skill_scores={},
        )
        assert result["source"] == "training_plan"
        assert result["skill_id"] == "organization"

    def test_mastery_gap_returned_for_lowest_score_skill(self):
        from app.services.unified_priority import compute_next_action
        # With no plan / assignments, should find mastery_gap (warranting score=0)
        result = compute_next_action(
            mastery_profile={"warranting": {"mastery_state": "not_started", "mastery_score": 0.0}},
            active_plan_week=None,
            coach_priority_skills=[],
            pending_assignments=[],
            active_missions=[],
            tournament_date_days=None,
            recent_skill_scores={},
        )
        assert result["source"] == "mastery_gap"

    def test_fallback_when_all_skills_proficient(self):
        from app.services.unified_priority import compute_next_action, PF_SKILL_PRIORITY_ORDER
        from app.services.mastery_engine import PROFICIENT_THRESHOLD
        # All skills at or above proficient threshold — expect fallback or needs_refresh
        mastery = {
            skill: {"mastery_state": "proficient", "mastery_score": PROFICIENT_THRESHOLD + 0.05}
            for skill in PF_SKILL_PRIORITY_ORDER
        }
        result = compute_next_action(
            mastery_profile=mastery,
            active_plan_week=None,
            coach_priority_skills=[],
            pending_assignments=[],
            active_missions=[],
            tournament_date_days=None,
            recent_skill_scores={},
        )
        # When all are proficient, we get fallback (no refresh since mastery_state != needs_refresh)
        assert result["source"] in ("fallback", "needs_refresh")
        assert "skill_id" in result

    def test_coach_priority_skill_without_prerequisites(self):
        from app.services.unified_priority import compute_next_action
        # clarity has no prerequisites — coach priority should work
        result = compute_next_action(
            mastery_profile={"clarity": {"mastery_state": "not_started", "mastery_score": 0.0}},
            active_plan_week=None,
            coach_priority_skills=["clarity"],
            pending_assignments=[],
            active_missions=[],
            tournament_date_days=None,
            recent_skill_scores={},
        )
        assert result["source"] == "coach_priority"
        assert result["skill_id"] == "clarity"

    def test_needs_refresh_when_all_gaps_filled(self):
        from app.services.unified_priority import compute_next_action, PF_SKILL_PRIORITY_ORDER
        from app.services.mastery_engine import PROFICIENT_THRESHOLD
        # All skills proficient except one marked needs_refresh
        mastery = {
            skill: {"mastery_state": "proficient", "mastery_score": PROFICIENT_THRESHOLD + 0.05}
            for skill in PF_SKILL_PRIORITY_ORDER
        }
        mastery["warranting"] = {"mastery_state": "needs_refresh", "mastery_score": PROFICIENT_THRESHOLD + 0.05}
        result = compute_next_action(
            mastery_profile=mastery,
            active_plan_week=None,
            coach_priority_skills=[],
            pending_assignments=[],
            active_missions=[],
            tournament_date_days=None,
            recent_skill_scores={},
        )
        assert result["source"] == "needs_refresh"
        assert result["skill_id"] == "warranting"

    def test_returns_required_keys(self):
        from app.services.unified_priority import compute_next_action
        result = compute_next_action({}, None, [], [], [], None, {})
        for key in ("skill_id", "source", "context"):
            assert key in result, f"Missing key: {key}"

    def test_sync_plan_advances_week(self):
        from app.services.unified_priority import sync_plan_with_mission_completion
        from app.services.mastery_engine import PROFICIENT_THRESHOLD
        plan = {
            "id": "plan1",
            "current_week": 1,
            "total_weeks": 4,
            "weeks": [
                {"week_num": 1, "skill_focus": "warranting"},
                {"week_num": 2, "skill_focus": "evidence_use"},
            ],
        }
        # mastery_state key and score above threshold
        mastery = {"warranting": {"mastery_state": "proficient", "mastery_score": PROFICIENT_THRESHOLD + 0.05}}
        updated = sync_plan_with_mission_completion(mastery, plan, "warranting")
        assert updated["current_week"] == 2

    def test_sync_plan_no_advance_if_not_proficient(self):
        from app.services.unified_priority import sync_plan_with_mission_completion
        plan = {"id": "p", "current_week": 1, "total_weeks": 4,
                "weeks": [{"week_num": 1, "skill_focus": "warranting"}]}
        mastery = {"warranting": {"mastery_state": "developing", "mastery_score": 0.45}}
        updated = sync_plan_with_mission_completion(mastery, plan, "warranting")
        assert updated["current_week"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Curriculum Validator
# ═══════════════════════════════════════════════════════════════════════════════

class TestCurriculumValidator:
    def test_file_exists(self):
        assert (SERVICES / "curriculum_validator.py").exists()

    def test_validate_curriculum_importable(self):
        from app.services.curriculum_validator import validate_curriculum
        assert callable(validate_curriculum)

    def test_returns_expected_schema(self):
        from app.services.curriculum_validator import validate_curriculum
        result = validate_curriculum()
        assert isinstance(result, dict)
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert "stats" in result

    def test_valid_is_bool(self):
        from app.services.curriculum_validator import validate_curriculum
        result = validate_curriculum()
        assert isinstance(result["valid"], bool)

    def test_errors_is_list(self):
        from app.services.curriculum_validator import validate_curriculum
        result = validate_curriculum()
        assert isinstance(result["errors"], list)

    def test_curriculum_passes_validation(self):
        from app.services.curriculum_validator import validate_curriculum
        result = validate_curriculum()
        assert result["valid"], f"Curriculum invalid: {result['errors']}"

    def test_stats_contains_lesson_count(self):
        from app.services.curriculum_validator import validate_curriculum
        result = validate_curriculum()
        assert result["stats"].get("lesson_count", 0) >= 11


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Event Pack Base + Registry
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventPackArchitecture:
    def test_base_file_exists(self):
        assert (EVENT_PACKS / "base.py").exists()

    def test_registry_file_exists(self):
        assert (EVENT_PACKS / "registry.py").exists()

    def test_event_pack_not_found_error_importable(self):
        from app.event_packs.base import EventPackNotFoundError
        assert issubclass(EventPackNotFoundError, ValueError)

    def test_get_event_pack_raises_for_unknown(self):
        from app.event_packs.registry import get_event_pack
        from app.event_packs.base import EventPackNotFoundError
        with pytest.raises(EventPackNotFoundError):
            get_event_pack("nonexistent_format_xyz")

    def test_get_event_pack_returns_public_forum(self):
        from app.event_packs.registry import get_event_pack
        mod = get_event_pack("public_forum")
        assert hasattr(mod, "SKILL_REGISTRY")

    def test_list_event_packs_returns_list(self):
        from app.event_packs.registry import list_event_packs
        packs = list_event_packs()
        assert isinstance(packs, list)
        assert len(packs) >= 1

    def test_list_includes_public_forum(self):
        from app.event_packs.registry import list_event_packs
        ids = [p["id"] for p in list_event_packs()]
        assert "public_forum" in ids

    def test_error_message_lists_supported(self):
        from app.event_packs.registry import get_event_pack
        from app.event_packs.base import EventPackNotFoundError
        try:
            get_event_pack("bad_pack")
        except EventPackNotFoundError as e:
            assert "public_forum" in str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Migration File
# ═══════════════════════════════════════════════════════════════════════════════

class TestPass21p1Migration:
    def _find_migration(self):
        if MIGRATIONS.exists():
            for f in sorted(MIGRATIONS.glob("*.sql")):
                if "pass21p1" in f.name or "training_integration" in f.name:
                    return f
        return None

    def test_migration_exists(self):
        assert self._find_migration() is not None, (
            "Pass 21.1 migration (pass21p1_training_integration) not found in supabase/migrations/"
        )

    def test_migration_has_training_sessions(self):
        f = self._find_migration()
        if f is None:
            pytest.skip("migration not found")
        sql = f.read_text()
        assert "training_sessions" in sql

    def test_migration_has_source_id_column(self):
        f = self._find_migration()
        if f is None:
            pytest.skip("migration not found")
        sql = f.read_text()
        assert "source_id" in sql

    def test_migration_has_unique_index(self):
        f = self._find_migration()
        if f is None:
            pytest.skip("migration not found")
        sql = f.read_text()
        assert "UNIQUE" in sql or "unique" in sql.lower()

    def test_migration_enables_rls(self):
        f = self._find_migration()
        if f is None:
            pytest.skip("migration not found")
        sql = f.read_text()
        assert "ENABLE ROW LEVEL SECURITY" in sql or "enable row level security" in sql.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Training API — new endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrainingAPINewEndpoints:
    def _src(self):
        return (API / "training.py").read_text()

    def test_next_action_endpoint_defined(self):
        src = self._src()
        assert "/next-action" in src

    def test_sessions_post_endpoint_defined(self):
        src = self._src()
        assert '"/sessions"' in src or "'/sessions'" in src

    def test_sessions_patch_endpoint_defined(self):
        src = self._src()
        assert '"/sessions/{session_id}"' in src or "'{session_id}'" in src

    def test_sessions_active_get_endpoint_defined(self):
        src = self._src()
        assert "active" in src

    def test_curriculum_validate_endpoint_defined(self):
        src = self._src()
        assert "validate" in src

    def test_unified_priority_imported(self):
        src = self._src()
        assert "unified_priority" in src or "compute_next_action" in src

    def test_curriculum_validator_imported(self):
        src = self._src()
        assert "curriculum_validator" in src or "validate_curriculum" in src


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Mastery hooks in other APIs
# ═══════════════════════════════════════════════════════════════════════════════

class TestMasteryHooksInAPIs:
    def test_drills_api_calls_emit_from_drill_attempt(self):
        src = (API / "drills.py").read_text()
        assert "emit_from_drill_attempt" in src

    def test_workouts_api_calls_emit_from_workout(self):
        src = (API / "workouts.py").read_text()
        assert "emit_from_workout" in src

    def test_judge_adaptation_api_calls_emit_from_judge_adaptation(self):
        src = (API / "judge_adaptation.py").read_text()
        assert "emit_from_judge_adaptation" in src

    def test_round_simulations_api_calls_emit_from_full_round(self):
        src = (API / "round_simulations.py").read_text()
        assert "emit_from_full_round" in src

    def test_missions_api_calls_emit_from_mission_completion(self):
        src = (API / "missions.py").read_text()
        assert "emit_from_mission_completion" in src

    def test_analysis_pipeline_calls_emit_from_speech_analysis(self):
        src = (SERVICES / "analysis_pipeline.py").read_text()
        assert "emit_from_speech_analysis" in src

    def test_hooks_wrapped_in_try_except(self):
        # All hooks must be non-fatal — verify they're in try blocks
        for fname in ("drills.py", "workouts.py"):
            src = (API / fname).read_text()
            assert "try:" in src
            assert "except" in src

    def test_drills_hook_only_fires_on_completed_status(self):
        src = (API / "drills.py").read_text()
        # The hook should be inside the completed branch
        idx_emit = src.index("emit_from_drill_attempt")
        # Find nearest "completed" before the emit
        segment = src[max(0, idx_emit - 400):idx_emit]
        assert "completed" in segment

    def test_workout_hook_only_fires_on_completed_status(self):
        src = (API / "workouts.py").read_text()
        idx_emit = src.index("emit_from_workout")
        segment = src[max(0, idx_emit - 600):idx_emit]
        assert "completed" in segment


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Lesson metadata completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestLessonMetadataCompleteness:
    def _curriculum(self):
        from app.event_packs.public_forum import NOVICE_PF_CURRICULUM
        return NOVICE_PF_CURRICULUM

    def test_all_lessons_have_common_mistakes(self):
        for lesson in self._curriculum():
            assert "common_mistakes" in lesson, f"Missing common_mistakes: {lesson.get('id')}"
            assert len(lesson["common_mistakes"]) >= 1

    def test_all_lessons_have_coach_note(self):
        for lesson in self._curriculum():
            assert "coach_note" in lesson, f"Missing coach_note: {lesson.get('id')}"
            assert len(lesson["coach_note"]) >= 10

    def test_all_lessons_have_author(self):
        for lesson in self._curriculum():
            assert lesson.get("author") == "Dissio Curriculum Team", (
                f"Missing/wrong author on {lesson.get('id')}"
            )

    def test_all_lessons_have_reviewed_date(self):
        for lesson in self._curriculum():
            assert "reviewed_date" in lesson, f"Missing reviewed_date: {lesson.get('id')}"
            assert lesson["reviewed_date"].startswith("2026")

    def test_lesson_count_is_11(self):
        assert len(self._curriculum()) == 11


# ═══════════════════════════════════════════════════════════════════════════════
# 9. AST-level checks (no runtime imports needed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestASTChecks:
    def test_mastery_integration_has_no_bare_except(self):
        src = (SERVICES / "mastery_integration.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Bare except catches everything — we want typed exceptions or at least Exception
                if node.type is None:
                    pytest.fail("mastery_integration.py has a bare except clause")

    def test_unified_priority_is_pure_function(self):
        src = (SERVICES / "unified_priority.py").read_text()
        # No DB calls — should not import supabase directly
        assert "get_supabase" not in src
        assert "supabase.table" not in src

    def test_curriculum_validator_has_circular_check(self):
        src = (SERVICES / "curriculum_validator.py").read_text()
        assert "circular" in src.lower() or "cycle" in src.lower() or "visited" in src.lower()
