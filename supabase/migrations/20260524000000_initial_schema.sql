-- =============================================================================
-- RoundLab — Initial Schema
-- Migration: 20260524000000_initial_schema.sql
--
-- Apply via: Supabase Dashboard → SQL Editor → paste and run.
-- Or via CLI: supabase db push (once project is linked).
-- =============================================================================


-- =============================================================================
-- 1. ENUM TYPES
-- =============================================================================

CREATE TYPE public.speech_type AS ENUM (
  'constructive',
  'rebuttal',
  'summary',
  'final_focus',
  'crossfire'
);

CREATE TYPE public.speech_side AS ENUM (
  'pro',
  'con'
);

CREATE TYPE public.speech_status AS ENUM (
  'pending',
  'transcribing',
  'analyzing',
  'done',
  'error'
);

-- Judge type affects the feedback tone and vocabulary the AI uses.
CREATE TYPE public.judge_type AS ENUM (
  'lay',
  'flow',
  'tech',
  'coach'
);


-- =============================================================================
-- 2. UTILITY: updated_at trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


-- =============================================================================
-- 3. PROFILES
-- Auto-created when a user signs up via auth.users trigger.
-- =============================================================================

CREATE TABLE public.profiles (
  id           uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Auto-insert a profile row whenever a new auth user is created.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id)
  VALUES (NEW.id);
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- =============================================================================
-- 4. SPEECHES
-- Core entity. One row per recorded or uploaded speech.
-- =============================================================================

CREATE TABLE public.speeches (
  id               uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid              NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title            text              NOT NULL,
  speech_type      public.speech_type NOT NULL,
  side             public.speech_side,
  judge_type       public.judge_type,
  topic            text,             -- The PF resolution being debated (e.g. "Resolved: ...")
  audio_url        text,             -- Supabase Storage path, set after upload
  duration_seconds integer,
  status           public.speech_status NOT NULL DEFAULT 'pending',
  created_at       timestamptz       NOT NULL DEFAULT now(),
  updated_at       timestamptz       NOT NULL DEFAULT now()
);

CREATE TRIGGER set_speeches_updated_at
  BEFORE UPDATE ON public.speeches
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 5. TRANSCRIPTS
-- One row per speech, written once by the pipeline. Never edited.
-- =============================================================================

CREATE TABLE public.transcripts (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  speech_id  uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  text       text        NOT NULL,
  word_count integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (speech_id)
);


-- =============================================================================
-- 6. ARGUMENT MAPS
-- Extracted claim/warrant/evidence/impact structure for a speech.
--
-- arguments JSONB shape:
-- [
--   {
--     "claim":         "string",
--     "warrant":       "string",
--     "evidence":      "string | null",
--     "impact":        "string",
--     "argument_type": "offense | defense",
--     "dropped":       false
--   }
-- ]
-- =============================================================================

CREATE TABLE public.argument_maps (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  speech_id  uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  arguments  jsonb       NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (speech_id)
);


-- =============================================================================
-- 7. FEEDBACK REPORTS
-- Ballot-style feedback for a speech.
--
-- scores JSONB shape:
-- {
--   "clash":            0-20,
--   "weighing":         0-20,
--   "extensions":       0-20,
--   "drops":            0-20,
--   "judge_adaptation": 0-20
-- }
--
-- raw_feedback: full LLM response, nullable, stored for debugging.
-- =============================================================================

CREATE TABLE public.feedback_reports (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  speech_id     uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  overall_score integer     CHECK (overall_score BETWEEN 1 AND 100),
  scores        jsonb       NOT NULL DEFAULT '{}',
  summary       text,
  strengths     text[]      NOT NULL DEFAULT '{}',
  weaknesses    text[]      NOT NULL DEFAULT '{}',
  raw_feedback  jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (speech_id)
);


-- =============================================================================
-- 8. DRILLS
-- Three personalized drills generated per speech, tied to top weaknesses.
-- "order" is 1, 2, or 3. Enforced at the application layer.
-- =============================================================================

CREATE TABLE public.drills (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  speech_id    uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  user_id      uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title        text        NOT NULL,
  description  text,
  skill_target text        NOT NULL, -- e.g. "weighing", "extensions", "drops"
  prompt       text        NOT NULL,
  "order"      integer     NOT NULL CHECK ("order" BETWEEN 1 AND 3),
  created_at   timestamptz NOT NULL DEFAULT now()
);


-- =============================================================================
-- 9. DRILL ATTEMPTS
-- Tracks each time a user submits a response to a drill.
--
-- feedback JSONB shape (Sprint 3+, schema TBD):
-- { "score": int, "commentary": "string", "suggestions": ["string"] }
-- =============================================================================

CREATE TABLE public.drill_attempts (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  drill_id   uuid        NOT NULL REFERENCES public.drills(id) ON DELETE CASCADE,
  user_id    uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  response   text,
  audio_url  text,
  feedback   jsonb,
  score      integer     CHECK (score BETWEEN 1 AND 100),
  created_at timestamptz NOT NULL DEFAULT now()
);


-- =============================================================================
-- 10. ROW-LEVEL SECURITY
-- All tables locked down. Backend uses the service role key (bypasses RLS).
-- Frontend uses the anon/user JWT and hits only these policies.
-- =============================================================================

ALTER TABLE public.profiles       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.speeches       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcripts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.argument_maps  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drills         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drill_attempts ENABLE ROW LEVEL SECURITY;

-- profiles: own row only
CREATE POLICY "profiles: select own"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "profiles: update own"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

-- speeches: full CRUD on own rows
CREATE POLICY "speeches: select own"
  ON public.speeches FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "speeches: insert own"
  ON public.speeches FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "speeches: update own"
  ON public.speeches FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "speeches: delete own"
  ON public.speeches FOR DELETE
  USING (auth.uid() = user_id);

-- transcripts: read-only for users; pipeline writes via service role
CREATE POLICY "transcripts: select own"
  ON public.transcripts FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.speeches
      WHERE speeches.id = transcripts.speech_id
        AND speeches.user_id = auth.uid()
    )
  );

-- argument_maps: read-only for users
CREATE POLICY "argument_maps: select own"
  ON public.argument_maps FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.speeches
      WHERE speeches.id = argument_maps.speech_id
        AND speeches.user_id = auth.uid()
    )
  );

-- feedback_reports: read-only for users
CREATE POLICY "feedback_reports: select own"
  ON public.feedback_reports FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.speeches
      WHERE speeches.id = feedback_reports.speech_id
        AND speeches.user_id = auth.uid()
    )
  );

-- drills: read-only for users (pipeline creates via service role)
CREATE POLICY "drills: select own"
  ON public.drills FOR SELECT
  USING (auth.uid() = user_id);

-- drill_attempts: users can read and submit their own attempts
CREATE POLICY "drill_attempts: select own"
  ON public.drill_attempts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "drill_attempts: insert own"
  ON public.drill_attempts FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- =============================================================================
-- 11. INDEXES
-- =============================================================================

-- Dashboard: list user's speeches newest-first
CREATE INDEX idx_speeches_user_created
  ON public.speeches (user_id, created_at DESC);

-- Load drills for a given speech
CREATE INDEX idx_drills_speech_id
  ON public.drills (speech_id);

-- User's full drill library
CREATE INDEX idx_drills_user_id
  ON public.drills (user_id);

-- Attempts per drill (for progress view)
CREATE INDEX idx_drill_attempts_drill_id
  ON public.drill_attempts (drill_id);

-- All attempts by a user (for progress dashboard)
CREATE INDEX idx_drill_attempts_user_id
  ON public.drill_attempts (user_id);
