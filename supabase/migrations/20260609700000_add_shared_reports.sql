-- Migration: add shared_reports table for shareable coach report links
-- Each row represents a share link for one speech.
-- The token is served through the backend; RLS here is defense-in-depth.

CREATE TABLE public.shared_reports (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  speech_id               uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  user_id                 uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  share_token             text        NOT NULL UNIQUE,
  title                   text,
  include_transcript      boolean     NOT NULL DEFAULT true,
  include_flow            boolean     NOT NULL DEFAULT true,
  include_feedback        boolean     NOT NULL DEFAULT true,
  include_drills          boolean     NOT NULL DEFAULT true,
  include_delivery        boolean     NOT NULL DEFAULT true,
  include_evidence_summary boolean    NOT NULL DEFAULT false,
  include_improvement     boolean     NOT NULL DEFAULT true,
  expires_at              timestamptz,
  revoked_at              timestamptz,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.shared_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "shared_reports_owner_select"
  ON public.shared_reports FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "shared_reports_owner_insert"
  ON public.shared_reports FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "shared_reports_owner_update"
  ON public.shared_reports FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "shared_reports_owner_delete"
  ON public.shared_reports FOR DELETE
  USING (auth.uid() = user_id);

CREATE INDEX idx_shared_reports_speech_id ON public.shared_reports (speech_id);
CREATE INDEX idx_shared_reports_user_id   ON public.shared_reports (user_id);
CREATE INDEX idx_shared_reports_token     ON public.shared_reports (share_token);

NOTIFY pgrst, 'reload schema';
