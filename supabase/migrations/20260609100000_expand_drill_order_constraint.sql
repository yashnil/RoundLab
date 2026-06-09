-- =============================================================================
-- RoundLab — Expand drill order constraint
-- Migration: 20260609100000_expand_drill_order_constraint.sql
--
-- The original schema limited drills.order to 1–3 (exactly 3 drills per speech).
-- Evidence-specific drills (evidence_alignment, claim_precision, evidence_attribution)
-- are inserted as additional drills after the standard 3, requiring order 4+.
--
-- This migration drops the old 1–3 constraint and replaces it with order >= 1,
-- allowing any positive integer order value (application code is the real guard).
-- =============================================================================

ALTER TABLE public.drills
  DROP CONSTRAINT IF EXISTS drills_order_check;

ALTER TABLE public.drills
  ADD CONSTRAINT drills_order_check CHECK ("order" >= 1);

COMMENT ON COLUMN public.drills."order"
  IS 'Display order within the drill list for a speech. Standard drills use 1–3; evidence drills may use 4+.';
