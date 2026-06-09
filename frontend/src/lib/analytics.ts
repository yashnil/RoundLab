/**
 * Lightweight frontend analytics helper.
 * Best-effort — all functions are fire-and-forget, never throw, never block.
 *
 * Events are sent to /users/{id}/events if the endpoint exists.
 * Until wired up server-side, calls 404 silently.
 */
import { apiFetch } from "@/lib/api";

export function logEvent(
  eventName: string,
  userId?: string | null,
  metadata?: Record<string, unknown>,
): void {
  if (!userId) return;
  // No await — truly fire-and-forget
  apiFetch(`/users/${userId}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_name: eventName,
      metadata_json: metadata ?? {},
    }),
  }).catch(() => {}); // silently swallow all errors
}
