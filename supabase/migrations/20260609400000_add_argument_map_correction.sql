-- =============================================================================
-- RoundLab — argument_maps correction columns
-- Allows users to edit the AI-generated flow and re-run coaching from it.
-- original_arguments preserves the AI draft so nothing is silently overwritten.
-- =============================================================================

ALTER TABLE public.argument_maps
  ADD COLUMN IF NOT EXISTS source_type text NOT NULL DEFAULT 'ai'
    CHECK (source_type IN ('ai', 'user_corrected')),
  ADD COLUMN IF NOT EXISTS original_arguments jsonb,
  ADD COLUMN IF NOT EXISTS user_corrected_at  timestamptz,
  ADD COLUMN IF NOT EXISTS correction_notes   text,
  ADD COLUMN IF NOT EXISTS updated_at         timestamptz NOT NULL DEFAULT now();

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
