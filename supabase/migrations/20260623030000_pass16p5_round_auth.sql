-- Pass 16.5 — Round auth hardening, prep gap deduplication, phase timer

-- 1. Add phase_started_at to round_simulations for server-side timer anchoring
ALTER TABLE round_simulations
  ADD COLUMN IF NOT EXISTS phase_started_at TIMESTAMPTZ;

-- 2. Add idempotency_key to round_speeches to prevent duplicate submissions
ALTER TABLE round_speeches
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_round_speeches_idempotency
  ON round_speeches (round_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- 3. Prep gap deduplication fields
ALTER TABLE prep_gaps
  ADD COLUMN IF NOT EXISTS fingerprint TEXT,
  ADD COLUMN IF NOT EXISTS occurrence_count INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_round_id UUID REFERENCES round_simulations(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'open';

CREATE INDEX IF NOT EXISTS idx_prep_gaps_fingerprint
  ON prep_gaps (fingerprint)
  WHERE fingerprint IS NOT NULL;

-- 4. Populate fingerprints for existing rows (md5 of user_id||workspace_id||category||title)
UPDATE prep_gaps
SET fingerprint = substr(
    encode(
      digest(
        coalesce(user_id::text,'') ||
        coalesce(workspace_id::text,'') ||
        coalesce(category,'') ||
        coalesce(title,''),
        'sha256'
      ),
      'hex'
    ), 1, 32
  )
WHERE fingerprint IS NULL;

-- 5. Ensure RLS on round_crossfire_exchanges allows student-question rows
-- (questioner_side can be student side — existing policy is broad enough)

-- 6. Add round_simulation_id FK to prep_gaps (idempotent)
ALTER TABLE prep_gaps
  ADD COLUMN IF NOT EXISTS round_simulation_id UUID REFERENCES round_simulations(id) ON DELETE SET NULL;
