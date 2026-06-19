-- =============================================================================
-- RoundLab — Team Assignments
-- Migration: 20260618000000_add_assignments.sql
--
-- Adds coach-authored assignments and per-student recipient records so coaches
-- can assign practice, track submission, and review work. Builds on teams /
-- team_members (20260602000000).
-- =============================================================================


-- =============================================================================
-- 1. ASSIGNMENTS TABLE  (one row per coach assignment)
-- =============================================================================

CREATE TABLE public.assignments (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id          uuid        NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
  created_by       uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title            text        NOT NULL,
  -- What the student should do. Maps to existing student routes.
  kind             text        NOT NULL DEFAULT 'speech',  -- speech | drill | rerecord
  speech_type      text,                                   -- constructive | rebuttal | summary | final_focus | crossfire
  side             text,                                   -- pro | con | null
  judge_type       text,                                   -- lay | flow | tech | coach | null
  topic            text,
  goal             text,
  success_criteria text[]      NOT NULL DEFAULT '{}',
  due_date         date,
  created_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.assignments IS 'Coach-authored practice assignments for a team.';
COMMENT ON COLUMN public.assignments.kind IS 'speech | drill | rerecord — selects the student route.';


-- =============================================================================
-- 2. ASSIGNMENT RECIPIENTS  (one row per assigned student)
-- =============================================================================

CREATE TABLE public.assignment_recipients (
  id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id        uuid        NOT NULL REFERENCES public.assignments(id) ON DELETE CASCADE,
  user_id              uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  -- assigned → submitted → reviewed | revision_requested
  status               text        NOT NULL DEFAULT 'assigned',
  submission_speech_id uuid        REFERENCES public.speeches(id) ON DELETE SET NULL,
  coach_feedback       text,
  reviewed_at          timestamptz,
  submitted_at         timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assignment_id, user_id)
);

COMMENT ON TABLE public.assignment_recipients IS 'Per-student status for an assignment.';
COMMENT ON COLUMN public.assignment_recipients.status IS 'assigned | submitted | reviewed | revision_requested';


-- =============================================================================
-- 3. ROW-LEVEL SECURITY
-- =============================================================================

ALTER TABLE public.assignments           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignment_recipients ENABLE ROW LEVEL SECURITY;

-- Helper predicate: is auth.uid() a coach of the given team?
-- (Inlined per policy since Postgres RLS can't share a function cheaply here.)

-- Assignments: any team member may read their team's assignments.
CREATE POLICY "assignments: select team members"
  ON public.assignments FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.team_id = assignments.team_id
        AND tm.user_id = auth.uid()
    )
  );

-- Assignments: only coaches of the team may create.
CREATE POLICY "assignments: insert coach"
  ON public.assignments FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.team_id = assignments.team_id
        AND tm.user_id = auth.uid()
        AND tm.role = 'coach'
    )
  );

-- Assignments: only coaches of the team may update/delete.
CREATE POLICY "assignments: modify coach"
  ON public.assignments FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.team_id = assignments.team_id
        AND tm.user_id = auth.uid()
        AND tm.role = 'coach'
    )
  );

-- Recipients: a student sees their own rows; coaches see all rows for their team's assignments.
CREATE POLICY "assignment_recipients: select own or coach"
  ON public.assignment_recipients FOR SELECT
  USING (
    user_id = auth.uid()
    OR EXISTS (
      SELECT 1
      FROM public.assignments a
      JOIN public.team_members tm ON tm.team_id = a.team_id
      WHERE a.id = assignment_recipients.assignment_id
        AND tm.user_id = auth.uid()
        AND tm.role = 'coach'
    )
  );

-- Recipients: the student may update their own row (to submit).
CREATE POLICY "assignment_recipients: update own"
  ON public.assignment_recipients FOR UPDATE
  USING (user_id = auth.uid());

-- Recipients: coaches of the team may update any recipient row (to review).
CREATE POLICY "assignment_recipients: update coach"
  ON public.assignment_recipients FOR UPDATE
  USING (
    EXISTS (
      SELECT 1
      FROM public.assignments a
      JOIN public.team_members tm ON tm.team_id = a.team_id
      WHERE a.id = assignment_recipients.assignment_id
        AND tm.user_id = auth.uid()
        AND tm.role = 'coach'
    )
  );

-- Recipients: coaches insert recipient rows when creating an assignment.
CREATE POLICY "assignment_recipients: insert coach"
  ON public.assignment_recipients FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.assignments a
      JOIN public.team_members tm ON tm.team_id = a.team_id
      WHERE a.id = assignment_recipients.assignment_id
        AND tm.user_id = auth.uid()
        AND tm.role = 'coach'
    )
  );


-- =============================================================================
-- 4. INDEXES
-- =============================================================================

CREATE INDEX idx_assignments_team_id            ON public.assignments (team_id);
CREATE INDEX idx_assignment_recipients_assignment ON public.assignment_recipients (assignment_id);
CREATE INDEX idx_assignment_recipients_user      ON public.assignment_recipients (user_id);
CREATE INDEX idx_assignment_recipients_status    ON public.assignment_recipients (status);
