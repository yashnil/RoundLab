-- Pass 17 — Round quality: coach review, replay markers, finding ratings, strategic memory.
--
-- Tables are insert/append-only for annotations and ratings.
-- Coach feedback never alters historical speech or flow records.

-- ── Coach round annotations ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS round_coach_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES round_simulations(id) ON DELETE CASCADE,
    coach_id UUID NOT NULL,
    annotation_type TEXT NOT NULL CHECK (
        annotation_type IN ('speech_note', 'argument_note', 'correction', 'drill_assignment', 'highlight')
    ),
    target_id UUID,
    target_type TEXT CHECK (
        target_type IS NULL OR target_type IN ('speech', 'argument', 'drill', 'finding')
    ),
    content TEXT NOT NULL,
    is_correction BOOLEAN NOT NULL DEFAULT FALSE,
    finding_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coach_annotations_round
    ON round_coach_annotations (round_id);
CREATE INDEX IF NOT EXISTS idx_coach_annotations_coach
    ON round_coach_annotations (coach_id);

-- ── Automated finding ratings ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS round_finding_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES round_simulations(id) ON DELETE CASCADE,
    finding_id TEXT NOT NULL,
    rater_id UUID NOT NULL,
    rating TEXT NOT NULL CHECK (
        rating IN ('correct', 'partly_correct', 'incorrect', 'useful', 'not_useful')
    ),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (round_id, finding_id, rater_id)
);

CREATE INDEX IF NOT EXISTS idx_finding_ratings_round
    ON round_finding_ratings (round_id);

-- ── Opponent strategic memory (per-round) ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS round_strategic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES round_simulations(id) ON DELETE CASCADE,
    opponent_side TEXT NOT NULL,
    opponent_commitments JSONB NOT NULL DEFAULT '[]',
    student_commitments JSONB NOT NULL DEFAULT '[]',
    concessions JSONB NOT NULL DEFAULT '[]',
    contradictions JSONB NOT NULL DEFAULT '[]',
    unanswered_arguments JSONB NOT NULL DEFAULT '[]',
    abandoned_arguments JSONB NOT NULL DEFAULT '[]',
    evidence_read JSONB NOT NULL DEFAULT '[]',
    evidence_challenges JSONB NOT NULL DEFAULT '[]',
    strategic_priorities JSONB NOT NULL DEFAULT '[]',
    planned_collapse TEXT,
    judge_risk_notes JSONB NOT NULL DEFAULT '[]',
    remaining_phases JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (round_id)
);

-- ── Round replay markers ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS round_replay_markers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES round_simulations(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    marker_type TEXT NOT NULL,  -- "turning_point", "highlight", "coach_note"
    description TEXT NOT NULL,
    argument_label TEXT,
    severity TEXT NOT NULL DEFAULT 'notable',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_replay_markers_round
    ON round_replay_markers (round_id);

-- ── Round quality reports (lightweight eval metadata) ─────────────────────────

CREATE TABLE IF NOT EXISTS round_quality_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES round_simulations(id) ON DELETE CASCADE,
    drop_detection_precision FLOAT,
    concession_precision FLOAT,
    evidence_reference_accuracy FLOAT,
    decision_confidence TEXT NOT NULL DEFAULT 'contested',
    hallucination_risk TEXT NOT NULL DEFAULT 'low',
    overall_quality TEXT NOT NULL DEFAULT 'good',
    warnings JSONB NOT NULL DEFAULT '[]',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (round_id)
);

-- ── RLS policies ──────────────────────────────────────────────────────────────

ALTER TABLE round_coach_annotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE round_finding_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE round_strategic_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE round_replay_markers ENABLE ROW LEVEL SECURITY;
ALTER TABLE round_quality_reports ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS for all tables (used by backend).
-- Authenticated users can read/insert only records they own.

CREATE POLICY "coach_annotations_owner" ON round_coach_annotations
    FOR ALL USING (
        coach_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM round_simulations rs
            WHERE rs.id = round_id AND rs.user_id = auth.uid()
        )
    );

CREATE POLICY "finding_ratings_owner" ON round_finding_ratings
    FOR ALL USING (rater_id = auth.uid());

CREATE POLICY "strategic_memory_round_owner" ON round_strategic_memory
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM round_simulations rs
            WHERE rs.id = round_id AND rs.user_id = auth.uid()
        )
    );

CREATE POLICY "replay_markers_round_owner" ON round_replay_markers
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM round_simulations rs
            WHERE rs.id = round_id AND rs.user_id = auth.uid()
        )
    );

CREATE POLICY "quality_reports_round_owner" ON round_quality_reports
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM round_simulations rs
            WHERE rs.id = round_id AND rs.user_id = auth.uid()
        )
    );
