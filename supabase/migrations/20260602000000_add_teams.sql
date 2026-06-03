-- =============================================================================
-- RoundLab — Add Teams Support
-- Migration: 20260602000000_add_teams.sql
--
-- Adds minimal team/organization support for coach pilot v1.
-- Allows coaches to create teams, invite students, and view progress.
-- =============================================================================


-- =============================================================================
-- 1. TEAMS TABLE
-- =============================================================================

CREATE TABLE public.teams (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name         text        NOT NULL,
  invite_code  text        UNIQUE NOT NULL,
  created_by   uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  created_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.teams IS 'Teams/organizations for coach pilot v1.';
COMMENT ON COLUMN public.teams.invite_code IS 'Short unique code students use to join (e.g. "DEBATE2024").';


-- =============================================================================
-- 2. TEAM MEMBERS TABLE
-- =============================================================================

CREATE TABLE public.team_members (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id    uuid        NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
  user_id    uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role       text        NOT NULL DEFAULT 'student',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (team_id, user_id)
);

COMMENT ON TABLE public.team_members IS 'Team membership with role (coach or student).';
COMMENT ON COLUMN public.team_members.role IS 'coach | student';


-- =============================================================================
-- 3. ROW-LEVEL SECURITY
-- =============================================================================

ALTER TABLE public.teams        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;

-- Teams: members can view their teams
CREATE POLICY "teams: select own"
  ON public.teams FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members
      WHERE team_members.team_id = teams.id
        AND team_members.user_id = auth.uid()
    )
  );

-- Teams: creator can insert
CREATE POLICY "teams: insert own"
  ON public.teams FOR INSERT
  WITH CHECK (auth.uid() = created_by);

-- Team members: members can view
CREATE POLICY "team_members: select own"
  ON public.team_members FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.team_id = team_members.team_id
        AND tm.user_id = auth.uid()
    )
  );

-- Team members: can insert self (for joining teams)
CREATE POLICY "team_members: insert self"
  ON public.team_members FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- =============================================================================
-- 4. INDEXES
-- =============================================================================

CREATE INDEX idx_teams_invite_code
  ON public.teams (invite_code);

CREATE INDEX idx_team_members_team_id
  ON public.team_members (team_id);

CREATE INDEX idx_team_members_user_id
  ON public.team_members (user_id);
