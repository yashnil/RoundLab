import type { ProgressSummary, PilotSummary, Speech } from "@/types";

/**
 * Describes where a user is in the Dissio first-run loop.
 * Derived from real progress/pilot data — never faked.
 */
export type FirstRunState =
  | "no_activity"       // no speeches yet — show command center
  | "speech_started"    // speech exists but no coaching report
  | "report_ready"      // coaching report done, no drills assigned
  | "drill_ready"       // drills assigned but none attempted
  | "drill_attempted"   // at least one drill attempted, not re-recorded
  | "rerecord_ready"    // re-recorded, hasn't viewed comparison
  | "improvement_ready" // viewed comparison
  | "feedback_rated"    // rated feedback — loop complete
  | "active_user";      // many speeches + attempts — ongoing use

/**
 * Derive the first-run state from real progress/pilot data.
 * Rules are strictly sequential: earlier states are checked first.
 */
export function deriveFirstRunState(params: {
  progress: ProgressSummary | null;
  speeches?: Speech[];
  pilot?: PilotSummary | null;
}): FirstRunState {
  const { progress, speeches = [], pilot } = params;
  if (!progress) return "no_activity";

  // Threshold for "active user" — not doing first-run UX anymore
  if (progress.feedback_ready_count >= 3 && progress.drill_attempts_count >= 3) {
    return "active_user";
  }

  // Feedback rated → loop complete
  if (pilot && pilot.feedback_rating_count > 0) return "feedback_rated";

  // Improvement comparison viewed
  if (pilot && pilot.comparison_count > 0) return "improvement_ready";

  // Re-recorded at least once
  const hasRerecord = pilot
    ? pilot.rerecord_count > 0
    : speeches.some((s) => !!s.parent_speech_id);
  if (hasRerecord) return "rerecord_ready";

  // Drill attempted but not re-recorded
  if (progress.drill_attempts_count > 0) return "drill_attempted";

  // Drills assigned but none started
  if (progress.drills_assigned_count > 0) return "drill_ready";

  // Coaching report exists but no drills
  if (progress.feedback_ready_count > 0) return "report_ready";

  // Speech created but pipeline not complete
  if (progress.speech_count > 0) return "speech_started";

  return "no_activity";
}

/** Human-readable label for a first-run state (useful in analytics). */
export const FIRST_RUN_STATE_LABELS: Record<FirstRunState, string> = {
  no_activity:      "No activity",
  speech_started:   "Speech started",
  report_ready:     "Report ready",
  drill_ready:      "Drill ready",
  drill_attempted:  "Drill attempted",
  rerecord_ready:   "Rerecord ready",
  improvement_ready:"Improvement viewed",
  feedback_rated:   "Feedback rated",
  active_user:      "Active user",
};
