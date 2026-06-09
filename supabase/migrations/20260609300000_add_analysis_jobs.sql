-- =============================================================================
-- RoundLab — analysis_jobs table
-- Tracks long-running analysis workflows with step progress and error detail.
-- speech_analysis is fully wired; other job types are pre-structured.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.analysis_jobs (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  speech_id     uuid        REFERENCES public.speeches(id)   ON DELETE CASCADE,
  drill_id      uuid        REFERENCES public.drills(id)     ON DELETE CASCADE,
  document_id   uuid        REFERENCES public.documents(id)  ON DELETE CASCADE,
  job_type      text        NOT NULL
                            CHECK (job_type IN (
                              'speech_analysis',
                              'drill_attempt_scoring',
                              'evidence_check',
                              'evidence_drill_generation',
                              'document_parse'
                            )),
  status        text        NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  current_step  text,
  progress      integer     CHECK (progress IS NULL OR (progress >= 0 AND progress <= 100)),
  error_message text,
  error_code    text,
  result_json   jsonb,
  attempt_count integer     NOT NULL DEFAULT 0,
  started_at    timestamptz,
  completed_at  timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS analysis_jobs_speech_id_idx
  ON public.analysis_jobs (speech_id);

CREATE INDEX IF NOT EXISTS analysis_jobs_user_status_idx
  ON public.analysis_jobs (user_id, status);

CREATE INDEX IF NOT EXISTS analysis_jobs_created_at_idx
  ON public.analysis_jobs (created_at DESC);

-- Row-level security: users can SELECT their own jobs only.
-- Backend service role bypasses RLS for INSERT/UPDATE.
ALTER TABLE public.analysis_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analysis jobs"
  ON public.analysis_jobs
  FOR SELECT
  USING (auth.uid() = user_id);

-- Keep updated_at current on every UPDATE.
CREATE OR REPLACE FUNCTION public.set_analysis_jobs_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER analysis_jobs_updated_at
  BEFORE UPDATE ON public.analysis_jobs
  FOR EACH ROW EXECUTE FUNCTION public.set_analysis_jobs_updated_at();

-- Notify PostgREST to reload its schema cache immediately.
NOTIFY pgrst, 'reload schema';
