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
  /** Stable index-based ID (e.g. "arg_1"), assigned on save. Null for older argument maps. */
  id?: string | null;
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
  /** Added by migration 20260609400000 */
  source_type?: "ai" | "user_corrected";
  original_arguments?: ArgumentItem[] | null;
  user_corrected_at?: string | null;
  correction_notes?: string | null;
  updated_at?: string | null;
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

export interface ScoreExplanation {
  dimension_name: string;
  score: number;
  score_band: string;
  evidence_from_speech: string;
  why_not_higher: string;
  how_to_improve: string;
}

export type DebateIssueType =
  | "missing_warrant"
  | "weak_evidence"
  | "unclear_impact"
  | "no_weighing"
  | "dropped_argument"
  | "weak_extension"
  | "no_clash"
  | "new_argument"
  | "organization"
  | "delivery";

export type IssueSeverity = "low" | "medium" | "high";

export interface DebateIssue {
  issue_type: DebateIssueType;
  severity: IssueSeverity;
  title: string;
  explanation: string;
  why_it_matters: string;
  recommendation: string;
  affected_argument_labels: string[];
  recommended_drill_type: string;
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
    score_explanations?: ScoreExplanation[];
    /** Structured debate issues — present in v2+ reports only */
    structured_issues?: DebateIssue[];
    calibrated_scores?: Record<string, number>;
    calibration_warnings?: string[];
    scoring_version?: string;
    report_input_hash?: string;
    /** Set when coaching was regenerated from a user-corrected flow */
    flow_correction_regenerated_at?: string | null;
    regenerated_from_correction?: boolean;
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
  /** Set when this speech was recorded to improve upon an earlier one. */
  parent_speech_id: string | null;
  /** The drill that motivated this re-record (used for improvement comparison). */
  source_drill_id: string | null;
}

/** Deterministic improvement comparison between a re-recorded speech and its parent. */
export interface SpeechComparisonResult {
  has_parent: boolean;
  parent_speech_id: string | null;
  source_drill_id: string | null;
  source_drill_skill: string | null;
  original_overall_score: number | null;
  new_overall_score: number | null;
  overall_delta: number | null;
  original_skill_score: number | null;
  new_skill_score: number | null;
  skill_delta: number | null;
  // Delivery deltas — only present when both speeches have delivery metrics
  original_delivery_score?: number | null;
  new_delivery_score?: number | null;
  delivery_score_delta?: number | null;
  original_wpm?: number | null;
  new_wpm?: number | null;
  wpm_delta?: number | null;
  original_filler_count?: number | null;
  new_filler_count?: number | null;
  filler_delta?: number | null;
  summary: string;
  still_needs_work: string | null;
  next_action: string;
}

export type PacingBand = "too_slow" | "steady" | "too_fast" | "unknown";

export interface DeliveryTimelineSegment {
  segment_index: number;
  approx_start_seconds: number | null;
  approx_end_seconds: number | null;
  word_count: number;
  filler_count: number;
  repeated_phrase_hits: number;
  excerpt: string;
  flags: string[];
}

export interface DeliveryMetrics {
  id?: string;
  speech_id: string;
  user_id: string;
  word_count: number | null;
  duration_seconds: number | null;
  words_per_minute: number | null;
  filler_word_count: number | null;
  filler_words_json: Record<string, number> | null;
  repeated_phrases_json: Array<{ phrase: string; count: number }> | null;
  long_sentence_count: number | null;
  average_sentence_words: number | null;
  delivery_score: number | null;
  pacing_band: PacingBand | null;
  clarity_flags_json: string[] | null;
  timeline_json: DeliveryTimelineSegment[] | null;
  created_at?: string;
  updated_at?: string;
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
  /** LLM-generated recommended practice time in seconds (30–300). Null for older drills. */
  time_limit_seconds: number | null;
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

// ── Analysis Jobs ─────────────────────────────────────────────────────────────

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type JobType =
  | "speech_analysis"
  | "drill_attempt_scoring"
  | "evidence_check"
  | "evidence_drill_generation"
  | "document_parse";

export interface AnalysisJob {
  id: string;
  user_id: string;
  speech_id: string | null;
  job_type: JobType;
  status: JobStatus;
  current_step: string | null;
  progress: number | null;
  error_message: string | null;
  error_code: string | null;
  result_json: Record<string, unknown> | null;
  attempt_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalyzeResponse {
  job_id: string;
  status: JobStatus;
}

// ── Evidence-Aware Coach types ─────────────────────────────────────────────────

export type DocumentStatus = "uploaded" | "parsed" | "failed";
export type DocumentType = "case" | "evidence" | "brief" | "other";
export type EvidenceSupportLevel =
  | "supported"
  | "partially_supported"
  | "unsupported"
  | "unverifiable";

export interface EvidenceDocument {
  id: string;
  user_id: string;
  team_id: string | null;
  filename: string;
  storage_path: string;
  doc_type: DocumentType;
  status: DocumentStatus;
  file_size_bytes: number | null;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  user_id: string;
  chunk_text: string;
  chunk_index: number;
  heading: string | null;
  page_number: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface EvidenceCard {
  id: string;
  document_id: string;
  user_id: string;
  chunk_id: string | null;
  tag: string | null;
  author: string | null;
  source: string | null;
  year: number | null;
  card_text: string;
  claim_summary: string | null;
  attribution_complete: boolean;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface ClaimEvidenceCheck {
  id: string;
  speech_id: string;
  user_id: string;
  argument_label: string | null;
  claim_text: string;
  evidence_text_from_speech: string | null;
  matched_card_id: string | null;
  support_level: EvidenceSupportLevel | null;
  explanation: string | null;
  created_at: string;
}

export interface DocumentWithCards {
  document: EvidenceDocument;
  chunks: DocumentChunk[];
  cards: EvidenceCard[];
}

export interface SearchResultItem {
  chunk: DocumentChunk;
  document_filename: string;
  cards: EvidenceCard[];
}

export interface EvidenceCheckResult {
  argument_label: string | null;
  claim_text: string;
  evidence_text_from_speech: string | null;
  matched_card: EvidenceCard | null;
  support_level: EvidenceSupportLevel;
  explanation: string;
}

// ── Pilot / Analytics types ───────────────────────────────────────────────────

export type FeedbackRating = "helpful" | "somewhat" | "not_helpful";
export type DrillRating = "helpful" | "somewhat" | "not_helpful";

export interface DrillRatingRow {
  id: string;
  user_id: string;
  drill_id: string;
  drill_attempt_id: string | null;
  rating: DrillRating;
  comment: string | null;
  created_at: string;
}

export type OutputFeedbackCategory =
  | "incorrect_issue"
  | "generic_feedback"
  | "evidence_mismatch"
  | "confusing_wording"
  | "technical_bug"
  | "other";

export type OutputFeedbackTargetType =
  | "speech_report"
  | "drill_feedback"
  | "evidence_check";

export interface SkillTrend {
  current: number;
  previous: number | null;
  delta: number | null;
  trend: "improving" | "stable" | "needs_attention" | "no_data";
}

export interface SkillTrends {
  clash: SkillTrend;
  weighing: SkillTrend;
  extensions: SkillTrend;
  drops: SkillTrend;
  judge_adaptation: SkillTrend;
}

export interface PilotSummary {
  speech_count: number;
  analyzed_speech_count: number;
  drill_count: number;
  drill_attempt_count: number;
  completed_drill_count: number;
  rerecord_count: number;
  comparison_count: number;
  feedback_rating_count: number;
  average_feedback_rating: number | null;
  drill_rating_count: number;
  average_drill_rating: number | null;
  return_for_second_speech: boolean;
  completed_one_drill: boolean;
  latest_skill_scores: Record<string, number> | null;
  skill_trends: SkillTrends | null;
  common_issues: string[];
}

export interface PilotAggregate {
  total_users: number;
  speeches_uploaded: number;
  analyzed_speeches: number;
  drills_assigned: number;
  drill_attempts: number;
  rerecords: number;
  feedback_ratings: number;
  average_feedback_usefulness: number | null;
  drill_ratings: number;
  average_drill_usefulness: number | null;
  common_issues: string[];
  common_drop_off: string;
}
