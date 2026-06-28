-- Dissio — Deterministic test-user application-data seed.
--
-- Auth users are created separately via the Supabase Auth Admin API
-- (see scripts/setup_local_test_env.sh) because direct bcrypt inserts
-- into auth.users require offline hash generation.
--
-- This file seeds all application-layer data: profiles, teams, memberships,
-- mastery scores, training plans, sessions, etc.
--
-- Stable UUIDs (used in Playwright constants and RLS test helpers):
--   Student A: 00000000-0000-0000-0001-000000000001  test_student_a@dissio.local
--   Coach A:   00000000-0000-0000-0002-000000000001  test_coach_a@dissio.local
--   Student B: 00000000-0000-0000-0001-000000000002  test_student_b@dissio.local
--   Coach B:   00000000-0000-0000-0002-000000000002  test_coach_b@dissio.local
--
-- Idempotent: safe to run multiple times.

BEGIN;

-- ── Profiles ──────────────────────────────────────────────────────────────────

INSERT INTO public.profiles (id, display_name, created_at)
VALUES
  ('00000000-0000-0000-0001-000000000001', 'Test Student A', now()),
  ('00000000-0000-0000-0002-000000000001', 'Test Coach A',   now()),
  ('00000000-0000-0000-0001-000000000002', 'Test Student B', now()),
  ('00000000-0000-0000-0002-000000000002', 'Test Coach B',   now())
ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name;

-- ── Teams ─────────────────────────────────────────────────────────────────────

INSERT INTO public.teams (id, name, invite_code, created_by, created_at)
VALUES
  ('00000000-0000-0000-0003-000000000001', 'Team A (Test)', 'TEAM-A-TEST', '00000000-0000-0000-0002-000000000001', now()),
  ('00000000-0000-0000-0003-000000000002', 'Team B (Test)', 'TEAM-B-TEST', '00000000-0000-0000-0002-000000000002', now())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- ── Team memberships ──────────────────────────────────────────────────────────

INSERT INTO public.team_members (team_id, user_id, role, created_at)
VALUES
  ('00000000-0000-0000-0003-000000000001', '00000000-0000-0000-0001-000000000001', 'student', now()),
  ('00000000-0000-0000-0003-000000000001', '00000000-0000-0000-0002-000000000001', 'coach',   now()),
  ('00000000-0000-0000-0003-000000000002', '00000000-0000-0000-0001-000000000002', 'student', now()),
  ('00000000-0000-0000-0003-000000000002', '00000000-0000-0000-0002-000000000002', 'coach',   now())
ON CONFLICT (team_id, user_id) DO NOTHING;

-- ── Initial mastery scores for Student A ─────────────────────────────────────

INSERT INTO public.mastery_scores (user_id, skill_id, mastery_score, confidence, evidence_count, mastery_state, updated_at)
VALUES
  ('00000000-0000-0000-0001-000000000001', 'warranting',       25.0, 0.4, 2, 'introduced',  now()),
  ('00000000-0000-0000-0001-000000000001', 'weighing',         15.0, 0.2, 1, 'introduced',  now()),
  ('00000000-0000-0000-0001-000000000001', 'extensions',       0.0,  0.0, 0, 'not_started', now()),
  ('00000000-0000-0000-0001-000000000001', 'responses',        10.0, 0.2, 1, 'introduced',  now()),
  ('00000000-0000-0000-0001-000000000001', 'clash',            0.0,  0.0, 0, 'not_started', now()),
  ('00000000-0000-0000-0001-000000000001', 'judge_adaptation', 0.0,  0.0, 0, 'not_started', now())
ON CONFLICT (user_id, skill_id) DO NOTHING;

-- ── One mastery evidence row for Student A ────────────────────────────────────

INSERT INTO public.mastery_evidence (
  id, user_id, skill_id, raw_score, normalized_score,
  source_type, source_id, change_reason, recorded_at
) VALUES (
  '00000000-0000-0000-0004-000000000001',
  '00000000-0000-0000-0001-000000000001',
  'warranting', 5.0, 25.0,
  'speech_analysis',
  'speech_analysis:seed-speech-001:warranting',
  'Seed evidence from initial practice speech',
  now() - INTERVAL '2 days'
) ON CONFLICT DO NOTHING;

-- ── Training plan for Student A ───────────────────────────────────────────────

INSERT INTO public.training_plans (
  id, user_id, plan_type, event_pack, current_week, total_weeks,
  weeks, status, created_at, updated_at
) VALUES (
  '00000000-0000-0000-0005-000000000001',
  '00000000-0000-0000-0001-000000000001',
  '4_week', 'public_forum', 1, 4,
  '[{"week":1,"skill_focus":"warranting","skill_name":"Warranting","objective":"Deepen your understanding of Warranting through targeted drill work.","lesson_id":"pf_novice_02","drill_description":"Take one of your constructive claims. Write it at the top of a page. Below it, complete this sentence five times: ''This is true because...''. Pick the most specific, mechanistic explanation. That''s your warrant.","speech_application":"After stating each claim in your constructive, say ''because'' out loud and complete the sentence with your warrant before moving to evidence.","completion_criteria":["Every claim in my speech is followed by a ''because'' explanation","My warrant describes a specific process or mechanism — not just ''studies show''","My warrant is different from my claim (not circular)","My evidence confirms the warrant mechanism, not just the conclusion"],"mastery_target":37.0,"estimated_hours":1.5},{"week":2,"skill_focus":"evidence_use","skill_name":"Evidence Use","objective":"Learn the fundamentals of Evidence Use and apply them in one practice speech.","lesson_id":"pf_novice_03","drill_description":"Find two pieces of evidence you use in your constructive. For each one, write: (1) the exact citation (author, year, publication), (2) the specific sentence or statistic that proves your claim, and (3) one sentence explaining the link.","speech_application":"In your next speech, pause before reading each card and state the citation out loud before the quoted text.","completion_criteria":["I cite author and year before every piece of evidence","The quoted text directly proves my specific claim","I explain how the evidence connects to my warrant after reading it"],"mastery_target":15.0,"estimated_hours":1.0},{"week":3,"skill_focus":"clash","skill_name":"Clash","objective":"Learn the fundamentals of Clash and apply them in one practice speech.","lesson_id":"pf_novice_04","drill_description":"Listen to a 2-minute speech (from a partner or recording). Write their arguments on a flow sheet. Then give a 90-second response covering their top argument with: name the argument, give your response, cite evidence if you have it.","speech_application":"In your next Rebuttal, name each argument you are answering before responding to it.","completion_criteria":["I respond to every opponent argument in my Rebuttal","I name each argument before I respond to it","I win at least one clash by out-evidencing the opponent"],"mastery_target":15.0,"estimated_hours":1.0},{"week":4,"skill_focus":"responses","skill_name":"Responses","objective":"Build consistency in Responses across multiple speech types.","lesson_id":null,"drill_description":"Practice responding to five opponent arguments in 90 seconds each. Label each response: Turn, Non-unique, Defensive, or Impact Take-out.","speech_application":"In your next Rebuttal, label each response type aloud before reading it.","completion_criteria":["I respond to every opponent argument in Rebuttal","I use at least two different response types","My responses are explained, not just asserted"],"mastery_target":22.0,"estimated_hours":1.5}]',
  'active', now(), now()
) ON CONFLICT (id) DO UPDATE SET weeks = EXCLUDED.weeks, updated_at = now();

-- ── Curriculum progress for Student A — pf_novice_01 in progress ─────────────

INSERT INTO public.curriculum_progress (id, user_id, lesson_id, event_pack, status, created_at)
VALUES (
  '00000000-0000-0000-0006-000000000001',
  '00000000-0000-0000-0001-000000000001',
  'pf_novice_01', 'public_forum', 'in_progress', now()
) ON CONFLICT (user_id, lesson_id) DO NOTHING;

-- ── Diagnostic result for Student A ─────────────────────────────────────────

INSERT INTO public.diagnostic_results (
  id, user_id, event_pack, experience_level,
  intake_data, strengths, priorities, recommended_track,
  status, completed_at, created_at
) VALUES (
  '00000000-0000-0000-0007-000000000001',
  '00000000-0000-0000-0001-000000000001',
  'public_forum', 'novice',
  '{"rounds_completed":2,"biggest_challenge":"extensions","time_available":"30min"}',
  ARRAY['clarity','organization'],
  ARRAY['warranting','weighing','extensions'],
  'novice',
  'completed', now(), now()
) ON CONFLICT (id) DO NOTHING;

-- ── Active training session for Student A ────────────────────────────────────
-- Note: training_sessions has a DEFERRABLE unique constraint on (user_id, lesson_id, status)
-- which does not support ON CONFLICT as an arbiter; use INSERT ... WHERE NOT EXISTS instead.

INSERT INTO public.training_sessions (
  id, user_id, lesson_id, plan_id,
  current_step, steps_completed, status, version,
  started_at, last_active_at
)
SELECT
  '00000000-0000-0000-0008-000000000001',
  '00000000-0000-0000-0001-000000000001',
  'pf_novice_01',
  '00000000-0000-0000-0005-000000000001',
  'lesson', '{}', 'active', 0,
  now() - INTERVAL '10 minutes', now() - INTERVAL '2 minutes'
WHERE NOT EXISTS (
  SELECT 1 FROM public.training_sessions
  WHERE id = '00000000-0000-0000-0008-000000000001'
);

-- ── Coach calibration for Team A ─────────────────────────────────────────────

INSERT INTO public.coach_calibration (team_id, standard, judge_emphasis, updated_by, updated_at)
VALUES (
  '00000000-0000-0000-0003-000000000001',
  'novice', 'lay',
  '00000000-0000-0000-0002-000000000001',
  now()
) ON CONFLICT (team_id) DO NOTHING;

-- ── Local dev: explicit grants ────────────────────────────────────────────────
-- In Supabase cloud, migrations run as supabase_admin which has default
-- privileges granting SELECT/INSERT/UPDATE/DELETE to service_role/authenticated.
-- In local dev, migrations run as postgres which only gives DXTM (not ARWD).
-- These grants make the local environment match cloud behaviour.
-- They are IDEMPOTENT and safe to re-run.

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
  TO service_role, authenticated;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public
  TO service_role, authenticated;

COMMIT;

-- Summary
DO $$ BEGIN
  RAISE NOTICE 'Seed complete. Users seeded:';
  RAISE NOTICE '  test_student_a@dissio.local (00000000-0000-0000-0001-000000000001)';
  RAISE NOTICE '  test_coach_a@dissio.local   (00000000-0000-0000-0002-000000000001)';
  RAISE NOTICE '  test_student_b@dissio.local (00000000-0000-0000-0001-000000000002)';
  RAISE NOTICE '  test_coach_b@dissio.local   (00000000-0000-0000-0002-000000000002)';
  RAISE NOTICE '  Password for all accounts: Dissio_Test1!';
END $$;
