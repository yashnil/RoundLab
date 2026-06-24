# RoundLab Database Migration Map

Last updated: 2026-06-23 (Pass 18)

This document maps every migration file to the tables it creates or alters.
Use it alongside `scripts/audit_remote_schema.sql` to validate remote state.

---

## Migration Chain (30 files, strict timestamp order)

| Timestamp        | File                                          | Action Summary                                                                  |
|------------------|-----------------------------------------------|---------------------------------------------------------------------------------|
| 20260524000000   | initial_schema.sql                            | CREATE: profiles, speeches, transcripts, argument_maps, feedback_reports, drills, drill_attempts + enums + triggers |
| 20260601000000   | add_drill_fields.sql                          | ALTER drills: add evidence_drill_type, skill_target                             |
| 20260602000000   | add_teams.sql                                 | CREATE: teams, team_members                                                     |
| 20260602100000   | add_feedback_rating.sql                       | ALTER feedback_reports: add rating, rating_comment                              |
| 20260604000000   | add_xp_ledger.sql                             | CREATE: user_xp_events                                                          |
| 20260606000000   | add_drill_time_limit.sql                      | ALTER drills: add time_limit_seconds                                            |
| 20260607000000   | add_rerecord_fields.sql                       | ALTER speeches: add is_rerecord, parent_speech_id, attempt_number              |
| 20260608100000   | add_evidence_tables.sql                       | CREATE: documents, document_chunks, evidence_cards, claim_evidence_checks       |
| 20260608110000   | fix_document_storage_policies.sql             | CREATE RLS policies on documents for storage                                    |
| 20260609000000   | add_pilot_tables.sql                          | CREATE: product_events, drill_ratings, output_feedback                          |
| 20260609100000   | expand_drill_order_constraint.sql             | ALTER drills: relax order CHECK to >= 1                                         |
| 20260609200000   | relax_drills_order_check.sql                  | Duplicate of above (idempotent — safe to apply)                                 |
| 20260609300000   | add_analysis_jobs.sql                         | CREATE: analysis_jobs                                                           |
| 20260609400000   | add_argument_map_correction.sql               | ALTER argument_maps: add correction fields                                      |
| 20260609500000   | add_delivery_metrics.sql                      | CREATE: delivery_metrics                                                        |
| 20260609600000   | add_pgvector_embeddings.sql                   | EXTENSION pgvector; CREATE FUNCTION match_document_chunks                       |
| 20260609700000   | add_shared_reports.sql                        | CREATE: shared_reports                                                          |
| 20260609800000   | add_workouts.sql                              | CREATE: workouts                                                                |
| 20260609900000   | add_blockfile_tables.sql                      | CREATE: block_entries, block_coverage_checks; CREATE FUNCTION match_block_entries |
| 20260610000000   | add_research_tables.sql                       | CREATE: research_sources, card_drafts; ALTER evidence_cards (add fields)        |
| 20260618000000   | add_assignments.sql                           | CREATE: assignments, assignment_recipients                                       |
| **20260622010000** | **pass13_evidence_library.sql**             | CREATE: resolutions, arguments, evidence_sources, library_card_metadata, blockfiles, blockfile_sections, blockfile_entries, frontlines, frontline_responses, frontline_response_cards, card_relationships, card_versions, frontline_performance_log |
| **20260622020000** | **pass14_tournament_prep.sql**              | CREATE: prep_workspaces, prep_gaps, prep_readiness_reports, prep_tasks, prep_workouts |
| **20260622030000** | **pass15_judge_adaptation.sql**             | CREATE: judge_profiles, judge_adaptations, judge_adaptation_notes, judge_workout_assignments |
| **20260622040000** | **pass15p5_evidence_studio.sql**            | CREATE POLICY + UNIQUE INDEX on documents (service_role bypass + upsert dedup)  |
| 20260623010000   | pass15p6_save_fix.sql                         | ALTER evidence_cards: card_text NOT NULL default, add cite column               |
| 20260623020000   | pass16_round_simulation.sql                   | CREATE: round_simulations, round_participants, round_speeches, round_crossfire_exchanges, round_arguments, round_flow_events, round_evidence_uses, round_decisions, round_drills, opponent_round_plans, round_adaptation_reviews; ALTER prep_gaps (add round_simulation_id) |
| **20260623025000** | **pass16_round_legality.sql**               | CREATE: round_legality_checks; ALTER frontline_performance_log (add round_simulation_id) |
| 20260623030000   | pass16p5_round_auth.sql                       | ALTER round_simulations (add phase_started_at); ALTER round_speeches (add idempotency_key); ALTER prep_gaps (add fingerprint, occurrence_count, first_seen_at, last_seen_at, last_round_id, status) |
| 20260623040000   | pass17_round_quality.sql                      | CREATE: round_coach_annotations, round_finding_ratings, round_strategic_memory, round_replay_markers, round_quality_reports |
| 20260623050000   | pass18_pilot.sql                              | CREATE: usage_limits, onboarding_progress; CREATE INDEXES on product_events + round_simulations; CREATE VIEW pilot_cost_summary |

**Bold** = migrations created or corrected in this audit (Pass 18.5).

---

## Table Inventory by Domain

### Auth & Identity (pre-existing Supabase)
- `auth.users` — Supabase managed

### Core User Data (initial_schema + early passes)
- `profiles` — 20260524
- `speeches` — 20260524 (+ ALTERs in 20260607)
- `transcripts` — 20260524
- `argument_maps` — 20260524 (+ ALTER in 20260609400000)
- `feedback_reports` — 20260524 (+ ALTER in 20260602100000)
- `drills` — 20260524 (+ ALTERs in 20260601/06/09100/09200)
- `drill_attempts` — 20260524
- `user_xp_events` — 20260604

### Team & Assignment
- `teams` — 20260602
- `team_members` — 20260602
- `assignments` — 20260618
- `assignment_recipients` — 20260618

### Evidence & Research (Pass 8–12)
- `documents` — 20260608100000
- `document_chunks` — 20260608100000
- `evidence_cards` — 20260608100000 (+ ALTERs in 20260610000000, 20260623010000)
- `claim_evidence_checks` — 20260608100000
- `research_sources` — 20260610000000
- `card_drafts` — 20260610000000

### Pilot & Analytics
- `product_events` — 20260609000000
- `drill_ratings` — 20260609000000
- `output_feedback` — 20260609000000
- `analysis_jobs` — 20260609300000
- `delivery_metrics` — 20260609500000
- `shared_reports` — 20260609700000
- `workouts` — 20260609800000
- `usage_limits` — 20260623050000
- `onboarding_progress` — 20260623050000

### Blockfile Trainer (Pass 10, distinct from Evidence Library blockfiles)
- `block_entries` — 20260609900000
- `block_coverage_checks` — 20260609900000

### Evidence Library (Pass 13)
- `resolutions` — 20260622010000
- `arguments` — 20260622010000
- `evidence_sources` — 20260622010000
- `library_card_metadata` — 20260622010000
- `blockfiles` — 20260622010000
- `blockfile_sections` — 20260622010000
- `blockfile_entries` — 20260622010000
- `frontlines` — 20260622010000
- `frontline_responses` — 20260622010000
- `frontline_response_cards` — 20260622010000
- `card_relationships` — 20260622010000
- `card_versions` — 20260622010000
- `frontline_performance_log` — 20260622010000

### Tournament Prep (Pass 14)
- `prep_workspaces` — 20260622020000
- `prep_gaps` — 20260622020000 (+ ALTERs in 20260623020000, 20260623030000)
- `prep_readiness_reports` — 20260622020000
- `prep_tasks` — 20260622020000
- `prep_workouts` — 20260622020000

### Judge Adaptation (Pass 15)
- `judge_profiles` — 20260622030000
- `judge_adaptations` — 20260622030000
- `judge_adaptation_notes` — 20260622030000
- `judge_workout_assignments` — 20260622030000

### Round Simulation (Pass 16)
- `round_simulations` — 20260623020000
- `round_participants` — 20260623020000
- `round_speeches` — 20260623020000
- `round_crossfire_exchanges` — 20260623020000
- `round_arguments` — 20260623020000
- `round_flow_events` — 20260623020000
- `round_evidence_uses` — 20260623020000
- `round_decisions` — 20260623020000
- `round_drills` — 20260623020000
- `opponent_round_plans` — 20260623020000
- `round_adaptation_reviews` — 20260623020000
- `round_legality_checks` — 20260623025000

### Coach Review (Pass 17)
- `round_coach_annotations` — 20260623040000
- `round_finding_ratings` — 20260623040000
- `round_strategic_memory` — 20260623040000
- `round_replay_markers` — 20260623040000
- `round_quality_reports` — 20260623040000

---

## RPC Functions
| Function                | Created in migration      |
|-------------------------|---------------------------|
| `match_document_chunks` | 20260609600000            |
| `match_block_entries`   | 20260609900000            |

## Views
| View                 | Created in migration |
|----------------------|----------------------|
| `pilot_cost_summary` | 20260623050000       |

## Storage Buckets (managed outside migrations)
- `audio` — for uploaded audio files
- `speeches` — for processed speech audio
- `documents` — for uploaded research documents

---

## Known Issues in this Migration Chain

1. **Duplicate migration** — `20260609100000` and `20260609200000` both perform the same `drills` constraint change. Idempotent (safe), but redundant.
2. **Soft FKs in prep_gaps** — `argument_id`, `blockfile_id`, `section_id`, `card_id`, `frontline_id` are stored as `uuid` without `REFERENCES` constraints to avoid circular dependency ordering.
3. **Dynamic source columns in judge_adaptations** — `source_evidence_id`, `source_argument_id`, etc. are nullable UUIDs without FK constraints because they point to different tables depending on `source_type`.
4. **frontline_performance_log has no application writer** — the table exists for future use; currently no backend service inserts into it.
