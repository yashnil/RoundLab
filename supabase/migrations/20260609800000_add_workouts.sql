-- Migration: add workouts table for Tournament Prep Workout Mode
-- Workouts are generated from an existing speech report and stored as structured JSON.
-- workout_json holds a WorkoutPlan with steps, re_record_goal, and coach_note.

CREATE TABLE public.workouts (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  speech_id         uuid        NOT NULL REFERENCES public.speeches(id) ON DELETE CASCADE,
  title             text        NOT NULL,
  description       text,
  estimated_minutes integer,
  workout_type      text        NOT NULL DEFAULT 'tournament_prep',
  status            text        NOT NULL DEFAULT 'not_started',
  focus_area        text,
  workout_json      jsonb       NOT NULL,
  completed_at      timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT workouts_status_check CHECK (
    status IN ('not_started', 'in_progress', 'completed')
  )
);

ALTER TABLE public.workouts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "workouts_owner_select"
  ON public.workouts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "workouts_owner_update"
  ON public.workouts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "workouts_owner_delete"
  ON public.workouts FOR DELETE
  USING (auth.uid() = user_id);

-- Service role handles inserts via backend (bypasses RLS)

CREATE INDEX idx_workouts_speech_id   ON public.workouts (speech_id);
CREATE INDEX idx_workouts_user_id     ON public.workouts (user_id);
CREATE INDEX idx_workouts_user_status ON public.workouts (user_id, status);

NOTIFY pgrst, 'reload schema';
