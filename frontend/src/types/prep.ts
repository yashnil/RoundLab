// Pass 14 — Tournament Prep TypeScript interfaces

export type Side = "pro" | "con" | "both";

export type GapCategory =
  | "missing_argument"
  | "missing_claim_support"
  | "missing_warrant"
  | "missing_impact"
  | "missing_uniqueness"
  | "missing_link"
  | "missing_internal_link"
  | "missing_response"
  | "missing_counterevidence"
  | "missing_weighing"
  | "weak_source"
  | "unsupported_card"
  | "partial_support"
  | "abstract_only"
  | "stale_evidence"
  | "freshness_unknown"
  | "duplicate_evidence"
  | "insufficient_source_diversity"
  | "missing_summary_extension"
  | "missing_final_focus_extension"
  | "frontline_underdeveloped";

export type GapSeverity = "critical" | "high" | "medium" | "low" | "info";

export type FreshnessState =
  | "current"
  | "aging"
  | "stale"
  | "superseded"
  | "older_but_still_relevant"
  | "freshness_unknown"
  | "not_time_sensitive";

export type FrontlineReadiness =
  | "ready"
  | "usable_with_gaps"
  | "underdeveloped"
  | "unsafe";

export type CoverageState =
  | "covered"
  | "partially_covered"
  | "missing"
  | "not_applicable"
  | "warning";

export type TaskType =
  | "research_evidence"
  | "replace_stale_card"
  | "verify_citation"
  | "strengthen_warrant"
  | "add_impact_evidence"
  | "find_counterevidence"
  | "build_frontline"
  | "add_weighing"
  | "write_summary_extension"
  | "write_final_focus_extension"
  | "complete_a_drill"
  | "review_unsafe_card";

export type TaskStatus = "pending" | "in_progress" | "completed" | "skipped";

export type WorkoutType =
  | "evidence_explanation"
  | "card_comparison"
  | "frontline_speed"
  | "summary_extension"
  | "evidence_indictment"
  | "stale_evidence"
  | "lay_judge_evidence";

export interface PrepWorkspace {
  id: string;
  user_id: string;
  team_id?: string;
  resolution_id: string;
  side: Side;
  tournament_date?: string;
  judge_emphasis?: string;
  created_at: string;
  updated_at: string;
}

export interface EvidenceFreshnessAssessment {
  card_id: string;
  card_tag?: string;
  published_date?: string;
  freshness_state: FreshnessState;
  claim_type: string;
  rule_applied: string;
  explanation: string;
  days_old?: number;
  has_newer_corroboration: boolean;
  assessed_at: string;
}

export interface CoverageDimension {
  dimension: string;
  state: CoverageState;
  evidence: string[];
  notes?: string;
}

export interface BlockfileCoverageResult {
  argument_id?: string;
  section_id?: string;
  section_title?: string;
  argument_type?: string;
  dimensions: CoverageDimension[];
  covered_count: number;
  total_applicable_count: number;
  coverage_pct: number;
  gaps: string[];
}

export interface PrepGap {
  id?: string;
  gap_category: GapCategory;
  severity: GapSeverity;
  title: string;
  reason: string;
  is_deterministic: boolean;
  argument_id?: string;
  blockfile_id?: string;
  section_id?: string;
  card_id?: string;
  frontline_id?: string;
  recommended_action?: string;
  estimated_minutes?: number;
  resolved: boolean;
}

export interface DimensionScore {
  dimension: string;
  score?: number;
  weight: number;
  explanation: string;
  contributing_gaps: string[];
}

export interface ReadinessDimensions {
  argument_coverage: DimensionScore;
  evidence_quality: DimensionScore;
  evidence_freshness: DimensionScore;
  frontline_readiness: DimensionScore;
  source_diversity: DimensionScore;
  speech_stage_readiness: DimensionScore;
  weighing_preparation: DimensionScore;
}

export interface PrepReadinessReport {
  id?: string;
  workspace_id?: string;
  user_id: string;
  resolution_id: string;
  resolution_title?: string;
  side: Side;
  generated_at: string;
  library_watermark?: string;
  tournament_date?: string;
  dimensions: ReadinessDimensions;
  composite_score?: number;
  gaps: PrepGap[];
  critical_gaps: PrepGap[];
  stale_cards: EvidenceFreshnessAssessment[];
  unsafe_cards: string[];
  strongest_arguments: string[];
  weakest_frontlines: string[];
  blockfile_coverage: BlockfileCoverageResult[];
  freshness_assessments: EvidenceFreshnessAssessment[];
  next_recommended_actions: string[];
  total_cards: number;
  total_arguments: number;
  total_frontlines: number;
  total_blockfiles: number;
}

export interface PrepTask {
  id: string;
  workspace_id: string;
  user_id: string;
  assigned_by?: string;
  gap_id?: string;
  task_type: TaskType;
  title: string;
  reason?: string;
  argument_id?: string;
  blockfile_id?: string;
  card_id?: string;
  frontline_id?: string;
  priority: number;
  estimated_minutes?: number;
  due_date?: string;
  status: TaskStatus;
  completion_notes?: string;
  is_auto_generated: boolean;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PrepWorkout {
  id: string;
  workspace_id: string;
  user_id: string;
  gap_id?: string;
  task_id?: string;
  workout_type: WorkoutType;
  title: string;
  description?: string;
  prompt: string;
  instructions?: string;
  success_criteria: string[];
  time_limit_seconds: number;
  source_card_id?: string;
  source_card_tag?: string;
  source_card_body?: string;
  drill_id?: string;
  drill_attempt_id?: string;
  status: "not_started" | "in_progress" | "completed" | "skipped";
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PrepPlan {
  workspace_id: string;
  user_id: string;
  resolution_title?: string;
  tournament_date?: string;
  tasks: PrepTask[];
  workouts: PrepWorkout[];
  total_estimated_minutes: number;
  generated_from_report_id?: string;
}

export interface WorkspaceOverview {
  workspace: PrepWorkspace;
  latest_report?: PrepReadinessReport;
  pending_tasks: PrepTask[];
  active_workouts: PrepWorkout[];
}
