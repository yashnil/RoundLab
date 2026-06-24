-- RoundLab Remote Schema Audit Script
-- Run this on your remote Supabase instance to verify all Pass 13–18 tables exist.
-- Connect via: psql "$SUPABASE_DB_URL" -f scripts/audit_remote_schema.sql
--
-- Output: one row per check, with status (EXISTS / MISSING / PARTIAL)

-- ── 1. Table existence check ──────────────────────────────────────────────────
SELECT
    t.tablename                              AS table_name,
    CASE WHEN t.tablename IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (
    VALUES
        -- Pass 13: Evidence Library
        ('resolutions'),
        ('arguments'),
        ('evidence_sources'),
        ('library_card_metadata'),
        ('blockfiles'),
        ('blockfile_sections'),
        ('blockfile_entries'),
        ('frontlines'),
        ('frontline_responses'),
        ('frontline_response_cards'),
        ('card_relationships'),
        ('card_versions'),
        ('frontline_performance_log'),
        -- Pass 14: Tournament Prep
        ('prep_workspaces'),
        ('prep_gaps'),
        ('prep_readiness_reports'),
        ('prep_tasks'),
        ('prep_workouts'),
        -- Pass 15: Judge Adaptation
        ('judge_profiles'),
        ('judge_adaptations'),
        ('judge_adaptation_notes'),
        ('judge_workout_assignments'),
        -- Pass 16: Round Simulation
        ('round_simulations'),
        ('round_participants'),
        ('round_speeches'),
        ('round_crossfire_exchanges'),
        ('round_arguments'),
        ('round_flow_events'),
        ('round_evidence_uses'),
        ('round_decisions'),
        ('round_drills'),
        ('opponent_round_plans'),
        ('round_adaptation_reviews'),
        ('round_legality_checks'),
        -- Pass 17: Coach Review
        ('round_coach_annotations'),
        ('round_finding_ratings'),
        ('round_strategic_memory'),
        ('round_replay_markers'),
        ('round_quality_reports'),
        -- Pass 18: Pilot
        ('usage_limits'),
        ('onboarding_progress')
) AS expected(expected_name)
LEFT JOIN pg_tables t
    ON t.tablename = expected.expected_name
    AND t.schemaname = 'public'
ORDER BY
    CASE WHEN t.tablename IS NOT NULL THEN 1 ELSE 0 END,
    expected.expected_name;


-- ── 2. prep_gaps column additions (Pass 16 + 16p5 ALTERs) ───────────────────
SELECT
    column_name,
    data_type,
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (
    VALUES
        ('round_simulation_id'),    -- added in pass16
        ('fingerprint'),            -- added in pass16p5
        ('occurrence_count'),       -- added in pass16p5
        ('first_seen_at'),          -- added in pass16p5
        ('last_seen_at'),           -- added in pass16p5
        ('last_round_id'),          -- added in pass16p5
        ('status')                  -- added in pass16p5
) AS expected(col_name)
LEFT JOIN information_schema.columns c
    ON c.table_name = 'prep_gaps'
    AND c.column_name = expected.col_name
    AND c.table_schema = 'public';


-- ── 3. round_simulations column additions (Pass 16.5 ALTER) ──────────────────
SELECT
    column_name,
    data_type,
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (
    VALUES
        ('phase_started_at')       -- added in pass16p5
) AS expected(col_name)
LEFT JOIN information_schema.columns c
    ON c.table_name = 'round_simulations'
    AND c.column_name = expected.col_name
    AND c.table_schema = 'public';


-- ── 4. evidence_cards column additions ───────────────────────────────────────
SELECT
    column_name,
    data_type,
    CASE WHEN column_name IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (
    VALUES
        ('card_text'),              -- pass15p6 save_fix
        ('cite')                    -- pass15p6 save_fix
) AS expected(col_name)
LEFT JOIN information_schema.columns c
    ON c.table_name = 'evidence_cards'
    AND c.column_name = expected.col_name
    AND c.table_schema = 'public';


-- ── 5. RLS enabled on all new tables ─────────────────────────────────────────
SELECT
    c.relname  AS table_name,
    c.relrowsecurity AS rls_enabled
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
AND c.relkind = 'r'
AND c.relname IN (
    'resolutions','arguments','evidence_sources','library_card_metadata',
    'blockfiles','blockfile_sections','blockfile_entries',
    'frontlines','frontline_responses','frontline_response_cards',
    'card_relationships','card_versions','frontline_performance_log',
    'prep_workspaces','prep_gaps','prep_readiness_reports',
    'prep_tasks','prep_workouts',
    'judge_profiles','judge_adaptations','judge_adaptation_notes',
    'judge_workout_assignments',
    'round_simulations','round_participants','round_speeches',
    'round_crossfire_exchanges','round_arguments','round_flow_events',
    'round_evidence_uses','round_decisions','round_drills',
    'opponent_round_plans','round_adaptation_reviews','round_legality_checks',
    'round_coach_annotations','round_finding_ratings','round_strategic_memory',
    'round_replay_markers','round_quality_reports',
    'usage_limits','onboarding_progress'
)
ORDER BY c.relname;


-- ── 6. RPC functions exist ────────────────────────────────────────────────────
SELECT
    proname AS function_name,
    CASE WHEN proname IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (
    VALUES ('match_document_chunks'), ('match_block_entries')
) AS expected(fn_name)
LEFT JOIN pg_proc p
    ON p.proname = expected.fn_name
ORDER BY fn_name;


-- ── 7. View exists ────────────────────────────────────────────────────────────
SELECT
    viewname,
    CASE WHEN viewname IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (VALUES ('pilot_cost_summary')) AS expected(vn)
LEFT JOIN pg_views v ON v.viewname = expected.vn AND v.schemaname = 'public';


-- ── 8. Key indexes ────────────────────────────────────────────────────────────
SELECT
    indexname,
    CASE WHEN indexname IS NOT NULL THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (
    VALUES
        ('idx_product_events_user_event'),
        ('idx_product_events_event_name_time'),
        ('idx_round_simulations_user_created'),
        ('idx_prep_gaps_fingerprint')
) AS expected(idx)
LEFT JOIN pg_indexes i ON i.indexname = expected.idx AND i.schemaname = 'public'
ORDER BY idx;


-- ── 9. Supabase migration history ────────────────────────────────────────────
-- Shows which local migrations have been recorded in the remote schema_migrations table.
SELECT
    version,
    inserted_at
FROM supabase_migrations.schema_migrations
ORDER BY inserted_at;
