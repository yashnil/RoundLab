-- Pass 14: Tournament Prep Intelligence
-- Tables: prep_workspaces, prep_gaps, prep_readiness_reports, prep_tasks, prep_workouts
-- Depends on: auth.users, teams, resolutions (Pass 13), evidence_cards (Pass 8)

-- ── prep_workspaces ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prep_workspaces (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id         uuid REFERENCES teams(id) ON DELETE SET NULL,
    resolution_id   uuid NOT NULL REFERENCES resolutions(id) ON DELETE RESTRICT,
    side            text NOT NULL DEFAULT 'both'
                    CHECK (side IN ('pro','con','both')),
    tournament_date text,   -- ISO date string, nullable
    judge_emphasis  text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prep_workspaces_user ON prep_workspaces (user_id);
CREATE INDEX IF NOT EXISTS idx_prep_workspaces_resolution
    ON prep_workspaces (user_id, resolution_id);

ALTER TABLE prep_workspaces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prep_workspaces_owner" ON prep_workspaces
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "prep_workspaces_service_role" ON prep_workspaces
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── prep_gaps ─────────────────────────────────────────────────────────────────
-- Preparation gaps detected via coverage analysis or post-round reflection.
-- Columns for deduplication (fingerprint, occurrence_count, etc.) and
-- FK to round_simulations are added in Pass 16 and Pass 16.5 migrations.
CREATE TABLE IF NOT EXISTS prep_gaps (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id     uuid NOT NULL REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id          uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    category         text NOT NULL,
    severity         text NOT NULL CHECK (severity IN ('high','medium','low')),
    title            text NOT NULL,
    description      text,
    suggested_action text,
    auto_resolved    boolean NOT NULL DEFAULT false,
    resolved         boolean NOT NULL DEFAULT false,
    is_deterministic boolean NOT NULL DEFAULT true,
    estimated_minutes int,
    argument_id      uuid,   -- logical ref to arguments; no FK to avoid circular dep
    blockfile_id     uuid,
    section_id       uuid,
    card_id          uuid,
    frontline_id     uuid,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prep_gaps_workspace ON prep_gaps (workspace_id);
CREATE INDEX IF NOT EXISTS idx_prep_gaps_user ON prep_gaps (user_id);
CREATE INDEX IF NOT EXISTS idx_prep_gaps_category ON prep_gaps (workspace_id, category);

ALTER TABLE prep_gaps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prep_gaps_owner" ON prep_gaps
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "prep_gaps_service_role" ON prep_gaps
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── prep_readiness_reports ────────────────────────────────────────────────────
-- Point-in-time readiness snapshots; append-only (new row per refresh).
CREATE TABLE IF NOT EXISTS prep_readiness_reports (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id      uuid NOT NULL REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id           uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    resolution_id     uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    side              text NOT NULL DEFAULT 'both'
                      CHECK (side IN ('pro','con','both')),
    tournament_date   text,
    gap_count         int NOT NULL DEFAULT 0,
    stale_card_count  int NOT NULL DEFAULT 0,
    unsafe_card_count int NOT NULL DEFAULT 0,
    composite_score   int,
    report_json       jsonb NOT NULL DEFAULT '{}',
    generated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prep_readiness_reports_workspace
    ON prep_readiness_reports (workspace_id);
CREATE INDEX IF NOT EXISTS idx_prep_readiness_reports_user
    ON prep_readiness_reports (user_id, generated_at DESC);

ALTER TABLE prep_readiness_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prep_readiness_reports_owner" ON prep_readiness_reports
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "prep_readiness_reports_service_role" ON prep_readiness_reports
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── prep_tasks ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prep_tasks (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id       uuid NOT NULL REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id            uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    assigned_by        uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    gap_id             uuid REFERENCES prep_gaps(id) ON DELETE SET NULL,
    task_type          text NOT NULL DEFAULT 'research_evidence'
                       CHECK (task_type IN (
                           'research_evidence','replace_stale_card','verify_citation',
                           'strengthen_warrant','add_impact_evidence','find_counterevidence',
                           'build_frontline','add_weighing','write_summary_extension',
                           'write_final_focus_extension','complete_a_drill','review_unsafe_card'
                       )),
    title              text NOT NULL,
    reason             text,
    argument_id        uuid,   -- logical FK; no hard constraint to avoid circular deps
    blockfile_id       uuid,
    card_id            uuid,
    frontline_id       uuid,
    priority           int NOT NULL DEFAULT 2,
    estimated_minutes  int,
    due_date           text,   -- ISO date string
    status             text NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','in_progress','completed','skipped')),
    completion_notes   text,
    is_auto_generated  boolean NOT NULL DEFAULT false,
    completed_at       timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prep_tasks_workspace ON prep_tasks (workspace_id);
CREATE INDEX IF NOT EXISTS idx_prep_tasks_user ON prep_tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_prep_tasks_status ON prep_tasks (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_prep_tasks_priority ON prep_tasks (workspace_id, priority);

ALTER TABLE prep_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prep_tasks_owner" ON prep_tasks
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "prep_tasks_coach_read" ON prep_tasks
    FOR SELECT USING (auth.uid() = assigned_by);

CREATE POLICY "prep_tasks_service_role" ON prep_tasks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── prep_workouts ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prep_workouts (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id        uuid NOT NULL REFERENCES prep_workspaces(id) ON DELETE CASCADE,
    user_id             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    gap_id              uuid REFERENCES prep_gaps(id) ON DELETE SET NULL,
    task_id             uuid REFERENCES prep_tasks(id) ON DELETE SET NULL,
    source_card_id      uuid REFERENCES evidence_cards(id) ON DELETE SET NULL,
    drill_id            uuid,   -- FK to drills table managed separately
    drill_attempt_id    uuid,
    workout_type        text NOT NULL
                        CHECK (workout_type IN (
                            'evidence_explanation','card_comparison','frontline_speed',
                            'summary_extension','evidence_indictment','stale_evidence',
                            'lay_judge_evidence'
                        )),
    title               text NOT NULL,
    description         text,
    prompt              text NOT NULL,
    instructions        text,
    success_criteria    text[] NOT NULL DEFAULT '{}',
    time_limit_seconds  int NOT NULL DEFAULT 90,
    source_card_tag     text,
    source_card_body    text,   -- truncated snapshot; not the live card body
    status              text NOT NULL DEFAULT 'not_started'
                        CHECK (status IN ('not_started','in_progress','completed','skipped')),
    completed_at        timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prep_workouts_workspace ON prep_workouts (workspace_id);
CREATE INDEX IF NOT EXISTS idx_prep_workouts_user ON prep_workouts (user_id);
CREATE INDEX IF NOT EXISTS idx_prep_workouts_status ON prep_workouts (workspace_id, status);

ALTER TABLE prep_workouts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prep_workouts_owner" ON prep_workouts
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "prep_workouts_service_role" ON prep_workouts
    FOR ALL TO service_role USING (true) WITH CHECK (true);

NOTIFY pgrst, 'reload schema';
