/**
 * Lightweight frontend analytics helper.
 * Best-effort — all functions are fire-and-forget, never throw, never block.
 *
 * Events are sent to the backend product_events table via /users/{id}/events.
 *
 * Signature: logEvent(eventName, userId?, metadata?)
 * (userId comes second for backward compatibility with existing call sites)
 *
 * Pilot funnel helpers use typed wrappers below. Do NOT include speech text,
 * evidence body, audio, or private notes in metadata.
 */
import { apiFetch } from "@/lib/api";

/** Base log function. Never throws, never blocks. */
export function logEvent(
  eventName: string,
  userId?: string | null,
  metadata?: Record<string, unknown>,
): void {
  if (!userId) return;
  apiFetch(`/users/${userId}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_name: eventName,
      metadata_json: metadata ?? {},
    }),
  }).catch(() => {});
}

// ── Typed pilot funnel helpers ─────────────────────────────────────────────

export function logOnboardingStep(userId: string, step: string): void {
  logEvent("onboarding_step_completed", userId, { step });
}

export function logOnboardingCompleted(userId: string, role: string): void {
  logEvent("onboarding_completed", userId, { role });
}

export function logEvidenceSaved(userId: string, cardId: string): void {
  logEvent("evidence_card_saved", userId, { card_id: cardId });
}

export function logRoundStarted(userId: string, roundId: string, format: string): void {
  logEvent("round_started", userId, { round_id: roundId, format });
}

export function logRoundCompleted(userId: string, roundId: string): void {
  logEvent("round_completed", userId, { round_id: roundId });
}

export function logDrillCompleted(userId: string, drillId: string): void {
  logEvent("drill_completed", userId, { drill_id: drillId });
}

export function logCoachReviewCompleted(userId: string, roundId: string): void {
  logEvent("coach_review_completed", userId, { round_id: roundId });
}

export function logFeedbackUseful(
  userId: string,
  feature: string,
  resourceId?: string,
): void {
  logEvent("feedback_marked_useful", userId, { feature, resource_id: resourceId });
}

export function logWorkflowFailure(
  userId: string,
  stage: string,
  errorCode: string,
): void {
  logEvent("workflow_stage_failed", userId, { stage, error_code: errorCode });
}

// ── Training OS analytics ──────────────────────────────────────────────────
// IMPORTANT: Never include transcript text, audio, evidence body, student
// names, email addresses, or sensitive notes in any of these events.

export function logDiagnosticStarted(userId: string, experienceLevel: string): void {
  logEvent("diagnostic_started", userId, { experience_level: experienceLevel });
}

export function logDiagnosticCompleted(userId: string, planId: string): void {
  logEvent("diagnostic_completed", userId, { plan_id: planId });
}

export function logLessonStarted(userId: string, lessonId: string, skillId: string): void {
  logEvent("lesson_started", userId, { lesson_id: lessonId, skill_id: skillId });
}

export function logLessonCompleted(
  userId: string,
  lessonId: string,
  skillId: string,
  score?: number,
): void {
  logEvent("lesson_completed", userId, { lesson_id: lessonId, skill_id: skillId, score });
}

export function logTrainingDrillStarted(userId: string, drillId: string, skillId: string): void {
  logEvent("training_drill_started", userId, { drill_id: drillId, skill_id: skillId });
}

export function logTrainingDrillCompleted(
  userId: string,
  drillId: string,
  skillId: string,
  scorePct: number,
): void {
  logEvent("training_drill_completed", userId, {
    drill_id: drillId,
    skill_id: skillId,
    score_pct: scorePct,
  });
}

export function logSpeechSubmitted(userId: string, speechId: string, speechType: string): void {
  logEvent("speech_submitted", userId, { speech_id: speechId, speech_type: speechType });
}

export function logRerecordCompleted(
  userId: string,
  speechId: string,
  parentSpeechId: string,
): void {
  logEvent("rerecord_completed", userId, {
    speech_id: speechId,
    parent_speech_id: parentSpeechId,
  });
}

export function logPlanResumed(userId: string, planId: string, week: number): void {
  logEvent("plan_resumed", userId, { plan_id: planId, current_week: week });
}

export function logPlanAbandoned(userId: string, planId: string): void {
  logEvent("plan_abandoned", userId, { plan_id: planId });
}

export function logCoachOverride(
  userId: string,
  studentId: string,
  skillId: string,
): void {
  // Note: coach user ID only, never student names or sensitive details
  logEvent("coach_mastery_override", userId, { skill_id: skillId });
}

export function logMasteryStateChange(
  userId: string,
  skillId: string,
  fromState: string,
  toState: string,
): void {
  logEvent("mastery_state_changed", userId, {
    skill_id: skillId,
    from_state: fromState,
    to_state: toState,
  });
}

export function logUploadFailure(userId: string, stage: string): void {
  logEvent("upload_failed", userId, { stage });
}

export function logAnalysisFailure(userId: string, speechId: string, stage: string): void {
  logEvent("analysis_failed", userId, { speech_id: speechId, stage });
}
