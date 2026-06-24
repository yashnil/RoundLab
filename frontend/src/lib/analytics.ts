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
