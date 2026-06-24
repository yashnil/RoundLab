-- Pass 15: Judge Adaptation Simulator
-- Tables: judge_profiles, judge_adaptations, judge_adaptation_notes,
--         judge_workout_assignments
-- Depends on: auth.users, teams, evidence_cards, prep_workspaces (Pass 14)

-- ── judge_profiles ────────────────────────────────────────────────────────────
-- Custom user-defined judge profiles. Built-in profiles live in application code.
CREATE TABLE IF NOT EXISTS judge_profiles (
    id                           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                      uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id                      uuid REFERENCES teams(id) ON DELETE SET NULL,
    name                         text NOT NULL,
    base_type                    text NOT NULL DEFAULT 'custom'
                                 CHECK (base_type IN (
                                     'lay','parent','flow','technical','coach','custom'
                                 )),
    description                  text,
    is_public                    boolean NOT NULL DEFAULT false,
    -- 13 preference dimensions (1-5 integer scale)
    jargon_tolerance             int NOT NULL DEFAULT 3 CHECK (jargon_tolerance BETWEEN 1 AND 5),
    speed_tolerance              int NOT NULL DEFAULT 3 CHECK (speed_tolerance BETWEEN 1 AND 5),
    evidence_detail_preference   int NOT NULL DEFAULT 3 CHECK (evidence_detail_preference BETWEEN 1 AND 5),
    line_by_line_expectation     int NOT NULL DEFAULT 3 CHECK (line_by_line_expectation BETWEEN 1 AND 5),
    extension_strictness         int NOT NULL DEFAULT 3 CHECK (extension_strictness BETWEEN 1 AND 5),
    weighing_expectation         int NOT NULL DEFAULT 3 CHECK (weighing_expectation BETWEEN 1 AND 5),
    narrative_preference         int NOT NULL DEFAULT 3 CHECK (narrative_preference BETWEEN 1 AND 5),
    real_world_explanation       int NOT NULL DEFAULT 3 CHECK (real_world_explanation BETWEEN 1 AND 5),
    technical_rule_sensitivity   int NOT NULL DEFAULT 3 CHECK (technical_rule_sensitivity BETWEEN 1 AND 5),
    intervention_tolerance       int NOT NULL DEFAULT 3 CHECK (intervention_tolerance BETWEEN 1 AND 5),
    organization_preference      int NOT NULL DEFAULT 3 CHECK (organization_preference BETWEEN 1 AND 5),
    source_qualification_importance int NOT NULL DEFAULT 3
                                 CHECK (source_qualification_importance BETWEEN 1 AND 5),
    persuasion_vs_flow_emphasis  int NOT NULL DEFAULT 3
                                 CHECK (persuasion_vs_flow_emphasis BETWEEN 1 AND 5),
    created_at                   timestamptz NOT NULL DEFAULT now(),
    updated_at                   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_judge_profiles_user ON judge_profiles (user_id);
CREATE INDEX IF NOT EXISTS idx_judge_profiles_type ON judge_profiles (base_type);

ALTER TABLE judge_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "judge_profiles_owner" ON judge_profiles
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "judge_profiles_public_read" ON judge_profiles
    FOR SELECT USING (is_public = true);

CREATE POLICY "judge_profiles_service_role" ON judge_profiles
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── judge_adaptations ─────────────────────────────────────────────────────────
-- Stored adaptation results (changes + risks) for a user's content + judge type.
-- source_*_id columns are nullable UUIDs with no FK constraints because they
-- point to different tables depending on source_type.
CREATE TABLE IF NOT EXISTS judge_adaptations (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    workspace_id          uuid REFERENCES prep_workspaces(id) ON DELETE SET NULL,
    judge_type            text NOT NULL,
    source_type           text NOT NULL
                          CHECK (source_type IN (
                              'evidence','argument','frontline','section',
                              'summary','final_focus','transcript'
                          )),
    -- Dynamic source FK (which field is set depends on source_type)
    source_evidence_id    uuid,
    source_argument_id    uuid,
    source_frontline_id   uuid,
    source_section_id     uuid,
    source_summary_id     uuid,
    source_final_focus_id uuid,
    source_transcript_id  uuid,
    -- Serialized result
    result_json           jsonb NOT NULL DEFAULT '{}',
    risk_count            int NOT NULL DEFAULT 0,
    change_count          int NOT NULL DEFAULT 0,
    created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_judge_adaptations_user
    ON judge_adaptations (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_judge_adaptations_judge_type
    ON judge_adaptations (user_id, judge_type);
CREATE INDEX IF NOT EXISTS idx_judge_adaptations_workspace
    ON judge_adaptations (workspace_id);

ALTER TABLE judge_adaptations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "judge_adaptations_owner" ON judge_adaptations
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "judge_adaptations_service_role" ON judge_adaptations
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── judge_adaptation_notes ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS judge_adaptation_notes (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    adaptation_id uuid NOT NULL REFERENCES judge_adaptations(id) ON DELETE CASCADE,
    user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    judge_type    text NOT NULL,
    note_text     text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_judge_adaptation_notes_adaptation
    ON judge_adaptation_notes (adaptation_id);
CREATE INDEX IF NOT EXISTS idx_judge_adaptation_notes_user
    ON judge_adaptation_notes (user_id, created_at DESC);

ALTER TABLE judge_adaptation_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "judge_adaptation_notes_owner" ON judge_adaptation_notes
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "judge_adaptation_notes_service_role" ON judge_adaptation_notes
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── judge_workout_assignments ─────────────────────────────────────────────────
-- Coach-assigned judge adaptation workouts for students.
CREATE TABLE IF NOT EXISTS judge_workout_assignments (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assigned_by             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    assigned_to             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id                 uuid REFERENCES teams(id) ON DELETE SET NULL,
    source_card_id          uuid REFERENCES evidence_cards(id) ON DELETE SET NULL,
    judge_type              text NOT NULL,
    workout_type            text NOT NULL,
    title                   text NOT NULL,
    prompt                  text NOT NULL,
    instructions            text,
    success_criteria        text,
    time_limit_seconds      int,
    source_card_tag         text,
    source_card_body_snapshot text,  -- full snapshot at time of assignment
    status                  text NOT NULL DEFAULT 'assigned'
                            CHECK (status IN ('assigned','in_progress','completed','skipped')),
    student_notes           text,
    completed_at            timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_judge_workout_assignments_to
    ON judge_workout_assignments (assigned_to, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_judge_workout_assignments_by
    ON judge_workout_assignments (assigned_by);
CREATE INDEX IF NOT EXISTS idx_judge_workout_assignments_team
    ON judge_workout_assignments (team_id);

ALTER TABLE judge_workout_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "judge_workout_assignments_student" ON judge_workout_assignments
    FOR ALL USING (auth.uid() = assigned_to);

CREATE POLICY "judge_workout_assignments_coach_read" ON judge_workout_assignments
    FOR SELECT USING (auth.uid() = assigned_by);

CREATE POLICY "judge_workout_assignments_service_role" ON judge_workout_assignments
    FOR ALL TO service_role USING (true) WITH CHECK (true);

NOTIFY pgrst, 'reload schema';
