-- ============================================================================
-- Fix team_members RLS infinite recursion + harden security-definer helpers.
--
-- Root cause (present since 20260602000000_add_teams.sql):
--   CREATE POLICY "team_members: select own"
--   USING (EXISTS (SELECT 1 FROM public.team_members tm WHERE tm.user_id = auth.uid() ...))
--   → Querying public.team_members from within a public.team_members policy
--     triggers the same policy, causing infinite recursion.
--
-- This was latent until Pass 21 added cross-table policies that queried
-- team_members, funnelling the recursion through the evaluator.
--
-- Fix strategy
-- ─────────────
-- Introduce SECURITY DEFINER helpers that run under the owning role (postgres),
-- which has no RLS. Every team-membership check in RLS goes through these
-- helpers — never a raw SELECT on public.team_members from within a policy.
--
-- Security invariants of the helpers
-- ────────────────────────────────────
-- • They accept NO caller-identity parameter (no arbitrary-UUID oracle risk).
--   The calling user is derived exclusively from auth.uid() inside the function.
-- • SET search_path = '' forces all references to be fully-qualified and
--   prevents search_path hijacking.
-- • REVOKE ALL ... FROM PUBLIC prevents anon/unauthenticated callers from
--   invoking them as membership probes.
-- • Only `authenticated` receives EXECUTE — service_role bypasses RLS and
--   never needs these helpers.
-- ============================================================================


-- ── 1. New hardened security-definer helpers ──────────────────────────────────

-- Returns the set of team_ids the calling user belongs to.
-- Used by: team_members coach-sees-team policy.
CREATE OR REPLACE FUNCTION public.current_user_team_ids()
RETURNS SETOF uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT team_id
  FROM public.team_members AS tm
  WHERE tm.user_id = auth.uid();
$$;

-- Returns true when the calling user is a coach on ANY team that also
-- contains student_uid. Used by mastery_scores, mastery_evidence,
-- training_plans, training_sessions SELECT policies.
CREATE OR REPLACE FUNCTION public.current_user_is_coach_of(student_uid uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.team_members AS c
    JOIN public.team_members AS s ON s.team_id = c.team_id
    WHERE c.user_id = auth.uid()
      AND c.role = 'coach'
      AND s.user_id = student_uid
  );
$$;

-- Returns true when the calling user is a member (any role) of team tid.
-- Used by: coach_calibration SELECT policy.
CREATE OR REPLACE FUNCTION public.current_user_is_team_member(tid uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.team_members AS tm
    WHERE tm.user_id = auth.uid()
      AND tm.team_id = tid
  );
$$;

-- Returns true when the calling user is a coach (role = 'coach') on team tid.
-- Used by: team_members SELECT coach policy (lets coaches see their roster).
CREATE OR REPLACE FUNCTION public.current_user_is_team_coach(tid uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.team_members AS tm
    WHERE tm.user_id = auth.uid()
      AND tm.team_id = tid
      AND tm.role = 'coach'
  );
$$;


-- ── 2. Restrict execution: revoke PUBLIC default, grant authenticated only ────

REVOKE ALL ON FUNCTION public.current_user_team_ids()           FROM PUBLIC;
REVOKE ALL ON FUNCTION public.current_user_is_coach_of(uuid)    FROM PUBLIC;
REVOKE ALL ON FUNCTION public.current_user_is_team_member(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.current_user_is_team_coach(uuid)  FROM PUBLIC;

-- service_role bypasses RLS and never calls these helpers — omit it deliberately.
GRANT EXECUTE ON FUNCTION public.current_user_team_ids()           TO authenticated;
GRANT EXECUTE ON FUNCTION public.current_user_is_coach_of(uuid)    TO authenticated;
GRANT EXECUTE ON FUNCTION public.current_user_is_team_member(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.current_user_is_team_coach(uuid)  TO authenticated;


-- ── 3. Fix team_members SELECT policies ──────────────────────────────────────
--
-- Policy design:
--   • Students see ONLY their own row (not teammates').
--     If a student could see teammates, they could enumerate the roster.
--   • Coaches see every row on teams they coach.
--     Uses current_user_is_team_coach() — SECURITY DEFINER, no recursion.

DROP POLICY IF EXISTS "team_members: select own"        ON public.team_members;
DROP POLICY IF EXISTS "team_members: coach sees team"   ON public.team_members;

CREATE POLICY "team_members_select_own"
  ON public.team_members
  FOR SELECT
  USING (user_id = auth.uid());

-- Coaches see the full roster of any team they coach.
CREATE POLICY "team_members_select_coached_team"
  ON public.team_members
  FOR SELECT
  USING (public.current_user_is_team_coach(team_id));


-- ── 4. Training OS table policies — replace old helpers ───────────────────────

-- mastery_scores: own row OR coach of that student
DROP POLICY IF EXISTS "user_own_mastery"                ON public.mastery_scores;
DROP POLICY IF EXISTS "coach_reads_team_mastery_scores" ON public.mastery_scores;
DROP POLICY IF EXISTS "mastery_scores_select"           ON public.mastery_scores;

CREATE POLICY "mastery_scores_select"
  ON public.mastery_scores
  FOR SELECT
  USING (
    auth.uid() = user_id
    OR public.current_user_is_coach_of(user_id)
  );

-- mastery_evidence: own row OR coach of that student
DROP POLICY IF EXISTS "user_own_mastery_evidence"           ON public.mastery_evidence;
DROP POLICY IF EXISTS "coach_reads_team_mastery_evidence"   ON public.mastery_evidence;
DROP POLICY IF EXISTS "mastery_evidence_select"             ON public.mastery_evidence;

CREATE POLICY "mastery_evidence_select"
  ON public.mastery_evidence
  FOR SELECT
  USING (
    auth.uid() = user_id
    OR public.current_user_is_coach_of(user_id)
  );

-- training_plans: own row OR coach of that student
DROP POLICY IF EXISTS "user_own_plan"                   ON public.training_plans;
DROP POLICY IF EXISTS "coach_reads_team_training_plans" ON public.training_plans;
DROP POLICY IF EXISTS "training_plans_select"           ON public.training_plans;

CREATE POLICY "training_plans_select"
  ON public.training_plans
  FOR SELECT
  USING (
    auth.uid() = user_id
    OR public.current_user_is_coach_of(user_id)
  );

-- training_sessions: own row OR coach of that student
DROP POLICY IF EXISTS "user_own_sessions"               ON public.training_sessions;
DROP POLICY IF EXISTS "coach_see_student_sessions"      ON public.training_sessions;
DROP POLICY IF EXISTS "training_sessions_coach_select"  ON public.training_sessions;

CREATE POLICY "training_sessions_select"
  ON public.training_sessions
  FOR SELECT
  USING (
    auth.uid() = user_id
    OR public.current_user_is_coach_of(user_id)
  );


-- ── 5. coach_calibration: harden SELECT, remove direct-write policy ───────────
--
-- All writes go through the backend service-role client (get_supabase() returns
-- a service_role client; see app/services/supabase_client.py). The existing
-- "service_calibration_write ALL" policy already covers service_role writes.
-- The "coach_calibration_write" INSERT policy is therefore redundant and creates
-- a direct-write surface for authenticated browsers — remove it.

DROP POLICY IF EXISTS "team_member_calibration"     ON public.coach_calibration;
DROP POLICY IF EXISTS "coach_calibration_select"    ON public.coach_calibration;
DROP POLICY IF EXISTS "coach_calibration_write"     ON public.coach_calibration;

-- Any team member (student or coach) may read calibration for their team.
CREATE POLICY "coach_calibration_select"
  ON public.coach_calibration
  FOR SELECT
  USING (public.current_user_is_team_member(team_id));

-- No INSERT/UPDATE/DELETE policy for authenticated — service_role handles writes.


-- ── 6. Drop old arbitrary-UUID oracle functions ───────────────────────────────
--
-- These accepted caller-identity UUIDs as arguments, allowing any authenticated
-- user to probe membership for arbitrary UUIDs:
--   SELECT get_user_team_ids('victim-uuid');
--
-- All policies have been migrated to current_user_* helpers above.

DROP FUNCTION IF EXISTS public.get_user_team_ids(uuid);
DROP FUNCTION IF EXISTS public.is_coach_of(uuid, uuid);
DROP FUNCTION IF EXISTS public.is_team_member_of(uuid, uuid);
