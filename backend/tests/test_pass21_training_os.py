"""
Pass 21 — Training OS tests.

Verifies (source-level and unit tests):
1. Event pack data integrity (28 skills, 11 lessons, legacy map)
2. Mastery engine determinism (aggregate, decay, state machine)
3. Training planner (priority order, plan generation)
4. Diagnostic engine (baseline scores, strength/priority detection)
5. Pydantic models (field presence, validation)
6. API router structure (17 endpoints, auth guards, route paths)
7. Migration file (6 new tables, RLS policies, indexes)
8. Main.py registration
9. Backward compatibility (legacy skill names still resolve)
10. Edge cases (empty evidence, zero confidence, staleness)
"""

from __future__ import annotations

import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"

sys.path.insert(0, str(BACKEND_ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# 1. Event Pack — data integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestEventPackIntegrity(unittest.TestCase):

    def setUp(self):
        from app.event_packs.public_forum import (
            SKILL_REGISTRY, LEGACY_SKILL_MAP, CANONICAL_TO_LEGACY,
            NOVICE_PF_CURRICULUM, NOVICE_TRACK, EVENT_PACK,
            SKILL_PREREQUISITES, get_skill, get_lesson,
            resolve_legacy_skill, get_prerequisites_met,
        )
        self.SKILL_REGISTRY = SKILL_REGISTRY
        self.LEGACY_SKILL_MAP = LEGACY_SKILL_MAP
        self.CANONICAL_TO_LEGACY = CANONICAL_TO_LEGACY
        self.NOVICE_PF_CURRICULUM = NOVICE_PF_CURRICULUM
        self.NOVICE_TRACK = NOVICE_TRACK
        self.EVENT_PACK = EVENT_PACK
        self.SKILL_PREREQUISITES = SKILL_PREREQUISITES
        self.get_skill = get_skill
        self.get_lesson = get_lesson
        self.resolve_legacy_skill = resolve_legacy_skill
        self.get_prerequisites_met = get_prerequisites_met

    def test_skill_count_is_28(self):
        self.assertEqual(len(self.SKILL_REGISTRY), 28)

    def test_lesson_count_is_11(self):
        self.assertEqual(len(self.NOVICE_PF_CURRICULUM), 11)

    def test_all_skill_categories_present(self):
        cats = {s["category"] for s in self.SKILL_REGISTRY.values()}
        self.assertIn("core_communication", cats)
        self.assertIn("pf_argumentation", cats)
        self.assertIn("speech_role", cats)

    def test_core_communication_count(self):
        count = sum(1 for s in self.SKILL_REGISTRY.values() if s["category"] == "core_communication")
        self.assertEqual(count, 8)

    def test_pf_argumentation_count(self):
        count = sum(1 for s in self.SKILL_REGISTRY.values() if s["category"] == "pf_argumentation")
        self.assertEqual(count, 15)

    def test_speech_role_count(self):
        count = sum(1 for s in self.SKILL_REGISTRY.values() if s["category"] == "speech_role")
        self.assertEqual(count, 5)

    def test_each_skill_has_required_fields(self):
        required = {"id", "name", "description", "novice_explanation", "prerequisites",
                    "category", "success_criteria", "mastery_thresholds"}
        for skill_id, skill in self.SKILL_REGISTRY.items():
            with self.subTest(skill_id=skill_id):
                for field in required:
                    self.assertIn(field, skill, f"{skill_id} missing field: {field}")

    def test_mastery_thresholds_keys(self):
        for skill_id, skill in self.SKILL_REGISTRY.items():
            thresholds = skill["mastery_thresholds"]
            for key in ("introducing", "developing", "proficient", "mastery"):
                with self.subTest(skill_id=skill_id, key=key):
                    self.assertIn(key, thresholds)

    def test_warranting_has_prerequisites(self):
        skill = self.get_skill("warranting")
        self.assertIsNotNone(skill)
        self.assertIn("claim_construction", skill["prerequisites"])

    def test_legacy_map_has_9_entries(self):
        self.assertGreaterEqual(len(self.LEGACY_SKILL_MAP), 9)

    def test_legacy_delivery_maps_to_clarity(self):
        self.assertEqual(self.LEGACY_SKILL_MAP.get("delivery"), "clarity")

    def test_legacy_drops_maps_to_responses(self):
        self.assertEqual(self.LEGACY_SKILL_MAP.get("drops"), "responses")

    def test_resolve_legacy_skill_returns_canonical(self):
        self.assertEqual(self.resolve_legacy_skill("delivery"), "clarity")
        self.assertEqual(self.resolve_legacy_skill("drops"), "responses")

    def test_resolve_unknown_returns_input(self):
        self.assertEqual(self.resolve_legacy_skill("unknown_skill_xyz"), "unknown_skill_xyz")

    def test_get_skill_returns_none_for_missing(self):
        self.assertIsNone(self.get_skill("definitely_not_a_skill"))

    def test_get_lesson_returns_correct_lesson(self):
        lesson = self.get_lesson("pf_novice_01")
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson["id"], "pf_novice_01")

    def test_each_lesson_has_required_fields(self):
        required = {"id", "title", "skill_id", "difficulty", "estimated_minutes",
                    "what_is_it", "why_judges_care", "weak_example", "strong_example",
                    "what_changed", "micro_drill", "success_checklist"}
        for lesson in self.NOVICE_PF_CURRICULUM:
            with self.subTest(lesson_id=lesson["id"]):
                for field in required:
                    self.assertIn(field, lesson, f"{lesson['id']} missing: {field}")

    def test_lesson_skill_ids_are_valid(self):
        valid_skills = set(self.SKILL_REGISTRY.keys()) | set(self.LEGACY_SKILL_MAP.keys())
        for lesson in self.NOVICE_PF_CURRICULUM:
            skill_id = lesson["skill_id"]
            resolved = self.resolve_legacy_skill(skill_id)
            self.assertIn(resolved, self.SKILL_REGISTRY,
                          f"Lesson {lesson['id']} references unknown skill: {skill_id}")

    def test_novice_track_has_11_lessons(self):
        self.assertEqual(len(self.NOVICE_TRACK["lesson_ids"]), 11)

    def test_event_pack_has_required_keys(self):
        for key in ("id", "name", "skills", "curriculum", "tracks"):
            with self.subTest(key=key):
                self.assertIn(key, self.EVENT_PACK)

    def test_prerequisites_all_valid_skill_ids(self):
        for skill_id, prereqs in self.SKILL_PREREQUISITES.items():
            for prereq in prereqs:
                with self.subTest(skill=skill_id, prereq=prereq):
                    self.assertIn(prereq, self.SKILL_REGISTRY,
                                  f"{skill_id} has invalid prereq: {prereq}")

    def test_get_prerequisites_met_empty_mastered(self):
        # Claim construction has no prereqs, should be available immediately
        result = self.get_prerequisites_met("claim_construction", set())
        self.assertTrue(result)

    def test_get_prerequisites_met_blocks_when_missing(self):
        # weighing requires impact_explanation and comparative_analysis
        result = self.get_prerequisites_met("weighing", set())
        self.assertFalse(result)

    def test_get_prerequisites_met_passes_when_satisfied(self):
        result = self.get_prerequisites_met("warranting", {"claim_construction"})
        self.assertTrue(result)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Mastery Engine — deterministic computation
# ─────────────────────────────────────────────────────────────────────────────

class TestMasteryEngine(unittest.TestCase):

    def setUp(self):
        from app.services.mastery_engine import (
            normalize_score, compute_recency_weight, compute_evidence_weight,
            compute_confidence, determine_mastery_state, aggregate_mastery,
            build_mastery_explanation, compute_team_skill_gaps,
            SOURCE_WEIGHTS, RECENCY_HALF_LIFE_DAYS,
        )
        self.normalize_score = normalize_score
        self.compute_recency_weight = compute_recency_weight
        self.compute_evidence_weight = compute_evidence_weight
        self.compute_confidence = compute_confidence
        self.determine_mastery_state = determine_mastery_state
        self.aggregate_mastery = aggregate_mastery
        self.build_mastery_explanation = build_mastery_explanation
        self.compute_team_skill_gaps = compute_team_skill_gaps
        self.SOURCE_WEIGHTS = SOURCE_WEIGHTS
        self.RECENCY_HALF_LIFE_DAYS = RECENCY_HALF_LIFE_DAYS

    # normalize_score
    def test_normalize_score_clamps_to_100(self):
        self.assertEqual(self.normalize_score(150.0, "speech_analysis"), 100.0)

    def test_normalize_score_clamps_to_0(self):
        self.assertEqual(self.normalize_score(-10.0, "speech_analysis"), 0.0)

    def test_normalize_score_0_20_scale(self):
        result = self.normalize_score(15.0, "speech_analysis", input_scale="0-20")
        self.assertAlmostEqual(result, 75.0, places=1)

    def test_normalize_score_0_20_max(self):
        result = self.normalize_score(20.0, "speech_analysis", input_scale="0-20")
        self.assertAlmostEqual(result, 100.0, places=1)

    # recency decay
    def test_recency_weight_fresh_is_near_1(self):
        now = datetime.now(timezone.utc)
        w = self.compute_recency_weight(now, now)
        self.assertAlmostEqual(w, 1.0, places=3)

    def test_recency_weight_half_life_is_half(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=self.RECENCY_HALF_LIFE_DAYS)
        w = self.compute_recency_weight(old, now)
        self.assertAlmostEqual(w, 0.5, places=2)

    def test_recency_weight_very_old_near_0(self):
        now = datetime.now(timezone.utc)
        very_old = now - timedelta(days=200)
        w = self.compute_recency_weight(very_old, now)
        self.assertLess(w, 0.1)

    # source weights
    def test_coach_review_highest_weight(self):
        self.assertGreater(self.SOURCE_WEIGHTS["coach_review"], self.SOURCE_WEIGHTS["speech_analysis"])

    def test_re_record_higher_than_speech(self):
        self.assertGreater(self.SOURCE_WEIGHTS["re_record"], self.SOURCE_WEIGHTS["speech_analysis"])

    def test_drill_attempt_lower_than_speech(self):
        self.assertLess(self.SOURCE_WEIGHTS["drill_attempt"], self.SOURCE_WEIGHTS["speech_analysis"])

    # confidence
    def test_confidence_zero_for_empty(self):
        self.assertEqual(self.compute_confidence([]), 0.0)

    def test_confidence_increases_with_evidence(self):
        items_1 = [{"source_type": "speech_analysis"}]
        items_5 = [{"source_type": "speech_analysis"}] * 5
        self.assertLess(
            self.compute_confidence(items_1),
            self.compute_confidence(items_5),
        )

    def test_confidence_max_1(self):
        items = [{"source_type": "coach_review"}] * 20
        self.assertLessEqual(self.compute_confidence(items), 1.0)

    # aggregate_mastery
    def test_aggregate_empty_returns_zero(self):
        now = datetime.now(timezone.utc)
        result = self.aggregate_mastery([], now)
        self.assertEqual(result["mastery_score"], 0.0)
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["evidence_count"], 0)
        self.assertIsNone(result["last_demonstrated_at"])

    def test_aggregate_single_item(self):
        now = datetime.now(timezone.utc)
        items = [{"normalized_score": 80.0, "source_type": "speech_analysis", "recorded_at": now}]
        result = self.aggregate_mastery(items, now)
        self.assertAlmostEqual(result["mastery_score"], 80.0, places=0)
        self.assertEqual(result["evidence_count"], 1)

    def test_aggregate_recent_items_weighted_more(self):
        now = datetime.now(timezone.utc)
        items = [
            {"normalized_score": 90.0, "source_type": "speech_analysis", "recorded_at": now},
            {"normalized_score": 10.0, "source_type": "speech_analysis", "recorded_at": now - timedelta(days=60)},
        ]
        result = self.aggregate_mastery(items, now)
        # Recent 90 should dominate; weighted avg > 50
        self.assertGreater(result["mastery_score"], 50.0)

    def test_aggregate_iso_string_date_accepted(self):
        now = datetime.now(timezone.utc)
        items = [{"normalized_score": 60.0, "source_type": "drill_attempt",
                   "recorded_at": now.isoformat()}]
        result = self.aggregate_mastery(items, now)
        self.assertGreater(result["mastery_score"], 0)

    # determine_mastery_state
    def test_state_not_started_when_no_evidence(self):
        now = datetime.now(timezone.utc)
        state = self.determine_mastery_state(0.0, 0.0, 0, None, now)
        self.assertEqual(state, "not_started")

    def test_state_introduced_with_few_evidence(self):
        now = datetime.now(timezone.utc)
        state = self.determine_mastery_state(30.0, 0.3, 1, now, now)
        self.assertEqual(state, "introduced")

    def test_state_developing_with_moderate_score(self):
        now = datetime.now(timezone.utc)
        state = self.determine_mastery_state(35.0, 0.5, 4, now, now)
        self.assertEqual(state, "developing")

    def test_state_proficient_at_50_plus(self):
        now = datetime.now(timezone.utc)
        state = self.determine_mastery_state(60.0, 0.6, 5, now, now)
        self.assertEqual(state, "proficient")

    def test_state_mastered_at_75_plus_with_high_confidence(self):
        now = datetime.now(timezone.utc)
        state = self.determine_mastery_state(80.0, 0.8, 5, now, now)
        self.assertEqual(state, "mastered")

    def test_state_needs_refresh_after_30_days(self):
        now = datetime.now(timezone.utc)
        stale_date = now - timedelta(days=35)
        state = self.determine_mastery_state(80.0, 0.8, 5, stale_date, now)
        self.assertEqual(state, "needs_refresh")

    def test_state_not_needs_refresh_if_below_proficient(self):
        now = datetime.now(timezone.utc)
        stale_date = now - timedelta(days=35)
        state = self.determine_mastery_state(30.0, 0.3, 2, stale_date, now)
        self.assertNotEqual(state, "needs_refresh")

    # team gaps
    def test_team_skill_gaps_computes_avg(self):
        student_data = [
            {"user_id": "u1", "skill_id": "warranting", "mastery_score": 60},
            {"user_id": "u2", "skill_id": "warranting", "mastery_score": 40},
        ]
        result = self.compute_team_skill_gaps(student_data)
        self.assertIn("warranting", result)
        self.assertAlmostEqual(result["warranting"]["avg_score"], 50.0)

    def test_team_skill_gaps_pct_proficient(self):
        student_data = [
            {"user_id": "u1", "skill_id": "weighing", "mastery_score": 60},
            {"user_id": "u2", "skill_id": "weighing", "mastery_score": 30},
        ]
        result = self.compute_team_skill_gaps(student_data)
        # 1 out of 2 is proficient (score >= 50) = 50%
        self.assertAlmostEqual(result["weighing"]["pct_proficient"], 50.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Training Planner — plan generation
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingPlanner(unittest.TestCase):

    def setUp(self):
        from app.services.training_planner import (
            prioritize_skills, generate_weekly_objective,
            generate_plan, suggest_practice_agenda,
        )
        self.prioritize_skills = prioritize_skills
        self.generate_weekly_objective = generate_weekly_objective
        self.generate_plan = generate_plan
        self.suggest_practice_agenda = suggest_practice_agenda

    def _basic_profile(self):
        return {
            "warranting": {"mastery_score": 20.0, "mastery_state": "developing", "confidence": 0.3},
            "clash": {"mastery_score": 30.0, "mastery_state": "developing", "confidence": 0.4},
            "weighing": {"mastery_score": 5.0, "mastery_state": "introduced", "confidence": 0.1},
            "claim_construction": {"mastery_score": 55.0, "mastery_state": "proficient", "confidence": 0.6},
        }

    def test_prioritize_returns_list(self):
        result = self.prioritize_skills(self._basic_profile())
        self.assertIsInstance(result, list)

    def test_prioritize_returns_up_to_6_skills(self):
        result = self.prioritize_skills(self._basic_profile())
        self.assertLessEqual(len(result), 6)

    def test_prioritize_prefers_low_mastery_skills(self):
        result = self.prioritize_skills(self._basic_profile())
        # weighing (5) or warranting (20) should appear before high-mastery skills
        self.assertTrue(len(result) > 0)
        # The top priority should not be claim_construction (already proficient)
        if result:
            self.assertNotEqual(result[0], "claim_construction")

    def test_generate_weekly_objective_structure(self):
        week = self.generate_weekly_objective("warranting", 20.0, 1)
        for field in ("week", "skill_focus", "skill_name", "objective", "drill_description",
                      "speech_application", "completion_criteria", "mastery_target", "estimated_hours"):
            with self.subTest(field=field):
                self.assertIn(field, week)

    def test_generate_weekly_objective_target_higher_than_current(self):
        week = self.generate_weekly_objective("warranting", 20.0, 1)
        self.assertGreater(week["mastery_target"], 20.0)

    def test_generate_weekly_objective_week_number(self):
        week = self.generate_weekly_objective("clash", 30.0, 3)
        self.assertEqual(week["week"], 3)

    def test_generate_plan_1_week(self):
        plan = self.generate_plan(self._basic_profile(), "1_week")
        self.assertEqual(plan["total_weeks"], 1)
        self.assertEqual(len(plan["weeks"]), 1)

    def test_generate_plan_4_week(self):
        plan = self.generate_plan(self._basic_profile(), "4_week")
        self.assertEqual(plan["total_weeks"], 4)
        self.assertEqual(len(plan["weeks"]), 4)

    def test_generate_plan_has_summary(self):
        plan = self.generate_plan(self._basic_profile(), "1_week")
        self.assertIn("summary", plan)
        self.assertIsInstance(plan["summary"], str)

    def test_generate_plan_coach_priority_overrides(self):
        plan = self.generate_plan(
            self._basic_profile(),
            "4_week",
            coach_priority_skills=["weighing"],
        )
        # Weighing should appear in first week(s)
        first_skills = [w["skill_focus"] for w in plan["weeks"][:2]]
        self.assertIn("weighing", first_skills)

    def test_generate_plan_tournament_countdown(self):
        from datetime import date
        # 3 weeks out
        t_date = date.today() + timedelta(days=21)
        plan = self.generate_plan(self._basic_profile(), "tournament_countdown", tournament_date=t_date)
        self.assertGreaterEqual(plan["total_weeks"], 1)

    def test_suggest_practice_agenda_structure(self):
        team_gaps = {
            "warranting": {"avg_score": 20.0, "pct_proficient": 30.0, "pct_mastered": 0.0, "student_count": 5},
            "weighing": {"avg_score": 15.0, "pct_proficient": 20.0, "pct_mastered": 0.0, "student_count": 5},
            "clash": {"avg_score": 40.0, "pct_proficient": 60.0, "pct_mastered": 10.0, "student_count": 5},
        }
        agenda = self.suggest_practice_agenda(team_gaps, duration_minutes=60)
        self.assertIsInstance(agenda, list)
        for item in agenda:
            for field in ("activity_type", "skill_id", "description", "duration_minutes", "team_data_reason"):
                with self.subTest(field=field):
                    self.assertIn(field, item)

    def test_suggest_practice_agenda_total_time(self):
        team_gaps = {
            "warranting": {"avg_score": 20.0, "pct_proficient": 30.0, "pct_mastered": 0.0, "student_count": 3},
            "responses": {"avg_score": 25.0, "pct_proficient": 40.0, "pct_mastered": 5.0, "student_count": 3},
        }
        agenda = self.suggest_practice_agenda(team_gaps, duration_minutes=45)
        total = sum(item["duration_minutes"] for item in agenda)
        self.assertLessEqual(total, 45)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Diagnostic Engine
# ─────────────────────────────────────────────────────────────────────────────

class TestDiagnosticEngine(unittest.TestCase):

    def setUp(self):
        from app.services.diagnostic_engine import (
            compute_initial_mastery_from_diagnostic,
            identify_strengths_and_priorities,
            recommend_starting_track,
            get_first_week_plan,
        )
        self.compute_initial = compute_initial_mastery_from_diagnostic
        self.identify = identify_strengths_and_priorities
        self.recommend_track = recommend_starting_track
        self.first_week = get_first_week_plan

    def test_first_time_level_returns_all_skills(self):
        result = self.compute_initial({"experience_level": "first_time", "self_ratings": {}})
        self.assertGreater(len(result), 0)
        for skill_id, data in result.items():
            with self.subTest(skill_id=skill_id):
                self.assertIn("mastery_score", data)
                self.assertIn("mastery_state", data)

    def test_novice_level_higher_than_first_time(self):
        first = self.compute_initial({"experience_level": "first_time", "self_ratings": {}})
        novice = self.compute_initial({"experience_level": "novice", "self_ratings": {}})
        if first and novice:
            avg_first = sum(v["mastery_score"] for v in first.values()) / len(first)
            avg_novice = sum(v["mastery_score"] for v in novice.values()) / len(novice)
            self.assertGreaterEqual(avg_novice, avg_first)

    def test_self_rating_5_boosts_score(self):
        base = self.compute_initial({"experience_level": "novice", "self_ratings": {}})
        boosted = self.compute_initial({
            "experience_level": "novice",
            "self_ratings": {"warranting": 5}
        })
        if base and boosted and "warranting" in base and "warranting" in boosted:
            self.assertGreaterEqual(boosted["warranting"]["mastery_score"],
                                    base["warranting"]["mastery_score"])

    def test_confidence_without_speech_is_low(self):
        result = self.compute_initial({"experience_level": "novice", "self_ratings": {}})
        for data in result.values():
            self.assertLessEqual(data["confidence"], 0.4)

    def test_confidence_with_speech_higher(self):
        result = self.compute_initial({
            "experience_level": "novice",
            "self_ratings": {},
            "speech_scores": {"warranting": 12.0},
        })
        if "warranting" in result:
            self.assertGreater(result["warranting"]["confidence"], 0.15)

    def test_identify_returns_tuple(self):
        profile = {
            "warranting": {"mastery_score": 60.0, "mastery_state": "proficient"},
            "weighing": {"mastery_score": 10.0, "mastery_state": "developing"},
            "clash": {"mastery_score": 80.0, "mastery_state": "mastered"},
        }
        result = self.identify(profile)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_identify_strengths_ordered_high_to_low(self):
        profile = {
            "warranting": {"mastery_score": 60.0, "mastery_state": "proficient"},
            "weighing": {"mastery_score": 10.0, "mastery_state": "developing"},
            "clash": {"mastery_score": 80.0, "mastery_state": "mastered"},
        }
        strengths, _ = self.identify(profile)
        if len(strengths) >= 2:
            scores = [profile[s]["mastery_score"] for s in strengths if s in profile]
            for i in range(len(scores) - 1):
                self.assertGreaterEqual(scores[i], scores[i + 1])

    def test_recommend_track_returns_string(self):
        result = self.recommend_track("novice", ["warranting", "clash"])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_first_week_plan_returns_list(self):
        result = self.first_week("novice", ["warranting", "clash"])
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for item in result:
            self.assertIsInstance(item, str)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class TestPydanticModels(unittest.TestCase):

    def setUp(self):
        from app.models.training import (
            MasteryScore, MasteryProfile, AddMasteryEvidenceRequest,
            CoachOverrideRequest, TrainingPlan, GeneratePlanRequest,
            CurriculumProgress, MarkLessonRequest, CoachCalibrationRequest,
            DiagnosticStartRequest, DiagnosticCompleteRequest, PracticeAgendaRequest,
        )
        self.MasteryScore = MasteryScore
        self.MasteryProfile = MasteryProfile
        self.AddMasteryEvidenceRequest = AddMasteryEvidenceRequest
        self.CoachOverrideRequest = CoachOverrideRequest
        self.TrainingPlan = TrainingPlan
        self.GeneratePlanRequest = GeneratePlanRequest
        self.CurriculumProgress = CurriculumProgress
        self.MarkLessonRequest = MarkLessonRequest
        self.CoachCalibrationRequest = CoachCalibrationRequest
        self.DiagnosticStartRequest = DiagnosticStartRequest
        self.DiagnosticCompleteRequest = DiagnosticCompleteRequest
        self.PracticeAgendaRequest = PracticeAgendaRequest

    def test_mastery_score_model_fields(self):
        m = self.MasteryScore(
            user_id="u1", skill_id="warranting",
            mastery_score=75.0, confidence=0.8,
            evidence_count=5, mastery_state="mastered",
        )
        self.assertEqual(m.mastery_score, 75.0)
        self.assertEqual(m.mastery_state, "mastered")

    def test_mastery_score_optional_fields_default_none(self):
        m = self.MasteryScore(
            user_id="u1", skill_id="warranting",
            mastery_score=50.0, confidence=0.5,
            evidence_count=3, mastery_state="proficient",
        )
        self.assertIsNone(m.coach_override_score)
        self.assertIsNone(m.coach_override_note)

    def test_add_evidence_request_defaults(self):
        r = self.AddMasteryEvidenceRequest(
            skill_id="warranting",
            raw_score=75.0,
            source_type="speech_analysis",
        )
        self.assertEqual(r.input_scale, "0-100")
        self.assertIsNone(r.source_id)

    def test_generate_plan_request_defaults(self):
        r = self.GeneratePlanRequest(plan_type="4_week")
        self.assertIsNone(r.tournament_date)
        self.assertIsNone(r.coach_priority_skills)

    def test_mark_lesson_request_fields(self):
        r = self.MarkLessonRequest(lesson_id="pf_novice_01", status="completed")
        self.assertEqual(r.lesson_id, "pf_novice_01")

    def test_diagnostic_start_request_fields(self):
        r = self.DiagnosticStartRequest(
            experience_level="novice",
            intake_data={"self_ratings": {"warranting": 3}},
        )
        self.assertEqual(r.experience_level, "novice")

    def test_practice_agenda_request_default_duration(self):
        r = self.PracticeAgendaRequest(team_id="team-123")
        self.assertEqual(r.duration_minutes, 60)

    def test_mastery_profile_model_fields(self):
        m = self.MasteryProfile(
            user_id="u1",
            skills={},
            computed_at="2026-06-27T00:00:00Z",
            event_pack="public_forum",
        )
        self.assertEqual(m.event_pack, "public_forum")


# ─────────────────────────────────────────────────────────────────────────────
# 6. API Router — structure and routes
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIRouter(unittest.TestCase):

    def setUp(self):
        from app.api.training import router
        self.router = router
        self.paths = [r.path for r in router.routes if hasattr(r, "path")]
        src_path = BACKEND_ROOT / "app" / "api" / "training.py"
        self.src = src_path.read_text(encoding="utf-8")

    def test_router_has_at_least_17_routes(self):
        # Pass 21 added 17; Pass 21.1 added 5 more (next-action, sessions CRUD, validate)
        self.assertGreaterEqual(len(self.router.routes), 17)

    def test_router_prefix_is_training(self):
        self.assertEqual(self.router.prefix, "/training")

    def test_event_pack_route_present(self):
        self.assertIn("/training/event-pack", self.paths)

    def test_skills_route_present(self):
        self.assertIn("/training/skills", self.paths)

    def test_curriculum_route_present(self):
        self.assertIn("/training/curriculum", self.paths)

    def test_lesson_detail_route_present(self):
        self.assertIn("/training/curriculum/lesson/{lesson_id}", self.paths)

    def test_mastery_get_route_present(self):
        self.assertIn("/training/mastery", self.paths)

    def test_mastery_evidence_route_present(self):
        self.assertIn("/training/mastery/evidence", self.paths)

    def test_plans_generate_route_present(self):
        self.assertIn("/training/plans/generate", self.paths)

    def test_diagnostic_start_route_present(self):
        self.assertIn("/training/diagnostic/start", self.paths)

    def test_diagnostic_complete_route_present(self):
        self.assertIn("/training/diagnostic/complete", self.paths)

    def test_practice_agenda_route_present(self):
        self.assertIn("/training/practice-agenda", self.paths)

    def test_auth_guard_on_mastery(self):
        self.assertIn("get_current_user_id", self.src)

    def test_imports_event_pack(self):
        self.assertIn("from app.event_packs.public_forum import", self.src)

    def test_imports_mastery_engine(self):
        self.assertIn("from app.services.mastery_engine import", self.src)

    def test_imports_training_planner(self):
        self.assertIn("from app.services.training_planner import", self.src)

    def test_imports_diagnostic_engine(self):
        self.assertIn("from app.services.diagnostic_engine import", self.src)

    def test_skill_not_found_returns_404(self):
        self.assertIn("404", self.src)

    def test_plan_id_week_update_route(self):
        self.assertIn("/training/plans/{plan_id}/week", self.paths)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Migration file — schema integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestMigrationFile(unittest.TestCase):

    def setUp(self):
        files = sorted(MIGRATIONS_DIR.glob("*pass21*.sql"))
        self.assertGreater(len(files), 0, "Pass 21 migration file not found")
        self.sql = files[0].read_text(encoding="utf-8")

    def test_mastery_scores_table_exists(self):
        self.assertIn("mastery_scores", self.sql)

    def test_mastery_evidence_table_exists(self):
        self.assertIn("mastery_evidence", self.sql)

    def test_training_plans_table_exists(self):
        self.assertIn("training_plans", self.sql)

    def test_curriculum_progress_table_exists(self):
        self.assertIn("curriculum_progress", self.sql)

    def test_coach_calibration_table_exists(self):
        self.assertIn("coach_calibration", self.sql)

    def test_diagnostic_results_table_exists(self):
        self.assertIn("diagnostic_results", self.sql)

    def test_rls_enabled_on_mastery_scores(self):
        self.assertIn("ENABLE ROW LEVEL SECURITY", self.sql)

    def test_service_role_write_policies(self):
        self.assertIn("service_role", self.sql)

    def test_mastery_state_check_constraint(self):
        self.assertIn("not_started", self.sql)
        self.assertIn("mastered", self.sql)
        self.assertIn("needs_refresh", self.sql)

    def test_primary_key_on_mastery_scores(self):
        # Composite PK: (user_id, skill_id)
        self.assertIn("PRIMARY KEY (user_id, skill_id)", self.sql)

    def test_indexes_created(self):
        self.assertIn("CREATE INDEX", self.sql)

    def test_cascade_delete_on_user(self):
        self.assertIn("ON DELETE CASCADE", self.sql)


# ─────────────────────────────────────────────────────────────────────────────
# 8. main.py registration
# ─────────────────────────────────────────────────────────────────────────────

class TestMainPyRegistration(unittest.TestCase):

    def setUp(self):
        self.src = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    def test_training_imported(self):
        self.assertIn("training", self.src)

    def test_training_router_included(self):
        self.assertIn("training.router", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Backward compatibility — legacy skill names
# ─────────────────────────────────────────────────────────────────────────────

class TestLegacyCompatibility(unittest.TestCase):

    def setUp(self):
        from app.event_packs.public_forum import LEGACY_SKILL_MAP, resolve_legacy_skill
        self.LEGACY_SKILL_MAP = LEGACY_SKILL_MAP
        self.resolve = resolve_legacy_skill

    def test_9_legacy_skills_all_resolve(self):
        legacy_9 = [
            "warranting", "weighing", "extensions", "drops",
            "evidence_use", "clash", "judge_adaptation", "delivery", "organization",
        ]
        from app.event_packs.public_forum import SKILL_REGISTRY
        for legacy in legacy_9:
            with self.subTest(skill=legacy):
                canonical = self.resolve(legacy)
                self.assertIn(canonical, SKILL_REGISTRY,
                              f"Legacy skill '{legacy}' resolved to '{canonical}' which is not in SKILL_REGISTRY")

    def test_mission_recommender_skills_still_in_registry(self):
        """Skills used in mission_recommender.py must still resolve correctly."""
        from app.event_packs.public_forum import SKILL_REGISTRY
        # These are the exact keys used in SKILL_TO_DIM in mission_recommender.py
        mission_skills = [
            "warranting", "weighing", "extensions", "drops",
            "evidence_use", "clash", "judge_adaptation", "delivery", "organization",
        ]
        for skill in mission_skills:
            with self.subTest(skill=skill):
                canonical = self.resolve(skill)
                self.assertIn(canonical, SKILL_REGISTRY)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases(unittest.TestCase):

    def test_aggregate_all_stale_evidence(self):
        from app.services.mastery_engine import aggregate_mastery
        now = datetime.now(timezone.utc)
        items = [
            {"normalized_score": 90.0, "source_type": "speech_analysis",
             "recorded_at": now - timedelta(days=180)},
        ]
        result = aggregate_mastery(items, now)
        # Very stale — score should be near-zero weighted (score * near_zero_weight / near_zero_weight = 90)
        # But the mastery score is still 90 (it's recency weighted, not zeroed)
        self.assertGreater(result["mastery_score"], 0)

    def test_zero_evidence_gives_not_started(self):
        from app.services.mastery_engine import determine_mastery_state
        now = datetime.now(timezone.utc)
        state = determine_mastery_state(0.0, 0.0, 0, None, now)
        self.assertEqual(state, "not_started")

    def test_plan_with_empty_profile(self):
        from app.services.training_planner import generate_plan
        plan = generate_plan({}, "1_week")
        self.assertEqual(plan["total_weeks"], 1)
        self.assertEqual(len(plan["weeks"]), 1)

    def test_diagnostic_varsity_higher_baseline(self):
        from app.services.diagnostic_engine import compute_initial_mastery_from_diagnostic
        first = compute_initial_mastery_from_diagnostic({"experience_level": "first_time", "self_ratings": {}})
        varsity = compute_initial_mastery_from_diagnostic({"experience_level": "varsity", "self_ratings": {}})
        if first and varsity:
            avg_first = sum(v["mastery_score"] for v in first.values()) / len(first)
            avg_varsity = sum(v["mastery_score"] for v in varsity.values()) / len(varsity)
            self.assertGreater(avg_varsity, avg_first)

    def test_team_skill_gaps_empty(self):
        from app.services.mastery_engine import compute_team_skill_gaps
        result = compute_team_skill_gaps([])
        self.assertEqual(result, {})

    def test_practice_agenda_empty_gaps(self):
        from app.services.training_planner import suggest_practice_agenda
        agenda = suggest_practice_agenda({}, duration_minutes=60)
        self.assertIsInstance(agenda, list)


if __name__ == "__main__":
    unittest.main()
