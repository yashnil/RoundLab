-- Pass 18: Production Pilot Readiness
-- Adds: product_events indexes, usage_limits table, cost_log view

-- ── 1. Indexes on product_events for analytics queries ────────────────────────
-- Supports pilot funnel queries: activation, retention, funnel drop
CREATE INDEX IF NOT EXISTS idx_product_events_user_event
    ON product_events (user_id, event_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_events_event_date
    ON product_events (event_name, (created_at::date));

-- ── 2. Usage limits table (pilot-mode per-user caps) ─────────────────────────
CREATE TABLE IF NOT EXISTS usage_limits (
    id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Rolling 24-hour counters (reset by background job or per-request check)
    rounds_today    int  NOT NULL DEFAULT 0,
    searches_today  int  NOT NULL DEFAULT 0,
    -- Estimated daily spend in USD
    spend_today_usd numeric(10, 6) NOT NULL DEFAULT 0,
    -- Limits (0 = use system defaults from config)
    max_rounds_daily        int     NOT NULL DEFAULT 0,
    max_searches_daily      int     NOT NULL DEFAULT 0,
    max_spend_daily_usd     numeric NOT NULL DEFAULT 0,
    -- Tracking
    last_reset_at   timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT usage_limits_user_unique UNIQUE (user_id)
);

ALTER TABLE usage_limits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "usage_limits_owner_read" ON usage_limits
    FOR SELECT USING (auth.uid() = user_id);

-- Admins (service role) can read/write all rows
CREATE POLICY "usage_limits_service_role" ON usage_limits
    FOR ALL USING (auth.role() = 'service_role');

-- ── 3. Cost log view (for developer/admin cost summary) ──────────────────────
CREATE OR REPLACE VIEW pilot_cost_summary AS
SELECT
    user_id,
    (created_at::date) AS date,
    event_name,
    COUNT(*) AS event_count,
    SUM((metadata_json->>'cost_usd')::numeric) FILTER (
        WHERE metadata_json->>'cost_usd' IS NOT NULL
    ) AS total_cost_usd
FROM product_events
WHERE event_name IN ('llm_cost_incurred', 'provider_cost_incurred')
GROUP BY user_id, (created_at::date), event_name;

-- ── 4. Index on round_simulations for coach review queries ────────────────────
CREATE INDEX IF NOT EXISTS idx_round_simulations_user_created
    ON round_simulations (user_id, created_at DESC);

-- ── 5. Onboarding progress table ─────────────────────────────────────────────
-- Tracks which onboarding steps each user has completed.
-- Skippable and resumable by design.
CREATE TABLE IF NOT EXISTS onboarding_progress (
    id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role            text NOT NULL DEFAULT 'student',  -- 'student' | 'coach'
    completed_steps text[] NOT NULL DEFAULT '{}',
    skipped         boolean NOT NULL DEFAULT false,
    completed_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT onboarding_progress_user_unique UNIQUE (user_id)
);

ALTER TABLE onboarding_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "onboarding_progress_owner" ON onboarding_progress
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "onboarding_progress_service_role" ON onboarding_progress
    FOR ALL USING (auth.role() = 'service_role');
