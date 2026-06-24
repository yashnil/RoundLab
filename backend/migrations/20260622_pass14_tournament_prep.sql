-- Pass 14 — Tournament Prep Intelligence, Evidence Freshness, and Gap-Driven Workouts
-- Apply via Supabase SQL editor or psql.
-- All tables reference Pass 13 entities where applicable.
-- Rollback: see DROP TABLE statements at the bottom (commented out by default).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. prep_workspaces
--    One per (user_id, resolution_id) pair; scoped to a resolution + optional side.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prep_workspaces (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id         uuid,
    resolution_id   uuid REFERENCES resolutions(id) ON DELETE CASCADE,
    side            text NOT NULL DEFAULT 'both'
        CHECK (side IN ('pro', 'con', 'both')),
    tournament_date date,
    judge_emphasis  text,           -- e.g. "lay", "flow", "tech"
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, resolution_id, side)
);

CREATE INDEX IF NOT EXISTS prep_workspaces_user_idx        ON prep_workspaces (user_id);
CREATE INDEX IF NOT EXISTS prep_workspaces_resolution_idx  ON prep_workspaces (resolution_id);
CREATE INDEX IF NOT EXISTS prep_workspaces_team_idx        ON prep_workspaces (team_id) WHERE team_id IS NOT NULL;

ALTER TABLE prep_workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY prep_workspaces_owner ON prep_workspaces FOR ALL USING (auth.uid() = user_id);
CREATE POLICY prep_workspaces_team_read ON prep_workspaces
    FOR SELECT USING (team_id IS NOT NULL AND team_id IN (
        SELECT team_id FROM team_members WHERE user_id = auth.uid()
    ));

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. prep_readiness_reports
--    Snapshot of readiness analysis at a point in time.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prep_readiness_reports (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id        uuid REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id             uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    resolution_id       uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    side                text NOT NULL DEFAULT 'both'
        CHECK (side IN ('pro', 'con', 'both')),
    generated_at        timestamptz NOT NULL DEFAULT now(),
    library_watermark   timestamptz,    -- latest updated_at in library at generation time
    tournament_date     date,
    -- Dimension scores 0-100; null = not enough data
    score_argument_coverage     integer CHECK (score_argument_coverage BETWEEN 0 AND 100),
    score_evidence_quality      integer CHECK (score_evidence_quality BETWEEN 0 AND 100),
    score_evidence_freshness    integer CHECK (score_evidence_freshness BETWEEN 0 AND 100),
    score_frontline_readiness   integer CHECK (score_frontline_readiness BETWEEN 0 AND 100),
    score_source_diversity      integer CHECK (score_source_diversity BETWEEN 0 AND 100),
    score_speech_stage_readiness integer CHECK (score_speech_stage_readiness BETWEEN 0 AND 100),
    score_weighing_preparation  integer CHECK (score_weighing_preparation BETWEEN 0 AND 100),
    composite_score             integer CHECK (composite_score BETWEEN 0 AND 100),
    -- Summary flags
    gap_count           integer NOT NULL DEFAULT 0,
    stale_card_count    integer NOT NULL DEFAULT 0,
    unsafe_card_count   integer NOT NULL DEFAULT 0,
    report_json         jsonb NOT NULL DEFAULT '{}',    -- full PrepReadinessReport payload
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS prep_reports_workspace_idx   ON prep_readiness_reports (workspace_id);
CREATE INDEX IF NOT EXISTS prep_reports_user_idx        ON prep_readiness_reports (user_id);
CREATE INDEX IF NOT EXISTS prep_reports_generated_idx   ON prep_readiness_reports (generated_at DESC);

ALTER TABLE prep_readiness_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY prep_reports_owner ON prep_readiness_reports FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. prep_gaps
--    Individual gaps detected in a readiness report.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prep_gaps (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       uuid REFERENCES prep_readiness_reports(id) ON DELETE CASCADE,
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    gap_category    text NOT NULL,
    severity        text NOT NULL DEFAULT 'medium'
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    title           text NOT NULL,
    reason          text NOT NULL,
    is_deterministic boolean NOT NULL DEFAULT true,
    -- Links back to library entities
    argument_id     uuid,
    blockfile_id    uuid,
    section_id      uuid,
    card_id         text,               -- evidence_cards.id (text, not uuid)
    frontline_id    uuid,
    -- Resolution metadata
    recommended_action text,
    estimated_minutes  integer,
    resolved        boolean NOT NULL DEFAULT false,
    resolved_at     timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS prep_gaps_report_idx     ON prep_gaps (report_id);
CREATE INDEX IF NOT EXISTS prep_gaps_user_idx       ON prep_gaps (user_id);
CREATE INDEX IF NOT EXISTS prep_gaps_severity_idx   ON prep_gaps (severity, resolved);
CREATE INDEX IF NOT EXISTS prep_gaps_category_idx   ON prep_gaps (gap_category);

ALTER TABLE prep_gaps ENABLE ROW LEVEL SECURITY;
CREATE POLICY prep_gaps_owner ON prep_gaps FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. prep_tasks
--    Derived or manually created tasks for tournament preparation.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prep_tasks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    uuid REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    assigned_by     uuid REFERENCES auth.users(id),    -- coach who assigned (null = self)
    gap_id          uuid REFERENCES prep_gaps(id) ON DELETE SET NULL,
    task_type       text NOT NULL DEFAULT 'research_evidence',
    title           text NOT NULL,
    reason          text,
    -- Library links
    argument_id     uuid,
    blockfile_id    uuid,
    card_id         text,
    frontline_id    uuid,
    -- Scheduling
    priority        integer NOT NULL DEFAULT 2          -- 1=highest, 3=lowest
        CHECK (priority BETWEEN 1 AND 3),
    estimated_minutes integer,
    due_date        date,
    status          text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
    completion_notes text,
    -- Audit
    is_auto_generated boolean NOT NULL DEFAULT false,
    completed_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS prep_tasks_workspace_idx ON prep_tasks (workspace_id);
CREATE INDEX IF NOT EXISTS prep_tasks_user_idx      ON prep_tasks (user_id);
CREATE INDEX IF NOT EXISTS prep_tasks_status_idx    ON prep_tasks (status, priority);
CREATE INDEX IF NOT EXISTS prep_tasks_gap_idx       ON prep_tasks (gap_id) WHERE gap_id IS NOT NULL;

ALTER TABLE prep_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY prep_tasks_owner ON prep_tasks FOR ALL USING (auth.uid() = user_id);
CREATE POLICY prep_tasks_assigned_read ON prep_tasks
    FOR SELECT USING (assigned_by = auth.uid());

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. prep_workouts
--    Gap-driven workouts tied to prep gaps and existing drill infrastructure.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prep_workouts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    uuid REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    gap_id          uuid REFERENCES prep_gaps(id) ON DELETE SET NULL,
    task_id         uuid REFERENCES prep_tasks(id) ON DELETE SET NULL,
    workout_type    text NOT NULL DEFAULT 'evidence_explanation',
    title           text NOT NULL,
    description     text,
    prompt          text NOT NULL,
    instructions    text,
    success_criteria jsonb NOT NULL DEFAULT '[]',   -- list of strings
    time_limit_seconds integer NOT NULL DEFAULT 90,
    -- Source evidence (immutable reference — never modified)
    source_card_id  text,
    source_card_tag text,
    source_card_body text,      -- snapshot at creation time
    -- Linked drill (if launched via drill system)
    drill_id        uuid,
    drill_attempt_id uuid,
    -- Status
    status          text NOT NULL DEFAULT 'not_started'
        CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
    completed_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS prep_workouts_workspace_idx  ON prep_workouts (workspace_id);
CREATE INDEX IF NOT EXISTS prep_workouts_user_idx       ON prep_workouts (user_id);
CREATE INDEX IF NOT EXISTS prep_workouts_gap_idx        ON prep_workouts (gap_id) WHERE gap_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS prep_workouts_status_idx     ON prep_workouts (status, user_id);

ALTER TABLE prep_workouts ENABLE ROW LEVEL SECURITY;
CREATE POLICY prep_workouts_owner ON prep_workouts FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- updated_at triggers
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION p14_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

CREATE OR REPLACE TRIGGER prep_workspaces_updated_at
    BEFORE UPDATE ON prep_workspaces
    FOR EACH ROW EXECUTE FUNCTION p14_set_updated_at();

CREATE OR REPLACE TRIGGER prep_tasks_updated_at
    BEFORE UPDATE ON prep_tasks
    FOR EACH ROW EXECUTE FUNCTION p14_set_updated_at();

CREATE OR REPLACE TRIGGER prep_workouts_updated_at
    BEFORE UPDATE ON prep_workouts
    FOR EACH ROW EXECUTE FUNCTION p14_set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────────
-- ROLLBACK (run manually if needed)
-- ─────────────────────────────────────────────────────────────────────────────
-- DROP TABLE IF EXISTS prep_workouts CASCADE;
-- DROP TABLE IF EXISTS prep_tasks CASCADE;
-- DROP TABLE IF EXISTS prep_gaps CASCADE;
-- DROP TABLE IF EXISTS prep_readiness_reports CASCADE;
-- DROP TABLE IF EXISTS prep_workspaces CASCADE;
-- DROP FUNCTION IF EXISTS p14_set_updated_at CASCADE;
