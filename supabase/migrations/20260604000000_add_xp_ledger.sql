-- XP Ledger: Append-only XP tracking to prevent XP loss on delete
-- XP represents earned learning progress, not current database rows

CREATE TABLE user_xp_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  event_key TEXT NOT NULL,
  xp_amount INTEGER NOT NULL DEFAULT 0,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Prevent duplicate XP awards for the same event
  CONSTRAINT unique_user_event_key UNIQUE (user_id, event_key)
);

CREATE INDEX idx_user_xp_events_user_id ON user_xp_events(user_id);
CREATE INDEX idx_user_xp_events_created_at ON user_xp_events(created_at DESC);
CREATE INDEX idx_user_xp_events_event_type ON user_xp_events(event_type);

-- Enable RLS
ALTER TABLE user_xp_events ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own XP events
CREATE POLICY "Users can read own XP events"
  ON user_xp_events
  FOR SELECT
  USING (auth.uid() = user_id);

-- Policy: Service role can insert (backend awards XP)
CREATE POLICY "Service role can insert XP events"
  ON user_xp_events
  FOR INSERT
  WITH CHECK (true);

COMMENT ON TABLE user_xp_events IS 'Append-only XP ledger. XP earned is never removed, even if source objects are deleted.';
COMMENT ON COLUMN user_xp_events.event_type IS 'Category of XP event: drill_attempt, skill_improvement, streak_bonus, etc.';
COMMENT ON COLUMN user_xp_events.event_key IS 'Unique identifier for this event to prevent duplicates. Format: {type}:{id}';
COMMENT ON COLUMN user_xp_events.xp_amount IS 'XP awarded for this event. Can be 0 for events that do not award XP directly.';

-- Add scoring version and fingerprint to feedback_reports
ALTER TABLE feedback_reports
  ADD COLUMN IF NOT EXISTS scoring_version TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS report_input_hash TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS last_regenerated_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_feedback_reports_scoring_version ON feedback_reports(scoring_version);
CREATE INDEX IF NOT EXISTS idx_feedback_reports_input_hash ON feedback_reports(report_input_hash);

COMMENT ON COLUMN feedback_reports.scoring_version IS 'Version of rubric/scoring system used to generate this report';
COMMENT ON COLUMN feedback_reports.report_input_hash IS 'SHA256 hash of inputs (transcript+speech_type+rubric_version) for fingerprinting';
COMMENT ON COLUMN feedback_reports.last_regenerated_at IS 'Timestamp of most recent regeneration';
