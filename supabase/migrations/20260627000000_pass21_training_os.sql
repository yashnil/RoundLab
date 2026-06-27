-- Pass 21: Training OS
-- Adds: mastery_scores, mastery_evidence, training_plans,
--        curriculum_progress, coach_calibration, diagnostic_results
-- No existing table is altered.

-- ── mastery_scores ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mastery_scores (
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    skill_id        TEXT NOT NULL,
    mastery_score   NUMERIC(5,2) NOT NULL DEFAULT 0
                        CHECK (mastery_score >= 0 AND mastery_score <= 100),
    confidence      NUMERIC(4,3) NOT NULL DEFAULT 0
                        CHECK (confidence >= 0 AND confidence <= 1),
    evidence_count  INT NOT NULL DEFAULT 0,
    mastery_state   TEXT NOT NULL DEFAULT 'not_started'
                        CHECK (mastery_state IN (
                            'not_started','introduced','developing',
                            'proficient','mastered','needs_refresh'
                        )),
    coach_override_score  NUMERIC(5,2),
    coach_override_note   TEXT,
    coach_overridden_by   UUID REFERENCES auth.users(id),
    last_demonstrated_at  TIMESTAMPTZ,
    recurring_weakness    INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, skill_id)
);

-- ── mastery_evidence ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mastery_evidence (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    skill_id         TEXT NOT NULL,
    raw_score        NUMERIC(5,2) NOT NULL,
    normalized_score NUMERIC(5,2) NOT NULL,
    source_type      TEXT NOT NULL CHECK (source_type IN (
                         'speech_analysis','drill_attempt','re_record',
                         'coach_review','tournament_workout',
                         'judge_adaptation_exercise','full_round'
                     )),
    source_id        TEXT,
    change_reason    TEXT,
    recorded_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── training_plans ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS training_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_type    TEXT NOT NULL CHECK (plan_type IN (
                     '1_week','4_week','tournament_countdown','custom'
                 )),
    event_pack   TEXT NOT NULL DEFAULT 'public_forum',
    current_week INT NOT NULL DEFAULT 1,
    total_weeks  INT NOT NULL DEFAULT 4,
    weeks        JSONB NOT NULL DEFAULT '[]',
    status       TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active','paused','completed','abandoned')),
    tournament_date DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── curriculum_progress ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS curriculum_progress (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    lesson_id    TEXT NOT NULL,
    event_pack   TEXT NOT NULL DEFAULT 'public_forum',
    status       TEXT NOT NULL DEFAULT 'not_started'
                     CHECK (status IN (
                         'not_started','in_progress','completed','skipped'
                     )),
    score        NUMERIC(5,2),
    completed_at TIMESTAMPTZ,
    coach_note   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, lesson_id)
);

-- ── coach_calibration ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS coach_calibration (
    team_id        UUID PRIMARY KEY REFERENCES teams(id) ON DELETE CASCADE,
    standard       TEXT NOT NULL DEFAULT 'novice'
                       CHECK (standard IN ('novice','jv','varsity')),
    judge_emphasis TEXT NOT NULL DEFAULT 'lay'
                       CHECK (judge_emphasis IN ('lay','flow','technical','mixed')),
    rubric_weights JSONB NOT NULL DEFAULT '{}',
    preferences    JSONB NOT NULL DEFAULT '{}',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     UUID REFERENCES auth.users(id)
);

-- ── diagnostic_results ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostic_results (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_pack       TEXT NOT NULL DEFAULT 'public_forum',
    experience_level TEXT NOT NULL DEFAULT 'novice'
                         CHECK (experience_level IN (
                             'first_time','novice','jv','varsity'
                         )),
    intake_data      JSONB NOT NULL DEFAULT '{}',
    strengths        TEXT[] NOT NULL DEFAULT '{}',
    priorities       TEXT[] NOT NULL DEFAULT '{}',
    recommended_track TEXT,
    confidence_note  TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','in_progress','completed')),
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Row Level Security ──────────────────────────────────────────────────────
ALTER TABLE mastery_scores      ENABLE ROW LEVEL SECURITY;
ALTER TABLE mastery_evidence    ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_plans      ENABLE ROW LEVEL SECURITY;
ALTER TABLE curriculum_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE coach_calibration   ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnostic_results  ENABLE ROW LEVEL SECURITY;

-- Users see their own data
CREATE POLICY "user_own_mastery"
    ON mastery_scores FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_own_mastery_evidence"
    ON mastery_evidence FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_own_plan"
    ON training_plans FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_own_curriculum"
    ON curriculum_progress FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_own_diagnostic"
    ON diagnostic_results FOR SELECT USING (auth.uid() = user_id);

-- Team members see their team's calibration
CREATE POLICY "team_member_calibration"
    ON coach_calibration FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM team_members tm
        WHERE tm.team_id = coach_calibration.team_id
          AND tm.user_id = auth.uid()
    ));

-- Service role handles all writes
CREATE POLICY "service_mastery_write"
    ON mastery_scores FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "service_mastery_evidence_write"
    ON mastery_evidence FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "service_plan_write"
    ON training_plans FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "service_curriculum_write"
    ON curriculum_progress FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "service_calibration_write"
    ON coach_calibration FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "service_diagnostic_write"
    ON diagnostic_results FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX idx_mastery_scores_user
    ON mastery_scores(user_id);

CREATE INDEX idx_mastery_evidence_user_skill
    ON mastery_evidence(user_id, skill_id);

CREATE INDEX idx_training_plans_user
    ON training_plans(user_id) WHERE status = 'active';

CREATE INDEX idx_curriculum_progress_user
    ON curriculum_progress(user_id);

CREATE INDEX idx_diagnostic_results_user
    ON diagnostic_results(user_id);
