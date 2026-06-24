-- Pass 15: Judge Adaptation Simulator
-- Tables: judge_profiles, judge_adaptations, judge_adaptation_notes, judge_workout_assignments

-- ── Helper: updated_at trigger ──────────────────────────────────────────────
CREATE OR REPLACE FUNCTION p15_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── 1. judge_profiles (custom profiles; built-ins are code constants) ────────
CREATE TABLE IF NOT EXISTS judge_profiles (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  team_id         uuid REFERENCES teams(id) ON DELETE SET NULL,
  name            text NOT NULL,
  base_type       text NOT NULL CHECK (base_type IN ('lay','parent','flow','technical','coach','custom')),
  description     text,
  -- 13 preference dimensions, 1-5 scale (null = use base_type default)
  jargon_tolerance           smallint CHECK (jargon_tolerance BETWEEN 1 AND 5),
  speed_tolerance            smallint CHECK (speed_tolerance BETWEEN 1 AND 5),
  evidence_detail_preference smallint CHECK (evidence_detail_preference BETWEEN 1 AND 5),
  line_by_line_expectation   smallint CHECK (line_by_line_expectation BETWEEN 1 AND 5),
  extension_strictness       smallint CHECK (extension_strictness BETWEEN 1 AND 5),
  weighing_expectation       smallint CHECK (weighing_expectation BETWEEN 1 AND 5),
  narrative_preference       smallint CHECK (narrative_preference BETWEEN 1 AND 5),
  real_world_explanation     smallint CHECK (real_world_explanation BETWEEN 1 AND 5),
  technical_rule_sensitivity smallint CHECK (technical_rule_sensitivity BETWEEN 1 AND 5),
  intervention_tolerance     smallint CHECK (intervention_tolerance BETWEEN 1 AND 5),
  organization_preference    smallint CHECK (organization_preference BETWEEN 1 AND 5),
  source_qualification_importance smallint CHECK (source_qualification_importance BETWEEN 1 AND 5),
  persuasion_vs_flow_emphasis smallint CHECK (persuasion_vs_flow_emphasis BETWEEN 1 AND 5),
  is_public       boolean NOT NULL DEFAULT false,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER p15_judge_profiles_updated_at
  BEFORE UPDATE ON judge_profiles
  FOR EACH ROW EXECUTE FUNCTION p15_set_updated_at();

ALTER TABLE judge_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY judge_profiles_owner ON judge_profiles
  FOR ALL USING (user_id = auth.uid());
CREATE POLICY judge_profiles_public_read ON judge_profiles
  FOR SELECT USING (is_public = true);

-- ── 2. judge_adaptations (persisted adaptation results) ──────────────────────
CREATE TABLE IF NOT EXISTS judge_adaptations (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  judge_type          text NOT NULL CHECK (judge_type IN ('lay','parent','flow','technical','coach','custom')),
  custom_profile_id   uuid REFERENCES judge_profiles(id) ON DELETE SET NULL,
  -- Source material (at least one required)
  source_type         text NOT NULL CHECK (source_type IN (
                        'evidence','argument','frontline','section','summary','final_focus','transcript')),
  source_card_id      uuid,
  source_argument_id  uuid,
  source_frontline_id uuid,
  source_section_id   uuid,
  -- Adaptation result stored as JSON
  result_json         jsonb NOT NULL,
  -- Summary columns for querying
  risk_count          integer NOT NULL DEFAULT 0,
  change_count        integer NOT NULL DEFAULT 0,
  rules_version       text NOT NULL DEFAULT 'p15_v1',
  -- Link to prep workspace if relevant
  workspace_id        uuid,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_judge_adaptations_user ON judge_adaptations(user_id);
CREATE INDEX idx_judge_adaptations_source_card ON judge_adaptations(source_card_id) WHERE source_card_id IS NOT NULL;

CREATE TRIGGER p15_judge_adaptations_updated_at
  BEFORE UPDATE ON judge_adaptations
  FOR EACH ROW EXECUTE FUNCTION p15_set_updated_at();

ALTER TABLE judge_adaptations ENABLE ROW LEVEL SECURITY;
CREATE POLICY judge_adaptations_owner ON judge_adaptations
  FOR ALL USING (user_id = auth.uid());

-- ── 3. judge_adaptation_notes (saved notes per adaptation) ───────────────────
CREATE TABLE IF NOT EXISTS judge_adaptation_notes (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  adaptation_id   uuid NOT NULL REFERENCES judge_adaptations(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  note_text       text NOT NULL,
  judge_type      text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE judge_adaptation_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY judge_adaptation_notes_owner ON judge_adaptation_notes
  FOR ALL USING (user_id = auth.uid());

-- ── 4. judge_workout_assignments (coach assignments) ─────────────────────────
CREATE TABLE IF NOT EXISTS judge_workout_assignments (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assigned_by     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  assigned_to     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  team_id         uuid REFERENCES teams(id) ON DELETE SET NULL,
  -- Workout definition (stored inline rather than linking to prep_workouts)
  workout_type    text NOT NULL,
  judge_type      text NOT NULL CHECK (judge_type IN ('lay','parent','flow','technical','coach','custom')),
  title           text NOT NULL,
  prompt          text NOT NULL,
  instructions    text,
  success_criteria jsonb NOT NULL DEFAULT '[]',
  time_limit_seconds integer NOT NULL DEFAULT 90,
  -- Source material reference (snapshot if needed for auditability)
  source_card_id  uuid,
  source_card_tag text,
  -- Bounded snapshot of card body (max 500 chars)
  source_card_body_snapshot text,
  -- Status
  status          text NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned','in_progress','completed','skipped')),
  completed_at    timestamptz,
  student_notes   text,
  coach_feedback  text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_judge_workout_assignments_to ON judge_workout_assignments(assigned_to);
CREATE INDEX idx_judge_workout_assignments_by ON judge_workout_assignments(assigned_by);

CREATE TRIGGER p15_judge_workout_assignments_updated_at
  BEFORE UPDATE ON judge_workout_assignments
  FOR EACH ROW EXECUTE FUNCTION p15_set_updated_at();

ALTER TABLE judge_workout_assignments ENABLE ROW LEVEL SECURITY;
CREATE POLICY judge_workout_assignments_assignee ON judge_workout_assignments
  FOR SELECT USING (assigned_to = auth.uid() OR assigned_by = auth.uid());
CREATE POLICY judge_workout_assignments_coach ON judge_workout_assignments
  FOR ALL USING (assigned_by = auth.uid());
