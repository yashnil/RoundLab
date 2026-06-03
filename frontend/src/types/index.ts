export interface HealthResponse {
  status: string;
  service: string;
}

export type SpeechType =
  | "constructive"
  | "rebuttal"
  | "summary"
  | "final_focus"
  | "crossfire";

export type SpeechSide = "pro" | "con";
export type JudgeType = "lay" | "flow" | "tech" | "coach";
export type SpeechStatus =
  | "pending"
  | "transcribing"
  | "analyzing"
  | "done"
  | "error";

export type ArgumentType =
  | "offense"
  | "defense"
  | "weighing"
  | "response"
  | "unclear";

export interface ArgumentItem {
  label: string;
  claim: string;
  warrant: string;
  evidence: string | null;
  impact: string;
  argument_type: ArgumentType;
  issues: string[];
  confidence: number | null;
}

export interface ArgumentMap {
  id: string;
  speech_id: string;
  arguments: ArgumentItem[];
  created_at: string;
}

export interface Transcript {
  id: string;
  speech_id: string;
  text: string;
  word_count: number | null;
  created_at: string;
}

export interface FeedbackScores {
  clash: number;
  weighing: number;
  extensions: number;
  drops: number;
  judge_adaptation: number;
}

export interface FeedbackReport {
  id: string;
  speech_id: string;
  overall_score: number | null;
  scores: FeedbackScores;
  summary: string | null;
  strengths: string[];
  weaknesses: string[];
  raw_feedback: {
    decision_logic?: string;
    dropped_or_undercovered_arguments?: string[];
    warranting_diagnostics?: string[];
    weighing_diagnostics?: string[];
    evidence_diagnostics?: string[];
    judge_adaptation_notes?: string;
    top_3_priorities?: string[];
    recommendations?: string[];
  } | null;
  helpful_rating?: string | null;
  helpful_comment?: string | null;
  created_at: string;
}

export interface Speech {
  id: string;
  user_id: string;
  title: string;
  speech_type: SpeechType;
  side: SpeechSide | null;
  judge_type: JudgeType | null;
  topic: string | null;
  audio_url: string | null;
  duration_seconds: number | null;
  status: SpeechStatus;
  created_at: string;
  updated_at: string;
}

export type DrillStatus = "assigned" | "attempted" | "completed";
export type DrillDifficulty = "beginner" | "intermediate" | "advanced";

export interface Drill {
  id: string;
  speech_id: string;
  user_id: string;
  title: string;
  description: string | null;
  skill_target: string;
  prompt: string;
  order: number;
  /** Step-by-step guidance (newline-separated) */
  instructions: string | null;
  /** Checklist items for self-evaluation */
  success_criteria: string[];
  /** The specific feedback weakness this drill targets */
  source_weakness: string | null;
  difficulty: DrillDifficulty;
  status: DrillStatus;
  created_at: string;
}

export interface DrillAttempt {
  id: string;
  drill_id: string;
  user_id: string;
  response: string | null;
  audio_url: string | null;
  feedback: Record<string, unknown> | null;
  score: number | null;
  created_at: string;
}

export interface IncompleteDrill {
  id: string;
  speech_id: string;
  title: string;
  skill_target: string;
  difficulty: string;
  status: string;
  speech_title: string;
}

export interface SkillAverages {
  clash: number;
  weighing: number;
  extensions: number;
  drops: number;
  judge_adaptation: number;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  earned_at: string | null;
}

export interface ProgressSummary {
  speech_count: number;
  feedback_ready_count: number;
  drills_assigned_count: number;
  drill_attempts_count: number;
  drills_completed_count: number;
  drill_completion_rate: number | null;
  incomplete_drills: IncompleteDrill[];
  skill_averages: SkillAverages | null;
  // Gamification
  xp: number;
  level: number;
  xp_to_next_level: number;
  badges: Badge[];
}

export interface UserTeam {
  team_id: string;
  team_name: string;
  role: "coach" | "student";
  invite_code: string;
}

export interface StudentProgress {
  user_id: string;
  display_name: string | null;
  speech_count: number;
  feedback_ready_count: number;
  drills_assigned_count: number;
  drill_attempts_count: number;
  latest_practice_at: string | null;
}

export interface TeamDashboard {
  team_id: string;
  team_name: string;
  invite_code: string;
  member_count: number;
  students: StudentProgress[];
}
