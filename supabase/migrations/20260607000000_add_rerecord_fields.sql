-- =============================================================================
-- RoundLab — Add re-record relationship columns to speeches
-- Migration: 20260607000000_add_rerecord_fields.sql
--
-- Links a re-recorded speech back to the original speech it is improving upon,
-- and to the specific drill that motivated the re-record.
-- Both columns are nullable and safe to add with IF NOT EXISTS.
-- =============================================================================

ALTER TABLE public.speeches
  ADD COLUMN IF NOT EXISTS parent_speech_id uuid REFERENCES public.speeches(id),
  ADD COLUMN IF NOT EXISTS source_drill_id   uuid REFERENCES public.drills(id);

COMMENT ON COLUMN public.speeches.parent_speech_id IS
  'ID of the original speech this was recorded to improve upon (re-record relationship).';

COMMENT ON COLUMN public.speeches.source_drill_id IS
  'ID of the drill that motivated this re-record, used for improvement comparison.';
