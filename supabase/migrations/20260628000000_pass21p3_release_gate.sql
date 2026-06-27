-- Pass 21.3: Training OS Production Release Gate
-- Closes proof, security, concurrency, and recovery gaps identified in 21–21.2.
--
-- Changes:
--   1. training_sessions.version — optimistic concurrency column
--   2. Composite source uniqueness on mastery_evidence
--      (replaces single-column source_id index; prevents cross-user collision)
--   3. coach_mastery_audit — authoritative trail for explicit coach overrides
--   4. coach_calibration.priority_skills_updated_at — track priority-only changes
--      so a priority override is never confused with a mastery signal

-- ── 1. Optimistic concurrency on training_sessions ───────────────────────────
ALTER TABLE training_sessions
    ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 0;

-- Every update must bump the version; the PATCH endpoint enforces this.
COMMENT ON COLUMN training_sessions.version IS
    'Monotonically increasing version; incremented on every successful PATCH. '
    'Clients supply expected_version; stale writes receive 409 Conflict.';

-- ── 2. Composite source uniqueness on mastery_evidence ───────────────────────
-- The previous single-column index on source_id was unsafe: two different users
-- whose events accidentally share the same source_id string (e.g. shared
-- drill template IDs) would conflict at the DB level.
-- The composite (user_id, source_type, source_id, skill_id) is safe and at
-- least as strict.
DROP INDEX IF EXISTS idx_mastery_evidence_source_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mastery_evidence_composite_source
    ON mastery_evidence(user_id, source_type, source_id, skill_id)
    WHERE source_id IS NOT NULL;

COMMENT ON INDEX idx_mastery_evidence_composite_source IS
    'Idempotent insert guard: (user, source_type, source_id, skill) must be '
    'unique. Replaces the old single-column source_id index.';

-- ── 3. Coach mastery audit ───────────────────────────────────────────────────
-- Records every explicit coach mastery override with enough context to audit:
--   - who changed what, when, why
--   - whether an observable artifact backs the change
-- A priority override (changing what to practice) does NOT write here or
-- to mastery_evidence.
CREATE TABLE IF NOT EXISTS coach_mastery_audit (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id        UUID NOT NULL REFERENCES auth.users(id),
    student_id      UUID NOT NULL REFERENCES auth.users(id),
    skill_id        TEXT NOT NULL,
    override_score  NUMERIC(5,2) NOT NULL
                        CHECK (override_score >= 0 AND override_score <= 100),
    -- 'mastery_override' = coach sets an authoritative score without evidence
    -- 'coach_performance_review' = coach evaluated real student performance
    override_type   TEXT NOT NULL CHECK (override_type IN (
                        'mastery_override', 'coach_performance_review'
                    )),
    reason          TEXT NOT NULL,
    -- artifact_id links to the speech/drill/assignment the coach reviewed
    -- NULL is allowed for mastery_override but should be documented in reason
    artifact_id     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE coach_mastery_audit ENABLE ROW LEVEL SECURITY;

-- Coaches can read their own audit entries
CREATE POLICY "coaches_read_own_audit" ON coach_mastery_audit
    FOR SELECT USING (auth.uid() = coach_id);

-- Students can read entries about themselves
CREATE POLICY "students_read_own_audit" ON coach_mastery_audit
    FOR SELECT USING (auth.uid() = student_id);

-- All writes go through service role (backend verifies coach authorization)
CREATE POLICY "service_write_audit" ON coach_mastery_audit
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

CREATE INDEX IF NOT EXISTS idx_coach_audit_student
    ON coach_mastery_audit(student_id, skill_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coach_audit_coach
    ON coach_mastery_audit(coach_id, created_at DESC);

-- ── 4. Track priority-only override timestamp ────────────────────────────────
-- Lets us prove that a "priority change" has a distinct timestamp from a
-- "mastery override" — useful in audits and in the unified_priority pipeline.
ALTER TABLE mastery_scores
    ADD COLUMN IF NOT EXISTS priority_override_at TIMESTAMPTZ;

COMMENT ON COLUMN mastery_scores.priority_override_at IS
    'Set when a coach changes practice priority WITHOUT changing mastery score. '
    'Never set when emitting evidence from actual performance.';
