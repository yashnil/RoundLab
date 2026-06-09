-- =============================================================================
-- RoundLab — Relax drills order constraint to allow evidence drills
-- Migration: 20260609200000_relax_drills_order_check.sql
--
-- Standard drills use order 1–3.
-- Evidence drills are inserted after standard drills and need order 4+.
-- The original schema had CHECK ("order" BETWEEN 1 AND 3); this drops that
-- and replaces it with CHECK ("order" >= 1) so any positive order is valid.
--
-- Apply via: Supabase Dashboard → SQL Editor → paste and run.
-- Or via CLI: supabase db push (once project is linked).
-- =============================================================================

ALTER TABLE public.drills
  DROP CONSTRAINT IF EXISTS drills_order_check;

ALTER TABLE public.drills
  ADD CONSTRAINT drills_order_check CHECK ("order" >= 1);

COMMENT ON COLUMN public.drills."order"
  IS 'Display order within the drill list for a speech. Standard drills use 1–3; evidence drills use 4+.';

-- Tell PostgREST to reload its schema cache so the new constraint is visible
-- immediately without a container restart.
NOTIFY pgrst, 'reload schema';
