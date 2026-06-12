-- Research-to-Card Evidence Builder
-- Extends evidence_cards with card-cutting fields.
-- Adds research_sources and card_drafts tables.

-- ── 1. Extend evidence_cards ──────────────────────────────────────────────────

ALTER TABLE public.evidence_cards
  ADD COLUMN IF NOT EXISTS url                      text,
  ADD COLUMN IF NOT EXISTS title                    text,
  ADD COLUMN IF NOT EXISTS publication              text,
  ADD COLUMN IF NOT EXISTS author_credentials       text,
  ADD COLUMN IF NOT EXISTS published_date           text,
  ADD COLUMN IF NOT EXISTS body_text                text,
  ADD COLUMN IF NOT EXISTS highlighted_spans_json   jsonb     NOT NULL DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS underline_spans_json     jsonb     NOT NULL DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS card_cutting_metadata_json jsonb   NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS source_quality           text
    CHECK (source_quality IN ('high','medium','low','unknown') OR source_quality IS NULL),
  ADD COLUMN IF NOT EXISTS extraction_confidence    numeric,
  ADD COLUMN IF NOT EXISTS generated_tag            boolean   NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS user_reviewed            boolean   NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS card_source_type         text
    CHECK (card_source_type IN ('uploaded_document','url','manual_paste','research_search')
           OR card_source_type IS NULL);

-- ── 2. research_sources ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.research_sources (
  id                       uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                  uuid          NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  query                    text,
  url                      text          NOT NULL,
  title                    text,
  publication              text,
  author                   text,
  published_date           text,
  extracted_text           text,
  extraction_metadata_json jsonb         NOT NULL DEFAULT '{}',
  source_quality           text
    CHECK (source_quality IN ('high','medium','low','unknown') OR source_quality IS NULL),
  status                   text          NOT NULL DEFAULT 'fetched'
    CHECK (status IN ('fetched','failed','card_generated','saved')),
  error_message            text,
  created_at               timestamptz   NOT NULL DEFAULT now(),
  updated_at               timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_sources_user_id_idx
  ON public.research_sources (user_id);

ALTER TABLE public.research_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_research_sources"
  ON public.research_sources FOR ALL
  USING  (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "service_role_research_sources"
  ON public.research_sources FOR ALL
  TO service_role USING (true) WITH CHECK (true);

-- ── 3. card_drafts ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.card_drafts (
  id                     uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                uuid          NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  research_source_id     uuid          REFERENCES public.research_sources(id) ON DELETE SET NULL,
  url                    text,
  topic                  text,
  claim_goal             text,
  side                   text,
  tag                    text          NOT NULL DEFAULT '',
  cite                   text          NOT NULL DEFAULT '',
  body_text              text          NOT NULL DEFAULT '',
  highlighted_spans_json jsonb         NOT NULL DEFAULT '[]',
  underline_spans_json   jsonb         NOT NULL DEFAULT '[]',
  author                 text,
  publication            text,
  title                  text,
  published_date         text,
  author_credentials     text,
  warrant_summary        text,
  impact_summary         text,
  source_quality         text
    CHECK (source_quality IN ('high','medium','low','unknown') OR source_quality IS NULL),
  credibility_notes      text,
  extraction_confidence  numeric,
  generated_tag          boolean       NOT NULL DEFAULT true,
  missing_metadata_json  jsonb         NOT NULL DEFAULT '{}',
  draft_json             jsonb         NOT NULL DEFAULT '{}',
  card_source_type       text
    CHECK (card_source_type IN ('url','manual_paste','research_search') OR card_source_type IS NULL),
  status                 text          NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','saved','discarded')),
  saved_card_id          uuid          REFERENCES public.evidence_cards(id) ON DELETE SET NULL,
  created_at             timestamptz   NOT NULL DEFAULT now(),
  updated_at             timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS card_drafts_user_id_idx   ON public.card_drafts (user_id);
CREATE INDEX IF NOT EXISTS card_drafts_status_idx    ON public.card_drafts (status);

ALTER TABLE public.card_drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_card_drafts"
  ON public.card_drafts FOR ALL
  USING  (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "service_role_card_drafts"
  ON public.card_drafts FOR ALL
  TO service_role USING (true) WITH CHECK (true);

-- PostgREST schema reload
NOTIFY pgrst, 'reload schema';
