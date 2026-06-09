-- =============================================================================
-- Delivery metrics table
-- Stores deterministic speaking-quality metrics derived from transcript + duration.
-- Kept separate from speeches/feedback_reports so it remains additive/optional.
-- =============================================================================

CREATE TABLE public.delivery_metrics (
  id                     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  speech_id              uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  user_id                uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  word_count             integer,
  duration_seconds       integer,
  words_per_minute       numeric,
  filler_word_count      integer,
  filler_words_json      jsonb       NOT NULL DEFAULT '{}',
  repeated_phrases_json  jsonb       NOT NULL DEFAULT '[]',
  long_sentence_count    integer,
  average_sentence_words numeric,
  delivery_score         integer     CHECK (delivery_score BETWEEN 0 AND 100),
  pacing_band            text        CHECK (pacing_band IN ('too_slow', 'steady', 'too_fast', 'unknown')),
  clarity_flags_json     jsonb       NOT NULL DEFAULT '[]',
  timeline_json          jsonb,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  UNIQUE (speech_id)
);

-- Trigger to auto-update updated_at
CREATE TRIGGER set_delivery_metrics_updated_at
  BEFORE UPDATE ON public.delivery_metrics
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS
ALTER TABLE public.delivery_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "delivery_metrics: select own"
  ON public.delivery_metrics FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "delivery_metrics: service insert"
  ON public.delivery_metrics FOR INSERT
  WITH CHECK (true);

CREATE POLICY "delivery_metrics: service update"
  ON public.delivery_metrics FOR UPDATE
  USING (true);

CREATE POLICY "delivery_metrics: service delete"
  ON public.delivery_metrics FOR DELETE
  USING (true);
