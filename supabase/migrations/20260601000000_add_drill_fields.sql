-- =============================================================================
-- RoundLab — Add Drill Fields
-- Migration: 20260601000000_add_drill_fields.sql
--
-- Adds richer columns to the drills table needed for v1 personalized drills.
-- All additions are nullable or have safe defaults so they are non-breaking.
-- =============================================================================

ALTER TABLE public.drills
  ADD COLUMN IF NOT EXISTS instructions       text,
  ADD COLUMN IF NOT EXISTS success_criteria   jsonb    NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS source_weakness    text,
  ADD COLUMN IF NOT EXISTS difficulty         text     NOT NULL DEFAULT 'beginner',
  ADD COLUMN IF NOT EXISTS status             text     NOT NULL DEFAULT 'assigned';

COMMENT ON COLUMN public.drills.instructions     IS 'Step-by-step guidance for the drill exercise.';
COMMENT ON COLUMN public.drills.success_criteria IS 'JSON array of strings — checklist of what ''good'' looks like.';
COMMENT ON COLUMN public.drills.source_weakness  IS 'The specific feedback weakness this drill targets.';
COMMENT ON COLUMN public.drills.difficulty       IS 'beginner | intermediate | advanced';
COMMENT ON COLUMN public.drills.status           IS 'assigned | attempted | completed';
