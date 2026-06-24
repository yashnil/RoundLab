-- RoundLab Remote Schema Audit — SELECT-only, covers all 31 migrations
--
-- Run this in the Supabase SQL Editor (safe — no DDL, no DML).
-- Produces one summary row per migration: fully_applied, checks_passed,
-- checks_total, missing_or_invalid_objects.
--
-- Conditional objects (HNSW indexes inside DO blocks) are excluded because
-- their absence does not indicate migration failure.
--
-- Output columns
--   migration_version          14-digit timestamp prefix
--   migration_name             file name stem (no timestamp, no .sql)
--   fully_applied              TRUE when every audited object exists
--   checks_passed / checks_total
--   missing_or_invalid_objects comma-separated list of failed checks

WITH

-- ── 1. Enum types ─────────────────────────────────────────────────────────────
expected_types(mv, mn, obj) AS (VALUES
    ('20260524000000','initial_schema','speech_type'),
    ('20260524000000','initial_schema','speech_side'),
    ('20260524000000','initial_schema','speech_status'),
    ('20260524000000','initial_schema','judge_type')
),
type_checks AS (
    SELECT mv AS migration_version, mn AS migration_name,
           'enum_type'::text AS check_type, obj AS object_name,
           EXISTS (
               SELECT 1 FROM pg_type t
               JOIN pg_namespace n ON n.oid = t.typnamespace
               WHERE t.typname = et.obj AND t.typtype = 'e' AND n.nspname = 'public'
           ) AS ok
    FROM expected_types et
),

-- ── 2. Tables ─────────────────────────────────────────────────────────────────
expected_tables(mv, mn, obj) AS (VALUES
    -- initial_schema
    ('20260524000000','initial_schema','profiles'),
    ('20260524000000','initial_schema','speeches'),
    ('20260524000000','initial_schema','transcripts'),
    ('20260524000000','initial_schema','argument_maps'),
    ('20260524000000','initial_schema','feedback_reports'),
    ('20260524000000','initial_schema','drills'),
    ('20260524000000','initial_schema','drill_attempts'),
    -- add_teams
    ('20260602000000','add_teams','teams'),
    ('20260602000000','add_teams','team_members'),
    -- add_xp_ledger
    ('20260604000000','add_xp_ledger','user_xp_events'),
    -- add_evidence_tables
    ('20260608100000','add_evidence_tables','documents'),
    ('20260608100000','add_evidence_tables','document_chunks'),
    ('20260608100000','add_evidence_tables','evidence_cards'),
    ('20260608100000','add_evidence_tables','claim_evidence_checks'),
    -- add_pilot_tables
    ('20260609000000','add_pilot_tables','product_events'),
    ('20260609000000','add_pilot_tables','drill_ratings'),
    ('20260609000000','add_pilot_tables','output_feedback'),
    -- add_analysis_jobs
    ('20260609300000','add_analysis_jobs','analysis_jobs'),
    -- add_delivery_metrics
    ('20260609500000','add_delivery_metrics','delivery_metrics'),
    -- add_shared_reports
    ('20260609700000','add_shared_reports','shared_reports'),
    -- add_workouts
    ('20260609800000','add_workouts','workouts'),
    -- add_blockfile_tables
    ('20260609900000','add_blockfile_tables','block_entries'),
    ('20260609900000','add_blockfile_tables','block_coverage_checks'),
    -- add_research_tables
    ('20260610000000','add_research_tables','research_sources'),
    ('20260610000000','add_research_tables','card_drafts'),
    -- add_assignments
    ('20260618000000','add_assignments','assignments'),
    ('20260618000000','add_assignments','assignment_recipients'),
    -- pass13_evidence_library
    ('20260622010000','pass13_evidence_library','resolutions'),
    ('20260622010000','pass13_evidence_library','arguments'),
    ('20260622010000','pass13_evidence_library','evidence_sources'),
    ('20260622010000','pass13_evidence_library','library_card_metadata'),
    ('20260622010000','pass13_evidence_library','blockfiles'),
    ('20260622010000','pass13_evidence_library','blockfile_sections'),
    ('20260622010000','pass13_evidence_library','blockfile_entries'),
    ('20260622010000','pass13_evidence_library','frontlines'),
    ('20260622010000','pass13_evidence_library','frontline_responses'),
    ('20260622010000','pass13_evidence_library','frontline_response_cards'),
    ('20260622010000','pass13_evidence_library','card_relationships'),
    ('20260622010000','pass13_evidence_library','card_versions'),
    ('20260622010000','pass13_evidence_library','frontline_performance_log'),
    -- pass14_tournament_prep
    ('20260622020000','pass14_tournament_prep','prep_workspaces'),
    ('20260622020000','pass14_tournament_prep','prep_gaps'),
    ('20260622020000','pass14_tournament_prep','prep_readiness_reports'),
    ('20260622020000','pass14_tournament_prep','prep_tasks'),
    ('20260622020000','pass14_tournament_prep','prep_workouts'),
    -- pass15_judge_adaptation
    ('20260622030000','pass15_judge_adaptation','judge_profiles'),
    ('20260622030000','pass15_judge_adaptation','judge_adaptations'),
    ('20260622030000','pass15_judge_adaptation','judge_adaptation_notes'),
    ('20260622030000','pass15_judge_adaptation','judge_workout_assignments'),
    -- pass16_round_simulation
    ('20260623020000','pass16_round_simulation','round_simulations'),
    ('20260623020000','pass16_round_simulation','round_participants'),
    ('20260623020000','pass16_round_simulation','round_speeches'),
    ('20260623020000','pass16_round_simulation','round_crossfire_exchanges'),
    ('20260623020000','pass16_round_simulation','round_arguments'),
    ('20260623020000','pass16_round_simulation','round_flow_events'),
    ('20260623020000','pass16_round_simulation','round_evidence_uses'),
    ('20260623020000','pass16_round_simulation','round_decisions'),
    ('20260623020000','pass16_round_simulation','round_drills'),
    ('20260623020000','pass16_round_simulation','opponent_round_plans'),
    ('20260623020000','pass16_round_simulation','round_adaptation_reviews'),
    -- pass16_round_legality
    ('20260623025000','pass16_round_legality','round_legality_checks'),
    -- pass17_round_quality
    ('20260623040000','pass17_round_quality','round_coach_annotations'),
    ('20260623040000','pass17_round_quality','round_finding_ratings'),
    ('20260623040000','pass17_round_quality','round_strategic_memory'),
    ('20260623040000','pass17_round_quality','round_replay_markers'),
    ('20260623040000','pass17_round_quality','round_quality_reports'),
    -- pass18_pilot
    ('20260623050000','pass18_pilot','usage_limits'),
    ('20260623050000','pass18_pilot','onboarding_progress')
),
table_checks AS (
    SELECT mv AS migration_version, mn AS migration_name,
           'table'::text AS check_type, obj AS object_name,
           to_regclass('public.' || obj) IS NOT NULL AS ok
    FROM expected_tables
),

-- ── 3. Columns (ALTER TABLE ADD COLUMN or SET DEFAULT) ────────────────────────
expected_columns(mv, mn, tbl, col) AS (VALUES
    -- add_drill_fields
    ('20260601000000','add_drill_fields','drills','instructions'),
    ('20260601000000','add_drill_fields','drills','success_criteria'),
    ('20260601000000','add_drill_fields','drills','source_weakness'),
    ('20260601000000','add_drill_fields','drills','difficulty'),
    ('20260601000000','add_drill_fields','drills','status'),
    -- add_feedback_rating
    ('20260602100000','add_feedback_rating','feedback_reports','helpful_rating'),
    ('20260602100000','add_feedback_rating','feedback_reports','helpful_comment'),
    -- add_xp_ledger (columns on feedback_reports)
    ('20260604000000','add_xp_ledger','feedback_reports','scoring_version'),
    ('20260604000000','add_xp_ledger','feedback_reports','report_input_hash'),
    ('20260604000000','add_xp_ledger','feedback_reports','last_regenerated_at'),
    -- add_drill_time_limit
    ('20260606000000','add_drill_time_limit','drills','time_limit_seconds'),
    -- add_rerecord_fields
    ('20260607000000','add_rerecord_fields','speeches','parent_speech_id'),
    ('20260607000000','add_rerecord_fields','speeches','source_drill_id'),
    -- add_argument_map_correction
    ('20260609400000','add_argument_map_correction','argument_maps','source_type'),
    ('20260609400000','add_argument_map_correction','argument_maps','original_arguments'),
    ('20260609400000','add_argument_map_correction','argument_maps','user_corrected_at'),
    ('20260609400000','add_argument_map_correction','argument_maps','correction_notes'),
    ('20260609400000','add_argument_map_correction','argument_maps','updated_at'),
    -- add_pgvector_embeddings: document_chunks columns
    ('20260609600000','add_pgvector_embeddings','document_chunks','embedding'),
    ('20260609600000','add_pgvector_embeddings','document_chunks','embedding_model'),
    ('20260609600000','add_pgvector_embeddings','document_chunks','embedded_at'),
    -- add_pgvector_embeddings: claim_evidence_checks columns
    ('20260609600000','add_pgvector_embeddings','claim_evidence_checks','matched_chunk_ids'),
    ('20260609600000','add_pgvector_embeddings','claim_evidence_checks','top_similarity'),
    ('20260609600000','add_pgvector_embeddings','claim_evidence_checks','retrieved_snippets_json'),
    ('20260609600000','add_pgvector_embeddings','claim_evidence_checks','support_rationale'),
    ('20260609600000','add_pgvector_embeddings','claim_evidence_checks','missing_link'),
    ('20260609600000','add_pgvector_embeddings','claim_evidence_checks','retrieval_mode'),
    -- add_blockfile_tables: documents columns
    ('20260609900000','add_blockfile_tables','documents','document_role'),
    ('20260609900000','add_blockfile_tables','documents','debate_side'),
    ('20260609900000','add_blockfile_tables','documents','topic'),
    ('20260609900000','add_blockfile_tables','documents','blockfile_metadata_json'),
    -- add_research_tables: evidence_cards columns
    ('20260610000000','add_research_tables','evidence_cards','url'),
    ('20260610000000','add_research_tables','evidence_cards','title'),
    ('20260610000000','add_research_tables','evidence_cards','publication'),
    ('20260610000000','add_research_tables','evidence_cards','author_credentials'),
    ('20260610000000','add_research_tables','evidence_cards','published_date'),
    ('20260610000000','add_research_tables','evidence_cards','body_text'),
    ('20260610000000','add_research_tables','evidence_cards','highlighted_spans_json'),
    ('20260610000000','add_research_tables','evidence_cards','underline_spans_json'),
    ('20260610000000','add_research_tables','evidence_cards','card_cutting_metadata_json'),
    ('20260610000000','add_research_tables','evidence_cards','source_quality'),
    ('20260610000000','add_research_tables','evidence_cards','extraction_confidence'),
    ('20260610000000','add_research_tables','evidence_cards','generated_tag'),
    ('20260610000000','add_research_tables','evidence_cards','user_reviewed'),
    ('20260610000000','add_research_tables','evidence_cards','card_source_type'),
    -- pass15p6_save_fix: evidence_cards.cite
    ('20260623010000','pass15p6_save_fix','evidence_cards','cite'),
    -- pass16_round_simulation: prep_gaps.round_simulation_id
    ('20260623020000','pass16_round_simulation','prep_gaps','round_simulation_id'),
    -- pass16_round_legality: frontline_performance_log.round_simulation_id
    ('20260623025000','pass16_round_legality','frontline_performance_log','round_simulation_id'),
    -- pass16p5_round_auth
    ('20260623030000','pass16p5_round_auth','round_simulations','phase_started_at'),
    ('20260623030000','pass16p5_round_auth','round_speeches','idempotency_key'),
    ('20260623030000','pass16p5_round_auth','prep_gaps','fingerprint'),
    ('20260623030000','pass16p5_round_auth','prep_gaps','occurrence_count'),
    ('20260623030000','pass16p5_round_auth','prep_gaps','first_seen_at'),
    ('20260623030000','pass16p5_round_auth','prep_gaps','last_seen_at'),
    ('20260623030000','pass16p5_round_auth','prep_gaps','last_round_id'),
    ('20260623030000','pass16p5_round_auth','prep_gaps','status')
),
column_checks AS (
    SELECT ec.mv AS migration_version, ec.mn AS migration_name,
           'column'::text AS check_type, ec.tbl || '.' || ec.col AS object_name,
           EXISTS (
               SELECT 1 FROM information_schema.columns c
               WHERE c.table_schema = 'public'
                 AND c.table_name   = ec.tbl
                 AND c.column_name  = ec.col
           ) AS ok
    FROM expected_columns ec
),

-- ── 4. Indexes ────────────────────────────────────────────────────────────────
-- HNSW indexes (document_chunks_embedding_hnsw_idx, idx_block_entries_embedding_hnsw)
-- are wrapped in conditional DO blocks and are excluded here.
expected_indexes(mv, mn, obj) AS (VALUES
    -- initial_schema
    ('20260524000000','initial_schema','idx_speeches_user_created'),
    ('20260524000000','initial_schema','idx_drills_speech_id'),
    ('20260524000000','initial_schema','idx_drills_user_id'),
    ('20260524000000','initial_schema','idx_drill_attempts_drill_id'),
    ('20260524000000','initial_schema','idx_drill_attempts_user_id'),
    -- add_teams
    ('20260602000000','add_teams','idx_teams_invite_code'),
    ('20260602000000','add_teams','idx_team_members_team_id'),
    ('20260602000000','add_teams','idx_team_members_user_id'),
    -- add_xp_ledger
    ('20260604000000','add_xp_ledger','idx_user_xp_events_user_id'),
    ('20260604000000','add_xp_ledger','idx_user_xp_events_created_at'),
    ('20260604000000','add_xp_ledger','idx_user_xp_events_event_type'),
    ('20260604000000','add_xp_ledger','idx_feedback_reports_scoring_version'),
    ('20260604000000','add_xp_ledger','idx_feedback_reports_input_hash'),
    -- add_evidence_tables
    ('20260608100000','add_evidence_tables','document_chunks_fts_idx'),
    ('20260608100000','add_evidence_tables','document_chunks_document_idx'),
    ('20260608100000','add_evidence_tables','evidence_cards_document_idx'),
    ('20260608100000','add_evidence_tables','claim_checks_speech_idx'),
    -- add_pilot_tables
    ('20260609000000','add_pilot_tables','idx_product_events_user_id'),
    ('20260609000000','add_pilot_tables','idx_product_events_event_name'),
    ('20260609000000','add_pilot_tables','idx_product_events_created_at'),
    ('20260609000000','add_pilot_tables','idx_drill_ratings_user_id'),
    ('20260609000000','add_pilot_tables','idx_drill_ratings_drill_id'),
    ('20260609000000','add_pilot_tables','idx_output_feedback_user_id'),
    ('20260609000000','add_pilot_tables','idx_output_feedback_target_type'),
    ('20260609000000','add_pilot_tables','idx_output_feedback_created_at'),
    -- add_analysis_jobs
    ('20260609300000','add_analysis_jobs','analysis_jobs_speech_id_idx'),
    ('20260609300000','add_analysis_jobs','analysis_jobs_user_status_idx'),
    ('20260609300000','add_analysis_jobs','analysis_jobs_created_at_idx'),
    -- add_shared_reports
    ('20260609700000','add_shared_reports','idx_shared_reports_speech_id'),
    ('20260609700000','add_shared_reports','idx_shared_reports_user_id'),
    ('20260609700000','add_shared_reports','idx_shared_reports_token'),
    -- add_workouts
    ('20260609800000','add_workouts','idx_workouts_speech_id'),
    ('20260609800000','add_workouts','idx_workouts_user_id'),
    ('20260609800000','add_workouts','idx_workouts_user_status'),
    -- add_blockfile_tables
    ('20260609900000','add_blockfile_tables','idx_block_entries_user_id'),
    ('20260609900000','add_blockfile_tables','idx_block_entries_document_id'),
    ('20260609900000','add_blockfile_tables','idx_block_entries_entry_type'),
    ('20260609900000','add_blockfile_tables','idx_block_entries_side'),
    ('20260609900000','add_blockfile_tables','idx_block_entries_topic'),
    ('20260609900000','add_blockfile_tables','idx_block_coverage_speech_id'),
    ('20260609900000','add_blockfile_tables','idx_block_coverage_user_id'),
    -- add_research_tables
    ('20260610000000','add_research_tables','research_sources_user_id_idx'),
    ('20260610000000','add_research_tables','card_drafts_user_id_idx'),
    ('20260610000000','add_research_tables','card_drafts_status_idx'),
    -- add_assignments
    ('20260618000000','add_assignments','idx_assignments_team_id'),
    ('20260618000000','add_assignments','idx_assignment_recipients_assignment'),
    ('20260618000000','add_assignments','idx_assignment_recipients_user'),
    ('20260618000000','add_assignments','idx_assignment_recipients_status'),
    -- pass13_evidence_library
    ('20260622010000','pass13_evidence_library','idx_resolutions_user'),
    ('20260622010000','pass13_evidence_library','idx_resolutions_team'),
    ('20260622010000','pass13_evidence_library','idx_resolutions_active'),
    ('20260622010000','pass13_evidence_library','idx_arguments_user'),
    ('20260622010000','pass13_evidence_library','idx_arguments_resolution'),
    ('20260622010000','pass13_evidence_library','idx_arguments_type'),
    ('20260622010000','pass13_evidence_library','idx_evidence_sources_user'),
    ('20260622010000','pass13_evidence_library','idx_evidence_sources_doi'),
    ('20260622010000','pass13_evidence_library','idx_evidence_sources_url_hash'),
    ('20260622010000','pass13_evidence_library','idx_library_card_metadata_user'),
    ('20260622010000','pass13_evidence_library','idx_library_card_metadata_card'),
    ('20260622010000','pass13_evidence_library','idx_library_card_metadata_resolution'),
    ('20260622010000','pass13_evidence_library','idx_blockfiles_user'),
    ('20260622010000','pass13_evidence_library','idx_blockfiles_resolution'),
    ('20260622010000','pass13_evidence_library','idx_blockfile_sections_blockfile'),
    ('20260622010000','pass13_evidence_library','idx_blockfile_sections_position'),
    ('20260622010000','pass13_evidence_library','idx_blockfile_entries_section'),
    ('20260622010000','pass13_evidence_library','idx_blockfile_entries_card'),
    ('20260622010000','pass13_evidence_library','idx_frontlines_user'),
    ('20260622010000','pass13_evidence_library','idx_frontlines_argument'),
    ('20260622010000','pass13_evidence_library','idx_frontlines_blockfile'),
    ('20260622010000','pass13_evidence_library','idx_frontline_responses_frontline'),
    ('20260622010000','pass13_evidence_library','idx_frontline_responses_type'),
    ('20260622010000','pass13_evidence_library','idx_frontline_response_cards_response'),
    ('20260622010000','pass13_evidence_library','idx_frontline_response_cards_card'),
    ('20260622010000','pass13_evidence_library','idx_card_relationships_from'),
    ('20260622010000','pass13_evidence_library','idx_card_relationships_to'),
    ('20260622010000','pass13_evidence_library','idx_card_relationships_creator'),
    ('20260622010000','pass13_evidence_library','idx_card_versions_card'),
    ('20260622010000','pass13_evidence_library','idx_card_versions_user'),
    ('20260622010000','pass13_evidence_library','idx_card_versions_number'),
    ('20260622010000','pass13_evidence_library','idx_frontline_perf_frontline'),
    ('20260622010000','pass13_evidence_library','idx_frontline_perf_user'),
    -- pass14_tournament_prep
    ('20260622020000','pass14_tournament_prep','idx_prep_workspaces_user'),
    ('20260622020000','pass14_tournament_prep','idx_prep_workspaces_resolution'),
    ('20260622020000','pass14_tournament_prep','idx_prep_gaps_workspace'),
    ('20260622020000','pass14_tournament_prep','idx_prep_gaps_user'),
    ('20260622020000','pass14_tournament_prep','idx_prep_gaps_category'),
    ('20260622020000','pass14_tournament_prep','idx_prep_readiness_reports_workspace'),
    ('20260622020000','pass14_tournament_prep','idx_prep_readiness_reports_user'),
    ('20260622020000','pass14_tournament_prep','idx_prep_tasks_workspace'),
    ('20260622020000','pass14_tournament_prep','idx_prep_tasks_user'),
    ('20260622020000','pass14_tournament_prep','idx_prep_tasks_status'),
    ('20260622020000','pass14_tournament_prep','idx_prep_tasks_priority'),
    ('20260622020000','pass14_tournament_prep','idx_prep_workouts_workspace'),
    ('20260622020000','pass14_tournament_prep','idx_prep_workouts_user'),
    ('20260622020000','pass14_tournament_prep','idx_prep_workouts_status'),
    -- pass15_judge_adaptation
    ('20260622030000','pass15_judge_adaptation','idx_judge_profiles_user'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_profiles_type'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_adaptations_user'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_adaptations_judge_type'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_adaptations_workspace'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_adaptation_notes_adaptation'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_adaptation_notes_user'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_workout_assignments_to'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_workout_assignments_by'),
    ('20260622030000','pass15_judge_adaptation','idx_judge_workout_assignments_team'),
    -- pass15p5_evidence_studio
    ('20260622040000','pass15p5_evidence_studio','documents_user_research_unique'),
    -- pass16_round_simulation
    ('20260623020000','pass16_round_simulation','idx_round_simulations_user'),
    ('20260623020000','pass16_round_simulation','idx_round_simulations_team'),
    ('20260623020000','pass16_round_simulation','idx_round_simulations_status'),
    ('20260623020000','pass16_round_simulation','idx_round_participants_round'),
    ('20260623020000','pass16_round_simulation','idx_round_speeches_round'),
    ('20260623020000','pass16_round_simulation','idx_round_speeches_phase'),
    ('20260623020000','pass16_round_simulation','idx_round_speeches_speaker'),
    ('20260623020000','pass16_round_simulation','idx_round_crossfire_round'),
    ('20260623020000','pass16_round_simulation','idx_round_crossfire_phase'),
    ('20260623020000','pass16_round_simulation','idx_round_arguments_round'),
    ('20260623020000','pass16_round_simulation','idx_round_arguments_side'),
    ('20260623020000','pass16_round_simulation','idx_round_arguments_status'),
    ('20260623020000','pass16_round_simulation','idx_round_flow_events_round'),
    ('20260623020000','pass16_round_simulation','idx_round_flow_events_argument'),
    ('20260623020000','pass16_round_simulation','idx_round_flow_events_phase'),
    ('20260623020000','pass16_round_simulation','idx_round_evidence_uses_round'),
    ('20260623020000','pass16_round_simulation','idx_round_evidence_uses_card'),
    ('20260623020000','pass16_round_simulation','idx_round_evidence_uses_phase'),
    ('20260623020000','pass16_round_simulation','idx_round_decisions_round'),
    ('20260623020000','pass16_round_simulation','idx_round_decisions_judge'),
    ('20260623020000','pass16_round_simulation','idx_round_drills_round'),
    ('20260623020000','pass16_round_simulation','idx_opponent_plans_round'),
    ('20260623020000','pass16_round_simulation','idx_round_adaptation_reviews_round'),
    -- pass16_round_legality
    ('20260623025000','pass16_round_legality','idx_round_legality_checks_round'),
    ('20260623025000','pass16_round_legality','idx_round_legality_checks_violation'),
    -- pass16p5_round_auth
    ('20260623030000','pass16p5_round_auth','idx_round_speeches_idempotency'),
    ('20260623030000','pass16p5_round_auth','idx_prep_gaps_fingerprint'),
    -- pass17_round_quality
    ('20260623040000','pass17_round_quality','idx_coach_annotations_round'),
    ('20260623040000','pass17_round_quality','idx_coach_annotations_coach'),
    ('20260623040000','pass17_round_quality','idx_finding_ratings_round'),
    ('20260623040000','pass17_round_quality','idx_replay_markers_round'),
    -- pass18_pilot
    ('20260623050000','pass18_pilot','idx_product_events_user_event'),
    ('20260623050000','pass18_pilot','idx_product_events_event_name_time'),
    ('20260623050000','pass18_pilot','idx_round_simulations_user_created')
),
index_checks AS (
    SELECT ei.mv AS migration_version, ei.mn AS migration_name,
           'index'::text AS check_type, ei.obj AS object_name,
           EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = ei.obj) AS ok
    FROM expected_indexes ei
),

-- ── 5. RLS enabled ────────────────────────────────────────────────────────────
expected_rls(mv, mn, obj) AS (VALUES
    ('20260524000000','initial_schema','profiles'),
    ('20260524000000','initial_schema','speeches'),
    ('20260524000000','initial_schema','transcripts'),
    ('20260524000000','initial_schema','argument_maps'),
    ('20260524000000','initial_schema','feedback_reports'),
    ('20260524000000','initial_schema','drills'),
    ('20260524000000','initial_schema','drill_attempts'),
    ('20260602000000','add_teams','teams'),
    ('20260602000000','add_teams','team_members'),
    ('20260604000000','add_xp_ledger','user_xp_events'),
    ('20260608100000','add_evidence_tables','documents'),
    ('20260608100000','add_evidence_tables','document_chunks'),
    ('20260608100000','add_evidence_tables','evidence_cards'),
    ('20260608100000','add_evidence_tables','claim_evidence_checks'),
    ('20260609000000','add_pilot_tables','product_events'),
    ('20260609000000','add_pilot_tables','drill_ratings'),
    ('20260609000000','add_pilot_tables','output_feedback'),
    ('20260609300000','add_analysis_jobs','analysis_jobs'),
    ('20260609500000','add_delivery_metrics','delivery_metrics'),
    ('20260609700000','add_shared_reports','shared_reports'),
    ('20260609800000','add_workouts','workouts'),
    ('20260609900000','add_blockfile_tables','block_entries'),
    ('20260609900000','add_blockfile_tables','block_coverage_checks'),
    ('20260610000000','add_research_tables','research_sources'),
    ('20260610000000','add_research_tables','card_drafts'),
    ('20260618000000','add_assignments','assignments'),
    ('20260618000000','add_assignments','assignment_recipients'),
    ('20260622010000','pass13_evidence_library','resolutions'),
    ('20260622010000','pass13_evidence_library','arguments'),
    ('20260622010000','pass13_evidence_library','evidence_sources'),
    ('20260622010000','pass13_evidence_library','library_card_metadata'),
    ('20260622010000','pass13_evidence_library','blockfiles'),
    ('20260622010000','pass13_evidence_library','blockfile_sections'),
    ('20260622010000','pass13_evidence_library','blockfile_entries'),
    ('20260622010000','pass13_evidence_library','frontlines'),
    ('20260622010000','pass13_evidence_library','frontline_responses'),
    ('20260622010000','pass13_evidence_library','frontline_response_cards'),
    ('20260622010000','pass13_evidence_library','card_relationships'),
    ('20260622010000','pass13_evidence_library','card_versions'),
    ('20260622010000','pass13_evidence_library','frontline_performance_log'),
    ('20260622020000','pass14_tournament_prep','prep_workspaces'),
    ('20260622020000','pass14_tournament_prep','prep_gaps'),
    ('20260622020000','pass14_tournament_prep','prep_readiness_reports'),
    ('20260622020000','pass14_tournament_prep','prep_tasks'),
    ('20260622020000','pass14_tournament_prep','prep_workouts'),
    ('20260622030000','pass15_judge_adaptation','judge_profiles'),
    ('20260622030000','pass15_judge_adaptation','judge_adaptations'),
    ('20260622030000','pass15_judge_adaptation','judge_adaptation_notes'),
    ('20260622030000','pass15_judge_adaptation','judge_workout_assignments'),
    ('20260623020000','pass16_round_simulation','round_simulations'),
    ('20260623020000','pass16_round_simulation','round_participants'),
    ('20260623020000','pass16_round_simulation','round_speeches'),
    ('20260623020000','pass16_round_simulation','round_crossfire_exchanges'),
    ('20260623020000','pass16_round_simulation','round_arguments'),
    ('20260623020000','pass16_round_simulation','round_flow_events'),
    ('20260623020000','pass16_round_simulation','round_evidence_uses'),
    ('20260623020000','pass16_round_simulation','round_decisions'),
    ('20260623020000','pass16_round_simulation','round_drills'),
    ('20260623020000','pass16_round_simulation','opponent_round_plans'),
    ('20260623020000','pass16_round_simulation','round_adaptation_reviews'),
    ('20260623025000','pass16_round_legality','round_legality_checks'),
    ('20260623040000','pass17_round_quality','round_coach_annotations'),
    ('20260623040000','pass17_round_quality','round_finding_ratings'),
    ('20260623040000','pass17_round_quality','round_strategic_memory'),
    ('20260623040000','pass17_round_quality','round_replay_markers'),
    ('20260623040000','pass17_round_quality','round_quality_reports'),
    ('20260623050000','pass18_pilot','usage_limits'),
    ('20260623050000','pass18_pilot','onboarding_progress')
),
rls_checks AS (
    SELECT er.mv AS migration_version, er.mn AS migration_name,
           'rls'::text AS check_type, er.obj AS object_name,
           EXISTS (
               SELECT 1 FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'public'
                 AND c.relname = er.obj
                 AND c.relrowsecurity = true
           ) AS ok
    FROM expected_rls er
),

-- ── 6. Policies ───────────────────────────────────────────────────────────────
-- Format: (mv, mn, schema, table, policy_name)
expected_policies(mv, mn, sn, tbl, pol) AS (VALUES
    -- initial_schema (public)
    ('20260524000000','initial_schema','public','profiles','profiles: select own'),
    ('20260524000000','initial_schema','public','profiles','profiles: update own'),
    ('20260524000000','initial_schema','public','speeches','speeches: select own'),
    ('20260524000000','initial_schema','public','speeches','speeches: insert own'),
    ('20260524000000','initial_schema','public','speeches','speeches: update own'),
    ('20260524000000','initial_schema','public','speeches','speeches: delete own'),
    ('20260524000000','initial_schema','public','transcripts','transcripts: select own'),
    ('20260524000000','initial_schema','public','argument_maps','argument_maps: select own'),
    ('20260524000000','initial_schema','public','feedback_reports','feedback_reports: select own'),
    ('20260524000000','initial_schema','public','drills','drills: select own'),
    ('20260524000000','initial_schema','public','drill_attempts','drill_attempts: select own'),
    ('20260524000000','initial_schema','public','drill_attempts','drill_attempts: insert own'),
    -- add_teams
    ('20260602000000','add_teams','public','teams','teams: select own'),
    ('20260602000000','add_teams','public','teams','teams: insert own'),
    ('20260602000000','add_teams','public','team_members','team_members: select own'),
    ('20260602000000','add_teams','public','team_members','team_members: insert self'),
    -- add_xp_ledger
    ('20260604000000','add_xp_ledger','public','user_xp_events','Users can read own XP events'),
    ('20260604000000','add_xp_ledger','public','user_xp_events','Service role can insert XP events'),
    -- add_evidence_tables
    ('20260608100000','add_evidence_tables','public','documents','users_own_documents'),
    ('20260608100000','add_evidence_tables','public','document_chunks','users_own_chunks'),
    ('20260608100000','add_evidence_tables','public','evidence_cards','users_own_cards'),
    ('20260608100000','add_evidence_tables','public','claim_evidence_checks','users_own_claim_checks'),
    -- fix_document_storage_policies (storage schema)
    ('20260608110000','fix_document_storage_policies','storage','objects','docs_storage_insert'),
    ('20260608110000','fix_document_storage_policies','storage','objects','docs_storage_select'),
    ('20260608110000','fix_document_storage_policies','storage','objects','docs_storage_delete'),
    ('20260608110000','fix_document_storage_policies','storage','objects','docs_storage_update'),
    -- add_pilot_tables
    ('20260609000000','add_pilot_tables','public','product_events','product_events_select_own'),
    ('20260609000000','add_pilot_tables','public','product_events','product_events_insert_own'),
    ('20260609000000','add_pilot_tables','public','drill_ratings','drill_ratings_select_own'),
    ('20260609000000','add_pilot_tables','public','drill_ratings','drill_ratings_insert_own'),
    ('20260609000000','add_pilot_tables','public','drill_ratings','drill_ratings_update_own'),
    ('20260609000000','add_pilot_tables','public','output_feedback','output_feedback_select_own'),
    ('20260609000000','add_pilot_tables','public','output_feedback','output_feedback_insert_own'),
    -- add_analysis_jobs
    ('20260609300000','add_analysis_jobs','public','analysis_jobs','Users can view own analysis jobs'),
    -- add_delivery_metrics
    ('20260609500000','add_delivery_metrics','public','delivery_metrics','delivery_metrics: select own'),
    ('20260609500000','add_delivery_metrics','public','delivery_metrics','delivery_metrics: service insert'),
    ('20260609500000','add_delivery_metrics','public','delivery_metrics','delivery_metrics: service update'),
    ('20260609500000','add_delivery_metrics','public','delivery_metrics','delivery_metrics: service delete'),
    -- add_shared_reports
    ('20260609700000','add_shared_reports','public','shared_reports','shared_reports_owner_select'),
    ('20260609700000','add_shared_reports','public','shared_reports','shared_reports_owner_insert'),
    ('20260609700000','add_shared_reports','public','shared_reports','shared_reports_owner_update'),
    ('20260609700000','add_shared_reports','public','shared_reports','shared_reports_owner_delete'),
    -- add_workouts
    ('20260609800000','add_workouts','public','workouts','workouts_owner_select'),
    ('20260609800000','add_workouts','public','workouts','workouts_owner_update'),
    ('20260609800000','add_workouts','public','workouts','workouts_owner_delete'),
    -- add_blockfile_tables
    ('20260609900000','add_blockfile_tables','public','block_entries','block_entries_owner_select'),
    ('20260609900000','add_blockfile_tables','public','block_entries','block_entries_owner_update'),
    ('20260609900000','add_blockfile_tables','public','block_entries','block_entries_owner_delete'),
    ('20260609900000','add_blockfile_tables','public','block_coverage_checks','coverage_owner_select'),
    -- add_research_tables
    ('20260610000000','add_research_tables','public','research_sources','users_own_research_sources'),
    ('20260610000000','add_research_tables','public','research_sources','service_role_research_sources'),
    ('20260610000000','add_research_tables','public','card_drafts','users_own_card_drafts'),
    ('20260610000000','add_research_tables','public','card_drafts','service_role_card_drafts'),
    -- add_assignments
    ('20260618000000','add_assignments','public','assignments','assignments: select team members'),
    ('20260618000000','add_assignments','public','assignments','assignments: insert coach'),
    ('20260618000000','add_assignments','public','assignments','assignments: modify coach'),
    ('20260618000000','add_assignments','public','assignment_recipients','assignment_recipients: select own or coach'),
    ('20260618000000','add_assignments','public','assignment_recipients','assignment_recipients: update own'),
    ('20260618000000','add_assignments','public','assignment_recipients','assignment_recipients: update coach'),
    ('20260618000000','add_assignments','public','assignment_recipients','assignment_recipients: insert coach'),
    -- pass13_evidence_library
    ('20260622010000','pass13_evidence_library','public','resolutions','resolutions_owner'),
    ('20260622010000','pass13_evidence_library','public','resolutions','resolutions_team_read'),
    ('20260622010000','pass13_evidence_library','public','resolutions','resolutions_service_role'),
    ('20260622010000','pass13_evidence_library','public','arguments','arguments_owner'),
    ('20260622010000','pass13_evidence_library','public','arguments','arguments_service_role'),
    ('20260622010000','pass13_evidence_library','public','evidence_sources','evidence_sources_owner'),
    ('20260622010000','pass13_evidence_library','public','evidence_sources','evidence_sources_service_role'),
    ('20260622010000','pass13_evidence_library','public','library_card_metadata','library_card_metadata_owner'),
    ('20260622010000','pass13_evidence_library','public','library_card_metadata','library_card_metadata_service_role'),
    ('20260622010000','pass13_evidence_library','public','blockfiles','blockfiles_owner'),
    ('20260622010000','pass13_evidence_library','public','blockfiles','blockfiles_team_read'),
    ('20260622010000','pass13_evidence_library','public','blockfiles','blockfiles_service_role'),
    ('20260622010000','pass13_evidence_library','public','blockfile_sections','blockfile_sections_owner'),
    ('20260622010000','pass13_evidence_library','public','blockfile_sections','blockfile_sections_service_role'),
    ('20260622010000','pass13_evidence_library','public','blockfile_entries','blockfile_entries_owner'),
    ('20260622010000','pass13_evidence_library','public','blockfile_entries','blockfile_entries_service_role'),
    ('20260622010000','pass13_evidence_library','public','frontlines','frontlines_owner'),
    ('20260622010000','pass13_evidence_library','public','frontlines','frontlines_service_role'),
    ('20260622010000','pass13_evidence_library','public','frontline_responses','frontline_responses_owner'),
    ('20260622010000','pass13_evidence_library','public','frontline_responses','frontline_responses_service_role'),
    ('20260622010000','pass13_evidence_library','public','frontline_response_cards','frontline_response_cards_owner'),
    ('20260622010000','pass13_evidence_library','public','frontline_response_cards','frontline_response_cards_service_role'),
    ('20260622010000','pass13_evidence_library','public','card_relationships','card_relationships_creator'),
    ('20260622010000','pass13_evidence_library','public','card_relationships','card_relationships_service_role'),
    ('20260622010000','pass13_evidence_library','public','card_versions','card_versions_owner'),
    ('20260622010000','pass13_evidence_library','public','card_versions','card_versions_service_role'),
    ('20260622010000','pass13_evidence_library','public','frontline_performance_log','frontline_performance_log_owner'),
    ('20260622010000','pass13_evidence_library','public','frontline_performance_log','frontline_performance_log_service_role'),
    -- pass14_tournament_prep
    ('20260622020000','pass14_tournament_prep','public','prep_workspaces','prep_workspaces_owner'),
    ('20260622020000','pass14_tournament_prep','public','prep_workspaces','prep_workspaces_service_role'),
    ('20260622020000','pass14_tournament_prep','public','prep_gaps','prep_gaps_owner'),
    ('20260622020000','pass14_tournament_prep','public','prep_gaps','prep_gaps_service_role'),
    ('20260622020000','pass14_tournament_prep','public','prep_readiness_reports','prep_readiness_reports_owner'),
    ('20260622020000','pass14_tournament_prep','public','prep_readiness_reports','prep_readiness_reports_service_role'),
    ('20260622020000','pass14_tournament_prep','public','prep_tasks','prep_tasks_owner'),
    ('20260622020000','pass14_tournament_prep','public','prep_tasks','prep_tasks_coach_read'),
    ('20260622020000','pass14_tournament_prep','public','prep_tasks','prep_tasks_service_role'),
    ('20260622020000','pass14_tournament_prep','public','prep_workouts','prep_workouts_owner'),
    ('20260622020000','pass14_tournament_prep','public','prep_workouts','prep_workouts_service_role'),
    -- pass15_judge_adaptation
    ('20260622030000','pass15_judge_adaptation','public','judge_profiles','judge_profiles_owner'),
    ('20260622030000','pass15_judge_adaptation','public','judge_profiles','judge_profiles_public_read'),
    ('20260622030000','pass15_judge_adaptation','public','judge_profiles','judge_profiles_service_role'),
    ('20260622030000','pass15_judge_adaptation','public','judge_adaptations','judge_adaptations_owner'),
    ('20260622030000','pass15_judge_adaptation','public','judge_adaptations','judge_adaptations_service_role'),
    ('20260622030000','pass15_judge_adaptation','public','judge_adaptation_notes','judge_adaptation_notes_owner'),
    ('20260622030000','pass15_judge_adaptation','public','judge_adaptation_notes','judge_adaptation_notes_service_role'),
    ('20260622030000','pass15_judge_adaptation','public','judge_workout_assignments','judge_workout_assignments_student'),
    ('20260622030000','pass15_judge_adaptation','public','judge_workout_assignments','judge_workout_assignments_coach_read'),
    ('20260622030000','pass15_judge_adaptation','public','judge_workout_assignments','judge_workout_assignments_service_role'),
    -- pass15p5_evidence_studio (conditional policy — may have been created if not exists)
    ('20260622040000','pass15p5_evidence_studio','public','documents','service_role_documents'),
    -- pass15p6_save_fix (conditional policies)
    ('20260623010000','pass15p6_save_fix','public','evidence_cards','service_role_evidence_cards'),
    ('20260623010000','pass15p6_save_fix','public','document_chunks','service_role_document_chunks'),
    -- pass16_round_simulation
    ('20260623020000','pass16_round_simulation','public','round_simulations','Users own their round simulations'),
    ('20260623020000','pass16_round_simulation','public','round_simulations','Service role can manage round simulations'),
    ('20260623020000','pass16_round_simulation','public','round_participants','Users see participants in their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_participants','Service role can manage round participants'),
    ('20260623020000','pass16_round_simulation','public','round_speeches','Users see speeches in their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_speeches','Service role can manage round speeches'),
    ('20260623020000','pass16_round_simulation','public','round_crossfire_exchanges','Users see crossfire in their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_crossfire_exchanges','Service role can manage round crossfire'),
    ('20260623020000','pass16_round_simulation','public','round_arguments','Users see arguments in their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_arguments','Service role can manage round arguments'),
    ('20260623020000','pass16_round_simulation','public','round_flow_events','Users see flow events in their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_flow_events','Service role can manage round flow events'),
    ('20260623020000','pass16_round_simulation','public','round_evidence_uses','Users see evidence uses in their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_evidence_uses','Service role can manage round evidence uses'),
    ('20260623020000','pass16_round_simulation','public','round_decisions','Users see decisions for their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_decisions','Service role can manage round decisions'),
    ('20260623020000','pass16_round_simulation','public','round_drills','Users see drills for their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_drills','Service role can manage round drills'),
    ('20260623020000','pass16_round_simulation','public','opponent_round_plans','Users see opponent plans for their rounds'),
    ('20260623020000','pass16_round_simulation','public','opponent_round_plans','Service role can manage opponent round plans'),
    ('20260623020000','pass16_round_simulation','public','round_adaptation_reviews','Users see adaptation reviews for their rounds'),
    ('20260623020000','pass16_round_simulation','public','round_adaptation_reviews','Service role can manage round adaptation reviews'),
    -- pass16_round_legality
    ('20260623025000','pass16_round_legality','public','round_legality_checks','round_legality_checks_read'),
    ('20260623025000','pass16_round_legality','public','round_legality_checks','round_legality_checks_service_role'),
    -- pass17_round_quality
    ('20260623040000','pass17_round_quality','public','round_coach_annotations','coach_annotations_owner'),
    ('20260623040000','pass17_round_quality','public','round_finding_ratings','finding_ratings_owner'),
    ('20260623040000','pass17_round_quality','public','round_strategic_memory','strategic_memory_round_owner'),
    ('20260623040000','pass17_round_quality','public','round_replay_markers','replay_markers_round_owner'),
    ('20260623040000','pass17_round_quality','public','round_quality_reports','quality_reports_round_owner'),
    -- pass18_pilot
    ('20260623050000','pass18_pilot','public','usage_limits','usage_limits_owner_read'),
    ('20260623050000','pass18_pilot','public','usage_limits','usage_limits_service_role'),
    ('20260623050000','pass18_pilot','public','onboarding_progress','onboarding_progress_owner'),
    ('20260623050000','pass18_pilot','public','onboarding_progress','onboarding_progress_service_role')
),
policy_checks AS (
    SELECT ep.mv AS migration_version, ep.mn AS migration_name,
           'policy'::text AS check_type,
           ep.sn || '.' || ep.tbl || '/' || ep.pol AS object_name,
           EXISTS (
               SELECT 1 FROM pg_policies
               WHERE schemaname = ep.sn
                 AND tablename  = ep.tbl
                 AND policyname = ep.pol
           ) AS ok
    FROM expected_policies ep
),

-- ── 7. Functions ──────────────────────────────────────────────────────────────
expected_functions(mv, mn, obj) AS (VALUES
    ('20260524000000','initial_schema','set_updated_at'),
    ('20260524000000','initial_schema','handle_new_user'),
    ('20260609300000','add_analysis_jobs','set_analysis_jobs_updated_at'),
    ('20260609600000','add_pgvector_embeddings','match_document_chunks'),
    ('20260609900000','add_blockfile_tables','match_block_entries'),
    ('20260623020000','pass16_round_simulation','update_round_updated_at')
),
function_checks AS (
    SELECT ef.mv AS migration_version, ef.mn AS migration_name,
           'function'::text AS check_type, ef.obj AS object_name,
           EXISTS (
               SELECT 1 FROM pg_proc p
               JOIN pg_namespace n ON n.oid = p.pronamespace
               WHERE n.nspname = 'public' AND p.proname = ef.obj
           ) AS ok
    FROM expected_functions ef
),

-- ── 8. Triggers ───────────────────────────────────────────────────────────────
-- (tbl_schema is 'auth' for on_auth_user_created, 'public' for all others)
expected_triggers(mv, mn, tbl, tbl_schema, trg) AS (VALUES
    ('20260524000000','initial_schema','users','auth','on_auth_user_created'),
    ('20260524000000','initial_schema','speeches','public','set_speeches_updated_at'),
    ('20260609300000','add_analysis_jobs','analysis_jobs','public','analysis_jobs_updated_at'),
    ('20260609500000','add_delivery_metrics','delivery_metrics','public','set_delivery_metrics_updated_at'),
    ('20260623020000','pass16_round_simulation','round_simulations','public','trg_round_simulations_updated_at'),
    ('20260623020000','pass16_round_simulation','round_arguments','public','trg_round_arguments_updated_at')
),
trigger_checks AS (
    SELECT et.mv AS migration_version, et.mn AS migration_name,
           'trigger'::text AS check_type, et.tbl || '.' || et.trg AS object_name,
           EXISTS (
               SELECT 1 FROM pg_trigger t
               JOIN pg_class c ON c.oid = t.tgrelid
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE t.tgname  = et.trg
                 AND c.relname = et.tbl
                 AND n.nspname = et.tbl_schema
           ) AS ok
    FROM expected_triggers et
),

-- ── 9. Extensions ─────────────────────────────────────────────────────────────
expected_extensions(mv, mn, obj) AS (VALUES
    ('20260609600000','add_pgvector_embeddings','vector')
),
extension_checks AS (
    SELECT ee.mv AS migration_version, ee.mn AS migration_name,
           'extension'::text AS check_type, ee.obj AS object_name,
           EXISTS (SELECT 1 FROM pg_extension WHERE extname = ee.obj) AS ok
    FROM expected_extensions ee
),

-- ── 10. Views ─────────────────────────────────────────────────────────────────
expected_views(mv, mn, obj) AS (VALUES
    ('20260623050000','pass18_pilot','pilot_cost_summary')
),
view_checks AS (
    SELECT ev.mv AS migration_version, ev.mn AS migration_name,
           'view'::text AS check_type, ev.obj AS object_name,
           EXISTS (
               SELECT 1 FROM pg_views
               WHERE schemaname = 'public' AND viewname = ev.obj
           ) AS ok
    FROM expected_views ev
),

-- ── 11. Named constraints ─────────────────────────────────────────────────────
-- Auto-named constraints follow PostgreSQL's {table}_{cols}_key convention.
-- CHECK constraints created explicitly keep their given names.
expected_constraints(mv, mn, tbl, con) AS (VALUES
    -- initial_schema: UNIQUE (speech_id) on transcripts, argument_maps, feedback_reports
    ('20260524000000','initial_schema','transcripts','transcripts_speech_id_key'),
    ('20260524000000','initial_schema','argument_maps','argument_maps_speech_id_key'),
    ('20260524000000','initial_schema','feedback_reports','feedback_reports_speech_id_key'),
    -- add_teams: UNIQUE (team_id, user_id)
    ('20260602000000','add_teams','team_members','team_members_team_id_user_id_key'),
    -- add_xp_ledger: named UNIQUE
    ('20260604000000','add_xp_ledger','user_xp_events','unique_user_event_key'),
    -- add_pilot_tables: named UNIQUE
    ('20260609000000','add_pilot_tables','drill_ratings','drill_ratings_user_drill_unique'),
    -- expand_drill_order_constraint: named CHECK
    ('20260609100000','expand_drill_order_constraint','drills','drills_order_check'),
    -- relax_drills_order_check: same constraint (idempotent duplicate)
    ('20260609200000','relax_drills_order_check','drills','drills_order_check'),
    -- add_delivery_metrics: UNIQUE (speech_id)
    ('20260609500000','add_delivery_metrics','delivery_metrics','delivery_metrics_speech_id_key'),
    -- add_shared_reports: UNIQUE (share_token)
    ('20260609700000','add_shared_reports','shared_reports','shared_reports_share_token_key'),
    -- add_workouts: named CHECK
    ('20260609800000','add_workouts','workouts','workouts_status_check'),
    -- add_assignments: UNIQUE (assignment_id, user_id)
    ('20260618000000','add_assignments','assignment_recipients','assignment_recipients_assignment_id_user_id_key'),
    -- pass13_evidence_library: named constraints
    ('20260622010000','pass13_evidence_library','evidence_sources','evidence_sources_user_doi_unique'),
    ('20260622010000','pass13_evidence_library','library_card_metadata','library_card_metadata_card_user_unique'),
    ('20260622010000','pass13_evidence_library','frontline_response_cards','frontline_response_cards_unique'),
    ('20260622010000','pass13_evidence_library','card_relationships','card_relationships_unique'),
    -- pass16_round_simulation: inline UNIQUE becomes auto-named
    ('20260623020000','pass16_round_simulation','round_arguments','round_arguments_round_id_label_key'),
    -- pass17_round_quality: inline UNIQUE constraints
    ('20260623040000','pass17_round_quality','round_finding_ratings','round_finding_ratings_round_id_finding_id_rater_id_key'),
    ('20260623040000','pass17_round_quality','round_strategic_memory','round_strategic_memory_round_id_key'),
    ('20260623040000','pass17_round_quality','round_quality_reports','round_quality_reports_round_id_key'),
    -- pass18_pilot: named UNIQUE constraints
    ('20260623050000','pass18_pilot','usage_limits','usage_limits_user_unique'),
    ('20260623050000','pass18_pilot','onboarding_progress','onboarding_progress_user_unique')
),
constraint_checks AS (
    SELECT ec.mv AS migration_version, ec.mn AS migration_name,
           'constraint'::text AS check_type, ec.tbl || '.' || ec.con AS object_name,
           EXISTS (
               SELECT 1 FROM pg_constraint c
               JOIN pg_class cl ON cl.oid = c.conrelid
               JOIN pg_namespace n ON n.oid = cl.relnamespace
               WHERE n.nspname = 'public'
                 AND cl.relname = ec.tbl
                 AND c.conname  = ec.con
           ) AS ok
    FROM expected_constraints ec
),

-- ── All checks unioned ────────────────────────────────────────────────────────
all_checks AS (
    SELECT migration_version, migration_name, check_type, object_name, ok FROM type_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM table_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM column_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM index_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM rls_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM policy_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM function_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM trigger_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM extension_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM view_checks
    UNION ALL
    SELECT migration_version, migration_name, check_type, object_name, ok FROM constraint_checks
)

-- ── Summary: one row per migration ───────────────────────────────────────────
SELECT
    migration_version,
    migration_name,
    bool_and(ok)                                                              AS fully_applied,
    count(*) FILTER (WHERE ok)                                                AS checks_passed,
    count(*)                                                                  AS checks_total,
    coalesce(
        string_agg(check_type || ':' || object_name, ', ')
            FILTER (WHERE NOT ok),
        ''
    )                                                                         AS missing_or_invalid_objects
FROM all_checks
GROUP BY migration_version, migration_name
ORDER BY migration_version;
