// Pass 16 — Full-Round PF Simulation types

export type RoundSide = "pro" | "con";
export type SpeakingOrder = "first" | "second";
export type SpeakerRole = "first" | "second";
export type OpponentDifficulty = "novice" | "jv" | "varsity";
export type RoundFormat = "full" | "shortened" | "speech_stage_drill" | "evidence_testing" | "judge_adaptation";
export type RoundStatus = "setup" | "active" | "paused" | "completed" | "abandoned";

export type RoundPhaseType =
  | "first_constructive"
  | "second_constructive"
  | "first_crossfire"
  | "first_rebuttal"
  | "second_rebuttal"
  | "grand_crossfire"
  | "first_summary"
  | "second_summary"
  | "final_crossfire"
  | "first_final_focus"
  | "second_final_focus"
  | "judge_deliberation"
  | "completed";

export type ArgumentFlowStatus =
  | "introduced"
  | "answered"
  | "conceded"
  | "extended"
  | "underextended"
  | "dropped"
  | "turned"
  | "mitigated"
  | "outweighed"
  | "new_in_late_speech"
  | "unresolved"
  | "live";

export type CrossfireExchangeType =
  | "question"
  | "answer"
  | "concession"
  | "contradiction"
  | "evasion"
  | "evidence_challenge";

export interface RoundSimulationConfig {
  format: RoundFormat;
  student_side: RoundSide;
  speaking_order: SpeakingOrder;
  speaker_role: SpeakerRole;
  judge_type: string;
  judge_profile_id?: string;
  opponent_difficulty: OpponentDifficulty;
  resolution: string;
  resolution_id?: string;
  prep_workspace_id?: string;
  coaching_hints_enabled: boolean;
  pauses_allowed: boolean;
  practice_mode_overrides: string[];
  constructive_time: number;
  rebuttal_time: number;
  summary_time: number;
  final_focus_time: number;
  crossfire_time: number;
  prep_time: number;
  approved_card_ids: string[];
  approved_blockfile_ids: string[];
  approved_frontline_ids: string[];
  source_scope: string;
  evidence_testing_mode: boolean;
}

export interface RoundSimulation {
  id: string;
  user_id: string;
  team_id?: string;
  config: RoundSimulationConfig;
  status: RoundStatus;
  current_phase: RoundPhaseType;
  phase_history: string[];
  started_at?: string;
  completed_at?: string;
  is_practice_mode: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoundSpeech {
  id: string;
  round_id: string;
  phase: RoundPhaseType;
  speaker_side: RoundSide;
  is_ai: boolean;
  transcript?: string;
  audio_url?: string;
  argument_labels: string[];
  responses_made: string[];
  arguments_extended: string[];
  arguments_dropped: string[];
  evidence_card_ids: string[];
  weighing_used?: string;
  strategic_goal?: string;
  estimated_speaking_time?: number;
  legality_violations: Array<{ type: string; description: string; severity: string }>;
  word_count?: number;
  is_immutable: boolean;
  created_at: string;
}

export interface RoundArgument {
  id: string;
  round_id: string;
  label: string;
  side: RoundSide;
  claim: string;
  warrant?: string;
  evidence_card_id?: string;
  impact?: string;
  initial_phase: RoundPhaseType;
  status: ArgumentFlowStatus;
  responses: string[];
  extensions: string[];
  concessions: string[];
  weighing?: string;
  is_offense: boolean;
  is_turn: boolean;
  is_framework: boolean;
  parent_argument_id?: string;
  last_updated_phase?: string;
}

export interface CrossfireExchange {
  id: string;
  round_id: string;
  phase: RoundPhaseType;
  sequence: number;
  questioner_side: RoundSide;
  question: string;
  answer?: string;
  target_argument?: string;
  exchange_type: CrossfireExchangeType;
  concession_extracted?: string;
  contradiction?: string;
  evasion_detected: boolean;
  evidence_challenge?: string;
  strategic_significance: string;
  created_at: string;
}

export interface RoundEvidenceUse {
  id: string;
  round_id: string;
  speech_id: string;
  card_id: string;
  speaker_side: RoundSide;
  phase: RoundPhaseType;
  citation_given: boolean;
  tag_matched_source: boolean;
  warrant_explained: boolean;
  extended_later: boolean;
  challenged_by_opponent: boolean;
  challenge_answered: boolean;
  relevant_to_final_decision: boolean;
  violations: string[];
  support_verdict?: string;
  source_classification?: string;
  flagged: boolean;
  created_at: string;
}

export interface DecisionTraceEntry {
  argument_id: string;
  argument_label: string;
  side: RoundSide;
  included: boolean;
  reason?: string;
}

export interface RoundDecisionTrace {
  arguments_considered: DecisionTraceEntry[];
  surviving_voters: string[];
  weighing_comparison: string;
  judge_profile_effects: string[];
  framework_resolution?: string;
  final_winner?: RoundSide;
  confidence: string;
}

export interface RoundDecision {
  id: string;
  round_id: string;
  judge_type: string;
  engine_version: string;
  winner: RoundSide;
  reason_for_decision: string;
  voting_issues: string[];
  speaker_points: Record<string, number>;
  decisive_concessions: string[];
  dropped_arguments: string[];
  evidence_issues: string[];
  weighing_comparison: string;
  legality_issues: string[];
  adaptation_successes: string[];
  adaptation_failures: string[];
  decision_trace: RoundDecisionTrace;
  created_at: string;
}

export interface RoundDrillSource {
  round_id: string;
  speech_phase: string;
  argument_label?: string;
  card_id?: string;
  weakness_description: string;
}

export interface RoundDrill {
  id: string;
  round_id: string;
  drill_id: string;
  source: RoundDrillSource;
  skill_target: string;
  title: string;
  prompt: string;
  success_criteria: string[];
  time_limit_seconds: number;
  created_at: string;
}

export interface RoundAdaptationReview {
  id: string;
  round_id: string;
  judge_type: string;
  adaptation_successes: string[];
  adaptation_failures: string[];
  how_other_judge_sees?: string;
  alternate_judge_type?: string;
  created_at: string;
}

export interface StudentCrossfireQA {
  id: string;
  question: string;
  answer: string;
  created_at: string;
}

export interface RoundStateResponse {
  simulation: RoundSimulation;
  current_phase: RoundPhaseType;
  phase_label: string;
  student_speaks_now: boolean;
  time_limit_seconds: number;
  phase_started_at?: string;
  speeches: RoundSpeech[];
  flow_arguments: RoundArgument[];
  active_crossfire?: CrossfireExchange[];
  decision?: RoundDecision;
  coaching_hint?: string;
}

export interface RoundHistoryItem {
  id: string;
  resolution: string;
  student_side: string;
  judge_type: string;
  status: string;
  winner?: string;
  created_at: string;
  completed_at?: string;
}

export interface PrepWarning {
  type: string;
  severity: "info" | "warning" | "error";
  message: string;
  card_id?: string;
}
