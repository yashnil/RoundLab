// Pass 15 — Judge Adaptation TypeScript Types

export type JudgeType = "lay" | "parent" | "flow" | "technical" | "coach" | "custom";

export type AdaptationTarget =
  | "evidence"
  | "argument"
  | "frontline"
  | "section"
  | "summary"
  | "final_focus"
  | "transcript";

export type AdaptationRiskLevel = "critical" | "high" | "medium" | "low";

export type AdaptationRiskCategory =
  | "causal_overstatement"
  | "qualifier_removal"
  | "missing_extension"
  | "new_argument_late_speech"
  | "jargon_overflow"
  | "under_explanation"
  | "shallow_response_overload"
  | "evidence_without_analysis"
  | "narrative_over_flow"
  | "unsafe_card_used"
  | "stale_card_used"
  | "dropped_argument_uncovered"
  | "warrant_collapsed"
  | "source_qualification_inflated";

export type WorkoutJudgeType =
  | "lay_explanation"
  | "parent_context"
  | "flow_extension"
  | "technical_concession"
  | "judge_switch"
  | "evidence_adaptation"
  | "final_focus_voter";

export interface JudgePreferences {
  jargon_tolerance: number;
  speed_tolerance: number;
  evidence_detail_preference: number;
  line_by_line_expectation: number;
  extension_strictness: number;
  weighing_expectation: number;
  narrative_preference: number;
  real_world_explanation: number;
  technical_rule_sensitivity: number;
  intervention_tolerance: number;
  organization_preference: number;
  source_qualification_importance: number;
  persuasion_vs_flow_emphasis: number;
}

export interface JudgeProfile {
  id?: string;
  judge_type: JudgeType;
  name: string;
  description: string;
  preferences: JudgePreferences;
  is_builtin: boolean;
  user_id?: string;
  team_id?: string;
}

export interface AdaptationChange {
  dimension: string;
  original?: string;
  adapted: string;
  reason: string;
  may_be_omitted: boolean;
}

export interface AdaptationRisk {
  category: AdaptationRiskCategory;
  level: AdaptationRiskLevel;
  description: string;
  source_ref?: string;
  how_to_mitigate: string;
}

export interface EvidencePresentationGuide {
  card_id: string;
  card_tag?: string;
  judge_type: JudgeType;
  who_is_source?: string;
  what_source_found?: string;
  why_it_matters?: string;
  one_sentence_causal?: string;
  short_citation?: string;
  flow_warrant?: string;
  flow_impact?: string;
  role_on_flow?: string;
  support_limit?: string;
  relevant_qualifier?: string;
  concession_interaction?: string;
  card_role?: "offense" | "defense" | "indict";
  best_practice_note?: string;
  methodological_limitation?: string;
  estimated_read_time_seconds?: number;
  can_be_paraphrased: boolean;
  risks: AdaptationRisk[];
}

export interface FrontlineAdaptation {
  frontline_id: string;
  judge_type: JudgeType;
  recommended_response_order: string[];
  lead_response_reason?: string;
  responses_to_condense: string[];
  responses_to_expand: string[];
  responses_needing_evidence: string[];
  analytic_responses_sufficient: boolean;
  read_evidence: boolean;
  offensive_carry_recommendation?: string;
  must_extend_in_summary: string[];
  must_extend_in_final_focus: string[];
  estimated_rebuttal_seconds: number;
  changes: AdaptationChange[];
  risks: AdaptationRisk[];
}

export interface SpeechStageAdaptation {
  stage: "rebuttal" | "summary" | "final_focus";
  judge_type: JudgeType;
  response_ordering: string[];
  time_allocation_notes?: string;
  evidence_vs_analytics_balance?: string;
  collapse_recommendation?: string;
  required_extensions: string[];
  voter_framing?: string;
  comparative_explanation?: string;
  technical_detail_level?: string;
  suggested_phrasing: string[];
  changes: AdaptationChange[];
  risks: AdaptationRisk[];
  estimated_seconds: number;
}

export interface JudgeAdaptationResult {
  id?: string;
  user_id: string;
  judge_type: JudgeType;
  source_type: AdaptationTarget;
  source_id: string;
  original_purpose: string;
  judge_goal: string;
  changes: AdaptationChange[];
  risks: AdaptationRisk[];
  critical_risks: AdaptationRisk[];
  evidence_guide?: EvidencePresentationGuide;
  frontline_adaptation?: FrontlineAdaptation;
  speech_plan?: SpeechStageAdaptation;
  what_to_emphasize: string[];
  what_to_simplify: string[];
  what_must_remain_explicit: string[];
  what_can_be_shortened: string[];
  suggested_phrasing: string[];
  preserved_source_refs: string[];
  estimated_seconds: number;
  rules_version: string;
  generated_at: string;
}

export interface JudgeComparisonDiff {
  dimension: string;
  judge_a_value: string;
  judge_b_value: string;
  why_different: string;
}

export interface JudgeComparisonResult {
  source_type: AdaptationTarget;
  source_id: string;
  judge_types: JudgeType[];
  constants: string[];
  differences: JudgeComparisonDiff[];
  strategic_risks_by_judge: Record<string, AdaptationRisk[]>;
  wording_differences: JudgeComparisonDiff[];
  time_allocation_differences: JudgeComparisonDiff[];
  generated_at: string;
}

export interface JudgeWorkoutCreate {
  user_id: string;
  workout_type: WorkoutJudgeType;
  judge_type: JudgeType;
  title: string;
  description?: string;
  prompt: string;
  instructions?: string;
  success_criteria: string[];
  time_limit_seconds: number;
  source_card_id?: string;
  source_card_tag?: string;
  source_card_body_snapshot?: string;
  source_argument_id?: string;
  source_frontline_id?: string;
  comparison_judge_type?: JudgeType;
  workspace_id?: string;
}

export interface JudgeWorkoutRow extends JudgeWorkoutCreate {
  id: string;
  status: "not_started" | "in_progress" | "completed";
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface JudgeReadinessDimensionScore {
  dimension: string;
  score: number | null;
  explanation: string;
  contributing_risks: string[];
}

export interface JudgeReadinessReport {
  user_id: string;
  judge_type: JudgeType;
  source_type: AdaptationTarget;
  source_id: string;
  clarity: JudgeReadinessDimensionScore;
  organization: JudgeReadinessDimensionScore;
  extension_completeness: JudgeReadinessDimensionScore;
  evidence_explanation: JudgeReadinessDimensionScore;
  weighing_fit: JudgeReadinessDimensionScore;
  jargon_fit: JudgeReadinessDimensionScore;
  strategic_focus: JudgeReadinessDimensionScore;
  speech_stage_legality: JudgeReadinessDimensionScore;
  composite_score: number | null;
  risks: AdaptationRisk[];
  generated_at: string;
}

export const JUDGE_TYPE_LABELS: Record<JudgeType, string> = {
  lay: "Lay Judge",
  parent: "Parent Judge",
  flow: "Flow Judge",
  technical: "Technical Judge",
  coach: "Coach Judge",
  custom: "Custom Profile",
};

export const JUDGE_TYPE_DESCRIPTIONS: Record<JudgeType, string> = {
  lay: "Community member with no debate experience. Responds to stories, real-world impact, and plain language.",
  parent: "Familiar with debate from watching, but not a debater. Needs context, definitions, and fairness framing.",
  flow: "Experienced debater who flows every word. Requires complete labels, explicit extensions, and precise weighing.",
  technical: "Expert judge who tracks concessions, burdens, and offense/defense separation precisely.",
  coach: "Evaluates strategic soundness and complete argument structure. Rewards best-practice habits.",
  custom: "Custom judge profile with personalized preference settings.",
};

export const RISK_LEVEL_COLORS: Record<AdaptationRiskLevel, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  high: "text-orange-600 bg-orange-50 border-orange-200",
  medium: "text-yellow-600 bg-yellow-50 border-yellow-200",
  low: "text-blue-600 bg-blue-50 border-blue-200",
};
