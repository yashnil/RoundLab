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

// ── Assignments ───────────────────────────────────────────────────────────────

export type AssignmentKind = "speech" | "rerecord" | "drill";
/** Effective status derived from the lifecycle + real analysis state. */
export type RecipientState =
  | "assigned"
  | "started"
  | "processing"
  | "ready_for_review"
  | "failed"
  | "reviewed"
  | "revision_requested";

export interface RecipientStatus {
  id: string;
  user_id: string;
  display_name: string | null;
  status: RecipientState;
  base_status?: string;
  submission_speech_id: string | null;
  coach_feedback: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
}

export interface Assignment {
  id: string;
  team_id: string;
  created_by: string;
  title: string;
  kind: AssignmentKind;
  speech_type: string | null;
  side: string | null;
  judge_type: string | null;
  topic: string | null;
  goal: string | null;
  success_criteria: string[];
  due_date: string | null;
  created_at: string;
  recipients: RecipientStatus[];
}

export interface ReviewQueueItem {
  recipient_id: string;
  assignment_id: string;
  assignment_title: string;
  student_id: string;
  student_name: string | null;
  status: RecipientState;
  submission_speech_id: string | null;
  submitted_at: string | null;
}

export interface TeamReadiness {
  team_id: string;
  assignment_count: number;
  recipient_total: number;
  assigned: number;
  in_progress: number;
  ready_for_review: number;
  failed: number;
  reviewed: number;
  revision_requested: number;
  review_backlog: number;
  completion_rate: number | null;
}

export interface AssignmentForSpeech {
  viewer_is_coach: boolean;
  recipient: {
    id: string;
    user_id: string;
    status: RecipientState;
    base_status: string;
    coach_feedback: string | null;
    submission_speech_id: string | null;
  };
  assignment: {
    id: string;
    title: string;
    kind: AssignmentKind;
    goal: string | null;
    success_criteria: string[];
    due_date: string | null;
    team_id: string;
  } | null;
}

export interface CoachStudentProfile {
  student_id: string;
  display_name: string | null;
  speech_count: number;
  feedback_ready_count: number;
  speeches: { id: string; title: string; speech_type: string; status: string; created_at: string }[];
  assignments: { recipient_id: string; title: string; status: RecipientState; submission_speech_id: string | null }[];
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
export type SearchMode = "keyword" | "semantic" | "hybrid";
export type EvidenceRetrievalMode = "semantic" | "keyword" | "none";

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
  // Blockfile trainer fields (added by migration 20260609900000)
  document_role?: DocumentRole | null;
  debate_side?: string | null;
  topic?: string | null;
  blockfile_metadata_json?: Record<string, unknown>;
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
  /** Saved markup so the Library preview can re-render user formatting. */
  highlighted_spans_json?: UserMarkupSpan[];
  underline_spans_json?: UserMarkupSpan[];
  card_cutting_metadata_json?: { user_markup?: UserCardMarkup } & Record<string, unknown>;
  created_at: string;
}

export interface RetrievedSnippet {
  chunk_id: string;
  document_id: string;
  snippet: string;
  similarity: number;
  heading: string | null;
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
  // RAG fields (added in Evidence RAG v1; optional for pre-RAG rows)
  matched_chunk_ids?: string[] | null;
  top_similarity?: number | null;
  retrieved_snippets_json?: RetrievedSnippet[] | null;
  support_rationale?: string | null;
  missing_link?: string | null;
  retrieval_mode?: EvidenceRetrievalMode | null;
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
  similarity: number | null;
  retrieval_mode: string | null;
}

export interface EvidenceCheckResult {
  argument_label: string | null;
  claim_text: string;
  evidence_text_from_speech: string | null;
  matched_card: EvidenceCard | null;
  support_level: EvidenceSupportLevel;
  explanation: string;
  // RAG fields (optional for backward compatibility)
  matched_chunk_ids?: string[] | null;
  top_similarity?: number | null;
  retrieved_snippets?: RetrievedSnippet[] | null;
  support_rationale?: string | null;
  missing_link?: string | null;
  retrieval_mode?: EvidenceRetrievalMode | null;
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

// ── Share report types ────────────────────────────────────────────────────────

export interface ShareResponse {
  id: string;
  share_token: string;
  include_transcript: boolean;
  include_flow: boolean;
  include_feedback: boolean;
  include_drills: boolean;
  include_delivery: boolean;
  include_evidence_summary: boolean;
  include_improvement: boolean;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateShareRequest {
  user_id: string;
  include_transcript?: boolean;
  include_flow?: boolean;
  include_feedback?: boolean;
  include_drills?: boolean;
  include_delivery?: boolean;
  include_evidence_summary?: boolean;
  include_improvement?: boolean;
  expires_in_days?: number | null;
}

export interface SharedReportFeedback {
  overall_score: number | null;
  scores: FeedbackScores | null;
  summary: string | null;
  strengths: string[];
  weaknesses: string[];
  top_3_priorities: string[] | null;
  structured_issues: DebateIssue[] | null;
}

export interface SharedReportArgument {
  label: string;
  claim: string;
  warrant: string;
  evidence: string | null;
  impact: string;
  argument_type: ArgumentType;
}

export interface SharedReportDrill {
  title: string;
  description: string | null;
  skill_target: string;
  prompt: string;
  success_criteria: string[];
  difficulty: string;
}

export interface SharedReportDelivery {
  words_per_minute: number | null;
  filler_word_count: number | null;
  delivery_score: number | null;
  pacing_band: string | null;
  repeated_phrases_json: Array<{ phrase: string; count: number }> | null;
}

export interface SharedReportEvidenceSummary {
  supported_count: number;
  partially_supported_count: number;
  unsupported_count: number;
  unverifiable_count: number;
  top_issues: Array<{
    claim_text: string;
    support_level: string;
    explanation: string | null;
  }>;
}

export interface SharedReportComparison {
  original_overall_score: number | null;
  new_overall_score: number | null;
  overall_delta: number | null;
  original_delivery_score: number | null;
  new_delivery_score: number | null;
  delivery_score_delta: number | null;
  original_wpm: number | null;
  new_wpm: number | null;
  wpm_delta: number | null;
  original_filler_count: number | null;
  new_filler_count: number | null;
  filler_delta: number | null;
  summary: string;
}

export interface SharedReportIncludeFlags {
  transcript: boolean;
  flow: boolean;
  feedback: boolean;
  drills: boolean;
  delivery: boolean;
  evidence_summary: boolean;
  improvement: boolean;
}

export interface SharedReportPayload {
  token: string;
  speech_type: SpeechType;
  side: SpeechSide | null;
  judge_type: JudgeType | null;
  topic: string | null;
  created_at: string;
  feedback: SharedReportFeedback | null;
  arguments: SharedReportArgument[] | null;
  drills: SharedReportDrill[] | null;
  delivery: SharedReportDelivery | null;
  transcript_text: string | null;
  evidence_summary: SharedReportEvidenceSummary | null;
  comparison: SharedReportComparison | null;
  include_flags: SharedReportIncludeFlags;
}

// ── Tournament Prep Workout ────────────────────────────────────────────────────

export type WorkoutStatus = "not_started" | "in_progress" | "completed";
export type WorkoutStepCategory = "argument" | "evidence" | "delivery" | "rerecord" | "blockfile";
export type WorkoutStepSource = "feedback" | "drill" | "delivery" | "evidence";

export interface WorkoutStep {
  id: string;
  title: string;
  category: WorkoutStepCategory;
  focus: string;
  estimated_minutes: number;
  source: WorkoutStepSource;
  problem: string;
  instruction: string;
  success_criteria: string;
  linked_drill_id?: string | null;
  completed: boolean;
}

export interface WorkoutJson {
  steps: WorkoutStep[];
  re_record_goal: string;
  coach_note: string;
  generated_from: {
    feedback_report_id?: string | null;
    argument_map_id?: string | null;
    delivery_metrics_id?: string | null;
  };
}

export interface Workout {
  id: string;
  user_id: string;
  speech_id: string;
  title: string;
  description?: string | null;
  estimated_minutes?: number | null;
  workout_type: string;
  status: WorkoutStatus;
  focus_area?: string | null;
  workout_json: WorkoutJson;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

// ── Blockfile and Frontline Trainer ───────────────────────────────────────────

export type BlockEntryType =
  | "block" | "frontline" | "answer" | "turn"
  | "defense" | "weighing" | "overview" | "unknown";

export type BlockCoverageStatus =
  | "covered" | "partially_covered" | "missing" | "no_available_block";

export type DocumentRole =
  | "evidence" | "case" | "blockfile" | "frontline" | "mixed";

export interface BlockEntry {
  id: string;
  user_id: string;
  document_id: string | null;
  source_chunk_id: string | null;
  entry_type: BlockEntryType;
  side: string | null;
  tag: string | null;
  opponent_claim: string | null;
  response_text: string;
  warrant_text: string | null;
  evidence_text: string | null;
  impact_text: string | null;
  weighing_text: string | null;
  author: string | null;
  source: string | null;
  date: string | null;
  topic: string | null;
  metadata_json: Record<string, unknown>;
  embedding_model: string | null;
  embedded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BlockCoverageCheck {
  id: string;
  user_id: string;
  speech_id: string;
  argument_id: string | null;
  claim_text: string;
  check_type: "block" | "frontline";
  status: BlockCoverageStatus;
  matched_block_entry_ids: string[];
  top_similarity: number | null;
  rationale: string | null;
  missing_piece: string | null;
  suggested_drill_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface BlockCoverageResponse {
  speech_id: string;
  checks: BlockCoverageCheck[];
  covered_count: number;
  partially_covered_count: number;
  missing_count: number;
  no_available_block_count: number;
  total_block_entries: number;
}

export interface ExtractBlocksResponse {
  document_id: string;
  entries_extracted: number;
  entries_embedded: number;
  entries: BlockEntry[];
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

// ── Research-to-Card Evidence Builder ─────────────────────────────────────────

export type SourceQuality = "high" | "medium" | "low" | "unknown";
export type CardDraftStatus = "draft" | "saved" | "discarded";
export type CardSourceType = "url" | "manual_paste" | "research_search";
export type SupportLevel = "strong_support" | "partial_support" | "weak_support" | "no_support";
export type CardPurpose =
  | "uniqueness" | "link" | "internal_link" | "impact" | "answer"
  | "frontline" | "weighing" | "background" | "solvency" | "harm" | "unknown";
export type EvidenceRole =
  | "direct_support"
  | "mechanism_support"
  | "example_support"
  | "impact_support"
  | "definition_support"
  | "authority_support"
  | "counter_evidence"
  | "not_useful";

export interface HighlightSpan {
  start: number;
  end: number;
  type?: "highlight" | "underline";
  reason?: string;
}

export interface SelectedSpan {
  start: number;
  end: number;
  text: string;
  sentence_index: number;
  rationale?: string;
}

/** A persisted user markup span (offsets into the edited card body). */
export interface UserMarkupSpan {
  start: number;
  end: number;
  text?: string;
  type: "highlight" | "underline" | "bold" | "italic";
  reason?: string;
}

/** All user-applied card formatting, persisted on save. */
export interface UserCardMarkup {
  highlight: UserMarkupSpan[];
  underline: UserMarkupSpan[];
  bold: UserMarkupSpan[];
  italic: UserMarkupSpan[];
}

export interface AnnotatedSpan extends SelectedSpan {
  id?: string;
  selected_by?: "ai" | "user";
  confidence?: number;
  prefix?: string;
  suffix?: string;
}

export interface EvidenceCutResult {
  original_passage: string;
  selected_spans: SelectedSpan[];
  cut_text: string;
  cut_text_with_ellipses: string;
  compression_ratio: number;
  confidence: number;
  cut_style: "full" | "light_cut" | "medium_cut" | "aggressive_cut";
  validation_passed: boolean;
  validation_notes?: string;
  // Part 4 — cut quality signals
  cut_confidence?: number;
  cut_warnings?: string[];
  bold_spans?: SelectedSpan[];
  annotated_spans?: AnnotatedSpan[];
  // Part 4b — spans remapped to cut_text_with_ellipses (for card-body highlighting)
  cut_body_spans?: SelectedSpan[];
  cut_body_bold_spans?: SelectedSpan[];
  // Part 4c — user-annotated underline spans (offsets in cut_text_with_ellipses)
  cut_body_underline_spans?: SelectedSpan[];
}

export interface CitationMetadata {
  author_display: string;
  authors: string[];
  year: string;
  title: string;
  container_title?: string;
  publication_name: string;
  url: string;
  doi?: string;
  accessed_date: string;
  citation_quality: "complete" | "partial" | "weak";
  mla_citation: string;
  short_cite: string;
  // Part 3 — citation provenance
  author_source?: string;
  date_source?: string;
  title_source?: string;
  publication_source?: string;
}

// Evidence Set Builder (Parts 1-2)
export interface EvidenceSlot {
  slot_id: string;
  slot_label: string;
  strategic_function: string;
  target_claim: string;
  desired_evidence_role: string;
  search_intent: string;
  preferred_source_types?: string[];
  recency_policy?: string;
  must_have_terms?: string[];
  helpful_terms?: string[];
  avoid_terms?: string[];
  success_criteria?: string;
}

export interface EvidenceSetPlan {
  topic: string;
  claim: string;
  side: string;
  slots: EvidenceSlot[];
  planning_method: "llm" | "deterministic";
}

export interface WeakLead {
  url?: string | null;
  tag?: string | null;
  slot_label?: string;
  short_cite?: string;
  reason?: string;
  body_excerpt?: string;
}

export interface CardIntelligence {
  why_this_card: string;
  supports_claim_because: string[];
  best_use:
    | "contention"
    | "rebuttal"
    | "summary"
    | "final_focus"
    | "frontline"
    | "weighing"
    | "impact"
    | "definition"
    | "crossfire";
  debate_use_notes: string[];
  limitations: string[];
  suggested_block_label: string;
  save_readiness: "ready" | "review_needed" | "weak";
  save_readiness_reasons: string[];
  // Part 9 — slot-aware debate intelligence
  opponent_response?: string;
  crossfire_question?: string;
  // Overhaul — structured debate-prep coaching
  warrant_analysis?: string;
  impact_analysis?: string;
  potential_weakness?: string;
  how_to_answer_weakness?: string;
  crossfire_answer?: string;
  best_pairing?: string;
  weighing_angle?: string;
}

export interface RegenerateCutRequest {
  original_passage: string;
  claim: string;
  evidence_role?: string;
  tag?: string;
  cut_style?: string;
  use_llm?: boolean;
}

export interface RegenerateCutResponse {
  cut: EvidenceCutResult;
  cut_style_applied: string;
}

export interface ArticleMetadata {
  title: string | null;
  author: string | null;
  publication: string | null;
  published_date: string | null;
  url: string;
  canonical_url?: string | null;
  language?: string | null;
  excerpt?: string | null;
  warnings: string[];
}

export interface ExtractedArticle {
  url: string;
  metadata: ArticleMetadata;
  extracted_text: string;
  extraction_method: string;
  extraction_confidence: number;
  status: "ok" | "partial" | "failed";
  error?: string | null;
}

export interface SourceQualityResult {
  source_quality: SourceQuality;
  credibility_notes: string;
  warnings: string[];
}

export interface ExtractUrlResponse {
  research_source_id: string;
  article: ExtractedArticle;
  quality: SourceQualityResult;
}

export interface SearchSourceCandidate {
  title: string;
  url: string;
  snippet: string;
  publication: string | null;
  published_date: string | null;
  source_quality: SourceQuality | null;
}

export interface SearchSourcesResponse {
  results: SearchSourceCandidate[];
  provider?: string | null;
  fallback?: string | null;
}

export interface CardDraft {
  id: string;
  user_id: string;
  research_source_id: string | null;
  url: string | null;
  topic: string | null;
  claim_goal: string | null;
  side: string | null;
  tag: string;
  cite: string;
  body_text: string;
  highlighted_spans_json: HighlightSpan[];
  underline_spans_json: HighlightSpan[];
  /**
   * Full user-applied card markup captured in the Studio editor. Highlight and
   * underline also mirror into their dedicated columns; bold and italic live
   * only here (and are persisted into card_cutting_metadata_json on save) so no
   * formatting edit is ever lost.
   */
  user_markup_json?: UserCardMarkup | null;
  author: string | null;
  publication: string | null;
  title: string | null;
  published_date: string | null;
  author_credentials: string | null;
  warrant_summary: string | null;
  impact_summary: string | null;
  source_quality: SourceQuality | null;
  credibility_notes: string | null;
  extraction_confidence: number | null;
  generated_tag: boolean;
  missing_metadata_json: Record<string, string>;
  card_source_type: CardSourceType | null;
  status: CardDraftStatus;
  saved_card_id: string | null;
  // Research-search extra fields (populated from draft_json by backend)
  support_level?: SupportLevel | null;
  support_rationale?: string | null;
  card_purpose?: CardPurpose | null;
  claim_supported?: boolean | null;
  best_supported_claim?: string | null;
  overclaim_warning?: string | null;
  safe_tag_scope?: string | null;
  evidence_role?: EvidenceRole | null;
  is_counter_evidence?: boolean | null;
  is_snippet_source?: boolean | null;
  // New evidence cut fields (all optional for backward compat)
  evidence_cut?: EvidenceCutResult | null;
  citation?: CitationMetadata | null;
  intelligence?: CardIntelligence | null;
  cut_text_with_ellipses?: string | null;
  selected_spans?: SelectedSpan[] | null;
  short_cite?: string | null;
  mla_citation?: string | null;
  citation_quality?: "complete" | "partial" | "weak" | null;
  extraction_method?: string | null;
  source_domain?: string | null;
  source_title?: string | null;
  // Evidence Set Builder slot assignment (Parts 2 + 9)
  slot_id?: string | null;
  slot_label?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SaveDraftResponse {
  card_id: string;
  draft_id: string;
  message: string;
}

export interface SearchDiagnostics {
  sources_found: number;
  sources_attempted: number;
  sources_extracted: number;
  passages_considered: number;
  candidates_generated: number;
  filtered_no_support: number;
  filtered_low_quality: number;
  query_variants_used: string[];
  // Extended diagnostics (Change 7)
  urls_extracted_full?: number;
  urls_snippet_only?: number;
  chunks_created?: number;
  chunks_after_quality_filter?: number;
  chunks_classified?: number;
  rejected_by_low_source_quality?: number;
  rejected_by_low_debate_usefulness?: number;
  rejected_by_overclaim?: number;
  rejected_as_counter_evidence?: number;
  providers_used?: string[];
  queries_run?: string[];
  possible_lead_urls?: string[];
  reranker_used?: string;
  // Firecrawl / Cohere instrumentation
  firecrawl_attempted?: number;
  firecrawl_succeeded?: number;
  firecrawl_failed?: number;
  cohere_rerank_attempted?: number;
  cohere_rerank_succeeded?: number;
  // Per-slot search diagnostics (populated when slot planner is active)
  slot_diagnostics?: Record<string, unknown> | null;
  slot_queries_run?: Record<string, string[]> | null;
  slot_cards_filled?: string[];
  slot_weak_leads?: string[];
  slot_unfilled_reasons?: Record<string, string> | null;
}

export interface GenerateCardsResponse {
  search_configured: boolean;
  query_used?: string | null;
  cards: CardDraft[];
  sources_considered?: Array<{ url: string; status: string; reason?: string; quality?: string; support_level?: string }>;
  no_card_reason?: string | null;
  suggestions?: string[];
  warnings?: string[];
  diagnostics?: SearchDiagnostics | null;
  suggested_revised_claims?: string[];
  normalized_claim?: string | null;
  corrections_applied?: string[];
  candidates_by_role?: Record<string, number>;
  // Claim ladder support indicators (Change 4)
  direct_support_found?: boolean;
  usable_indirect_support_found?: boolean;
  indirect_support_explanation?: string | null;
  // Evidence Set Builder (Parts 2 + 6)
  weak_leads?: WeakLead[];
  unfilled_slots?: string[];
  evidence_set_plan?: EvidenceSetPlan | null;
}

export interface ResearchConfigResponse {
  search_provider: string;
  search_configured: boolean;
  url_extraction_available: boolean;
  card_builder_available: boolean;
}
