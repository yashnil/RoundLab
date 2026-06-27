-- Pass 21.1: Training OS Integration
-- Adds:
--   1. Unique constraint on mastery_evidence(source_id) for idempotent inserts
--   2. training_sessions table for guided session player persistence
--   3. indexes for performance

-- ── Unique source_id on mastery_evidence ────────────────────────────────────
-- Prevents duplicate evidence from the same source event.
-- ON CONFLICT DO NOTHING lets callers be safely idempotent.
ALTER TABLE mastery_evidence
    ADD COLUMN IF NOT EXISTS source_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mastery_evidence_source_id
    ON mastery_evidence(source_id)
    WHERE source_id IS NOT NULL;

-- ── training_sessions ────────────────────────────────────────────────────────
-- Persists guided session state step-by-step.
CREATE TABLE IF NOT EXISTS training_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    lesson_id       TEXT NOT NULL,
    plan_id         UUID REFERENCES training_plans(id) ON DELETE SET NULL,
    current_step    TEXT NOT NULL DEFAULT 'lesson',
    steps_completed TEXT[] NOT NULL DEFAULT '{}',
    speech_id       UUID,
    drill_id        UUID,
    rerecord_id     UUID,
    mastery_before  JSONB,
    mastery_after   JSONB,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','paused','completed','abandoned')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    UNIQUE (user_id, lesson_id, status)
        DEFERRABLE INITIALLY IMMEDIATE
);

-- RLS
ALTER TABLE training_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_own_sessions" ON training_sessions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "service_sessions_write" ON training_sessions
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Coaches can see their students' sessions
CREATE POLICY "coach_see_student_sessions" ON training_sessions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM team_members coach_mem
            JOIN team_members student_mem
                ON coach_mem.team_id = student_mem.team_id
            WHERE coach_mem.user_id = auth.uid()
              AND coach_mem.role = 'coach'
              AND student_mem.user_id = training_sessions.user_id
        )
    );

CREATE INDEX IF NOT EXISTS idx_training_sessions_user
    ON training_sessions(user_id) WHERE status = 'active';

-- ── Additional performance indexes ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_mastery_evidence_user_skill_recorded
    ON mastery_evidence(user_id, skill_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_mastery_scores_state
    ON mastery_scores(user_id, mastery_state);
