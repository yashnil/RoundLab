-- =============================================================================
-- RoundLab — Pass 15.5: Evidence Studio Reliability
-- Migration: 20260622_pass15p5_evidence_studio.sql
--
-- 1. Adds service_role bypass policy to documents (so the backend's
--    service-role client can write the per-user Research Library row).
-- 2. Adds a unique index on (user_id, storage_path) so the upsert pattern
--    in _get_or_create_research_doc is race-safe.
-- =============================================================================

-- Service-role can read/write all documents (bypasses RLS for backend pipeline).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename  = 'documents'
      AND policyname = 'service_role_documents'
  ) THEN
    EXECUTE $policy$
      CREATE POLICY service_role_documents
        ON public.documents FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
    $policy$;
  END IF;
END;
$$;

-- Unique index so concurrent upserts don't create duplicate Research Library
-- rows for the same user.  Uses a partial index scoped to the sentinel path.
CREATE UNIQUE INDEX IF NOT EXISTS documents_user_research_unique
  ON public.documents (user_id, storage_path)
  WHERE storage_path = '_research';

-- PostgREST schema reload
NOTIFY pgrst, 'reload schema';
