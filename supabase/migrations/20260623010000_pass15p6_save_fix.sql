-- Pass 15.6: Fix evidence_cards save pipeline
-- Root causes:
--   1. evidence_cards.card_text is TEXT NOT NULL with no DEFAULT.
--      The save code inserted body_text but not card_text, triggering a
--      null-value constraint violation.
--   2. evidence_cards had no cite column.  The save code tried to insert
--      the cite field from card_drafts, causing an unknown-column error.
-- Fix: add DEFAULT '' to card_text and add cite column.
-- Also add service_role bypass policies for evidence_cards and document_chunks
-- (belt-and-suspenders; the service-role key already bypasses RLS, but explicit
-- policies make intent clear and prevent future surprises).

-- ── 1. Patch evidence_cards ────────────────────────────────────────────────────

ALTER TABLE public.evidence_cards
  ALTER COLUMN card_text  SET DEFAULT '',
  ADD COLUMN IF NOT EXISTS cite text DEFAULT '';

-- ── 2. service_role policies ──────────────────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename  = 'evidence_cards'
      AND policyname = 'service_role_evidence_cards'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY service_role_evidence_cards
        ON public.evidence_cards FOR ALL
        TO service_role USING (true) WITH CHECK (true);
    $policy$;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename  = 'document_chunks'
      AND policyname = 'service_role_document_chunks'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY service_role_document_chunks
        ON public.document_chunks FOR ALL
        TO service_role USING (true) WITH CHECK (true);
    $policy$;
  END IF;
END $$;

-- PostgREST schema reload
NOTIFY pgrst, 'reload schema';
