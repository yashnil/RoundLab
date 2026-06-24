-- Pass 16.1: Round legality checks table
-- Depends on: round_simulations, round_speeches (Pass 16)
-- Populated by the decision engine when processing speech legality_violations JSONB.

CREATE TABLE IF NOT EXISTS round_legality_checks (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id              uuid NOT NULL REFERENCES round_simulations(id) ON DELETE CASCADE,
    speech_id             uuid REFERENCES round_speeches(id) ON DELETE SET NULL,
    phase                 text,
    speaker_side          text CHECK (speaker_side IN ('pro','con')),
    violation_category    text,  -- e.g. 'new_argument','paraphrasing','time_violation'
    violation_description text NOT NULL,
    is_violation          boolean NOT NULL DEFAULT true,
    severity              text NOT NULL DEFAULT 'medium'
                          CHECK (severity IN ('critical','high','medium','low')),
    auto_detected         boolean NOT NULL DEFAULT true,
    created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_round_legality_checks_round
    ON round_legality_checks (round_id);
CREATE INDEX IF NOT EXISTS idx_round_legality_checks_violation
    ON round_legality_checks (round_id, is_violation);

ALTER TABLE round_legality_checks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "round_legality_checks_read" ON round_legality_checks
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM round_simulations rs
                WHERE rs.id = round_legality_checks.round_id AND rs.user_id = auth.uid())
    );

CREATE POLICY "round_legality_checks_service_role" ON round_legality_checks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Also add FK from frontline_performance_log to round_simulations now that
-- round_simulations exists.
ALTER TABLE frontline_performance_log
    ADD COLUMN IF NOT EXISTS round_simulation_id uuid
        REFERENCES round_simulations(id) ON DELETE SET NULL;

NOTIFY pgrst, 'reload schema';
