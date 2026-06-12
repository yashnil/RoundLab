-- Migration: blockfile and frontline trainer
-- Adds document_role/side/topic to documents, block_entries table,
-- block_coverage_checks table, and match_block_entries RPC.

-- ── 1. Extend documents ──────────────────────────────────────────────────────

ALTER TABLE public.documents
  ADD COLUMN IF NOT EXISTS document_role text
    CHECK (document_role IS NULL OR document_role IN (
      'evidence', 'case', 'blockfile', 'frontline', 'mixed'
    )),
  ADD COLUMN IF NOT EXISTS debate_side text
    CHECK (debate_side IS NULL OR debate_side IN (
      'pro', 'con', 'aff', 'neg', 'both'
    )),
  ADD COLUMN IF NOT EXISTS topic text,
  ADD COLUMN IF NOT EXISTS blockfile_metadata_json jsonb NOT NULL DEFAULT '{}';

-- ── 2. block_entries ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.block_entries (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  document_id      uuid        REFERENCES public.documents(id)       ON DELETE CASCADE,
  source_chunk_id  uuid        REFERENCES public.document_chunks(id) ON DELETE SET NULL,
  entry_type       text        NOT NULL DEFAULT 'unknown'
    CHECK (entry_type IN ('block', 'frontline', 'answer', 'turn', 'defense', 'weighing', 'overview', 'unknown')),
  side             text
    CHECK (side IS NULL OR side IN ('pro', 'con', 'aff', 'neg', 'both')),
  tag              text,
  opponent_claim   text,
  response_text    text        NOT NULL,
  warrant_text     text,
  evidence_text    text,
  impact_text      text,
  weighing_text    text,
  author           text,
  source           text,
  date             text,
  topic            text,
  metadata_json    jsonb       NOT NULL DEFAULT '{}',
  embedding        vector(1536),
  embedding_model  text,
  embedded_at      timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.block_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "block_entries_owner_select"
  ON public.block_entries FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "block_entries_owner_update"
  ON public.block_entries FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "block_entries_owner_delete"
  ON public.block_entries FOR DELETE
  USING (auth.uid() = user_id);

-- Service role handles inserts (backend bypasses RLS)

CREATE INDEX IF NOT EXISTS idx_block_entries_user_id
  ON public.block_entries (user_id);

CREATE INDEX IF NOT EXISTS idx_block_entries_document_id
  ON public.block_entries (document_id);

CREATE INDEX IF NOT EXISTS idx_block_entries_entry_type
  ON public.block_entries (entry_type);

CREATE INDEX IF NOT EXISTS idx_block_entries_side
  ON public.block_entries (side);

CREATE INDEX IF NOT EXISTS idx_block_entries_topic
  ON public.block_entries (topic);

-- HNSW index for fast approximate nearest-neighbour search (conditional)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_extension WHERE extname = 'vector'
  ) THEN
    CREATE INDEX IF NOT EXISTS idx_block_entries_embedding_hnsw
      ON public.block_entries
      USING hnsw (embedding vector_cosine_ops)
      WITH (m = 16, ef_construction = 64);
  END IF;
END
$$;

-- ── 3. block_coverage_checks ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.block_coverage_checks (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                 uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  speech_id               uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  argument_id             text,
  claim_text              text        NOT NULL,
  check_type              text        NOT NULL
    CHECK (check_type IN ('block', 'frontline')),
  status                  text        NOT NULL
    CHECK (status IN ('covered', 'partially_covered', 'missing', 'no_available_block')),
  matched_block_entry_ids jsonb       NOT NULL DEFAULT '[]',
  top_similarity          numeric,
  rationale               text,
  missing_piece           text,
  suggested_drill_json    jsonb,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.block_coverage_checks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "coverage_owner_select"
  ON public.block_coverage_checks FOR SELECT
  USING (auth.uid() = user_id);

-- Service role handles inserts/updates

CREATE INDEX IF NOT EXISTS idx_block_coverage_speech_id
  ON public.block_coverage_checks (speech_id);

CREATE INDEX IF NOT EXISTS idx_block_coverage_user_id
  ON public.block_coverage_checks (user_id);

-- ── 4. match_block_entries RPC ───────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.match_block_entries(
  query_embedding      vector(1536),
  match_user_id        uuid,
  match_count          int     DEFAULT 8,
  similarity_threshold float   DEFAULT 0.30,
  entry_type_filter    text    DEFAULT NULL,
  side_filter          text    DEFAULT NULL
)
RETURNS TABLE (
  id               uuid,
  document_id      uuid,
  entry_type       text,
  side             text,
  tag              text,
  opponent_claim   text,
  response_text    text,
  warrant_text     text,
  evidence_text    text,
  impact_text      text,
  weighing_text    text,
  source           text,
  author           text,
  "date"           text,
  similarity       float
)
LANGUAGE sql STABLE SECURITY INVOKER
AS $$
  SELECT
    be.id,
    be.document_id,
    be.entry_type,
    be.side,
    be.tag,
    be.opponent_claim,
    be.response_text,
    be.warrant_text,
    be.evidence_text,
    be.impact_text,
    be.weighing_text,
    be.source,
    be.author,
    be.date,
    (1 - (be.embedding <=> query_embedding))::float AS similarity
  FROM public.block_entries be
  WHERE
    be.user_id          = match_user_id
    AND be.embedding    IS NOT NULL
    AND (1 - (be.embedding <=> query_embedding)) >= similarity_threshold
    AND (entry_type_filter IS NULL OR be.entry_type = entry_type_filter)
    AND (side_filter IS NULL OR be.side = side_filter OR be.side = 'both')
  ORDER BY be.embedding <=> query_embedding
  LIMIT match_count;
$$;

NOTIFY pgrst, 'reload schema';
