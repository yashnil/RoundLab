-- =============================================================================
-- RoundLab — Evidence RAG v1: pgvector semantic search
-- Migration: 20260609600000_add_pgvector_embeddings.sql
--
-- Changes:
--   1. Enable pgvector extension
--   2. Add embedding column to document_chunks
--   3. Add HNSW index for approximate nearest-neighbor search
--   4. Add match_document_chunks SQL function (user-scoped cosine similarity)
--   5. Extend claim_evidence_checks with RAG audit columns
-- =============================================================================


-- 1. Enable pgvector
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS vector;


-- 2. Add embedding columns to document_chunks
-- =============================================================================
ALTER TABLE public.document_chunks
  ADD COLUMN IF NOT EXISTS embedding        vector(1536),
  ADD COLUMN IF NOT EXISTS embedding_model  text,
  ADD COLUMN IF NOT EXISTS embedded_at      timestamptz;


-- 3. HNSW index for cosine similarity search
--    Wrapped in DO block so the migration succeeds even if the pgvector version
--    does not yet support HNSW (falls back gracefully, index can be added later).
-- =============================================================================
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename   = 'document_chunks'
      AND indexname   = 'document_chunks_embedding_hnsw_idx'
  ) THEN
    BEGIN
      EXECUTE '
        CREATE INDEX document_chunks_embedding_hnsw_idx
          ON public.document_chunks
          USING hnsw (embedding vector_cosine_ops)
          WITH (m = 16, ef_construction = 64)
      ';
      RAISE NOTICE 'HNSW index created on document_chunks.embedding';
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'HNSW index not supported on this pgvector version — skipping. '
                   'Add the index manually after upgrading: '
                   'CREATE INDEX document_chunks_embedding_hnsw_idx ON public.document_chunks '
                   'USING hnsw (embedding vector_cosine_ops);';
    END;
  END IF;
END;
$$;


-- 4. match_document_chunks — user-scoped semantic search function
--    Returns chunks ranked by cosine similarity to the query embedding.
--    Only searches chunks owned by match_user_id (RLS equivalent in SQL).
--    Never returns raw embeddings.
-- =============================================================================
CREATE OR REPLACE FUNCTION public.match_document_chunks(
  query_embedding      vector(1536),
  match_user_id        uuid,
  match_count          int     DEFAULT 8,
  similarity_threshold float   DEFAULT 0.30
)
RETURNS TABLE (
  id             uuid,
  document_id    uuid,
  user_id        uuid,
  chunk_text     text,
  chunk_index    int,
  heading        text,
  page_number    int,
  metadata_json  jsonb,
  created_at     timestamptz,
  similarity     float
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    dc.id,
    dc.document_id,
    dc.user_id,
    dc.chunk_text,
    dc.chunk_index,
    dc.heading,
    dc.page_number,
    dc.metadata_json,
    dc.created_at,
    (1 - (dc.embedding <=> query_embedding))::float AS similarity
  FROM  public.document_chunks dc
  WHERE dc.user_id  = match_user_id
    AND dc.embedding IS NOT NULL
    AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Grant execution to service role only.
-- The backend calls this function after enforcing user ownership.
GRANT EXECUTE ON FUNCTION public.match_document_chunks(vector, uuid, int, float)
  TO service_role;


-- 5. Extend claim_evidence_checks with RAG audit columns
-- =============================================================================
ALTER TABLE public.claim_evidence_checks
  ADD COLUMN IF NOT EXISTS matched_chunk_ids        jsonb    NOT NULL DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS top_similarity           numeric,
  ADD COLUMN IF NOT EXISTS retrieved_snippets_json  jsonb    NOT NULL DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS support_rationale        text,
  ADD COLUMN IF NOT EXISTS missing_link             text,
  ADD COLUMN IF NOT EXISTS retrieval_mode           text
    CHECK (retrieval_mode IN ('semantic', 'keyword', 'none', NULL));


-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload schema';
