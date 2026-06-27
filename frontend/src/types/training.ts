export type MasteryState = 'not_started' | 'introduced' | 'developing' | 'proficient' | 'mastered' | 'needs_refresh';
export type SkillCategory = 'core_communication' | 'pf_argumentation' | 'speech_role';
export type PlanType = '1_week' | '4_week' | 'tournament_countdown' | 'custom';
export type ExperienceLevel = 'first_time' | 'novice' | 'jv' | 'varsity';

export interface Skill {
  id: string;
  name: string;
  description: string;
  novice_explanation: string;
  prerequisites: string[];
  speech_roles: string[];
  success_criteria: string[];
  category: SkillCategory;
  legacy_aliases: string[];
  mastery_thresholds: {
    introducing: number;
    developing: number;
    proficient: number;
    mastery: number;
  };
}

export interface MasteryScore {
  user_id: string;
  skill_id: string;
  mastery_score: number;
  confidence: number;
  evidence_count: number;
  mastery_state: MasteryState;
  last_demonstrated_at: string | null;
  coach_override_score: number | null;
  coach_override_note: string | null;
  recurring_weakness: number;
  explanation?: string;
}

export interface MasteryProfile {
  user_id: string;
  skills: Record<string, MasteryScore>;
  computed_at: string;
  event_pack: string;
}

export interface WeekPlan {
  week: number;
  skill_focus: string;
  skill_name: string;
  objective: string;
  lesson_id: string | null;
  drill_description: string;
  speech_application: string;
  completion_criteria: string[];
  mastery_target: number;
  estimated_hours: number;
}

export interface TrainingPlan {
  id: string;
  user_id: string;
  plan_type: PlanType;
  event_pack: string;
  current_week: number;
  total_weeks: number;
  weeks: WeekPlan[];
  status: 'active' | 'paused' | 'completed' | 'abandoned';
  created_at: string;
  summary?: string;
}

export interface CurriculumLesson {
  id: string;
  title: string;
  skill_id: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  prerequisite_lesson_ids: string[];
  estimated_minutes: number;
  what_is_it: string;
  why_judges_care: string;
  weak_example: string;
  strong_example: string;
  what_changed: string;
  recognition_check: string;
  micro_drill: string;
  speech_application: string;
  success_checklist: string[];
  recommended_next: string;
  version: string;
  common_mistakes?: string[];
  coach_note?: string;
  author?: string;
  reviewed_date?: string;
}

export interface CurriculumProgress {
  lesson_id: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  score: number | null;
  completed_at: string | null;
  coach_note: string | null;
}

export interface DiagnosticData {
  id: string;
  status: 'pending' | 'in_progress' | 'completed';
  experience_level: ExperienceLevel;
  strengths: string[];
  priorities: string[];
  recommended_track: string;
  confidence_note: string;
  completed_at: string | null;
}

export interface PracticeAgendaItem {
  activity_type: 'review' | 'drill' | 'partner_exercise' | 'rerecord' | 'reflection';
  skill_id: string;
  description: string;
  duration_minutes: number;
  team_data_reason: string;
}

// Constants
export const MASTERY_STATE_LABEL: Record<MasteryState, string> = {
  not_started: 'Not Started',
  introduced: 'Introduced',
  developing: 'Developing',
  proficient: 'Proficient',
  mastered: 'Mastered',
  needs_refresh: 'Needs Refresh',
};

export const MASTERY_STATE_COLOR: Record<MasteryState, string> = {
  not_started: 'text-ink-subtle',
  introduced: 'text-blue-500',
  developing: 'text-warn',
  proficient: 'text-ok',
  mastered: 'text-lav',
  needs_refresh: 'text-orange-400',
};

export const MASTERY_STATE_BG: Record<MasteryState, string> = {
  not_started: 'bg-surface-2',
  introduced: 'bg-blue-50',
  developing: 'bg-warn/10',
  proficient: 'bg-ok/10',
  mastered: 'bg-lav/10',
  needs_refresh: 'bg-orange-50',
};

export const EXPERIENCE_LABEL: Record<ExperienceLevel, string> = {
  first_time: 'First-time debater',
  novice: 'Novice',
  jv: 'Junior Varsity',
  varsity: 'Varsity',
};
