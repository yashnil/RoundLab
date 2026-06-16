/**
 * Explicit recorder state model (pure, framework-free).
 *
 * The recording UI is driven by this reducer rather than a tangle of booleans.
 * Invalid transitions are ignored (the state is returned unchanged) so the UI
 * can never land in a contradictory state. `useRecorder` wraps this with the
 * actual MediaRecorder / getUserMedia side effects.
 */

export type RecorderStatus =
  | "idle"
  | "requesting-permission"
  | "ready"
  | "recording"
  | "stopping"
  | "recorded"
  | "playing"
  | "uploading"
  | "uploaded"
  | "error";

export interface RecorderState {
  status: RecorderStatus;
  /** Captured audio, preserved across upload failures. */
  blob: Blob | null;
  /** Object URL for playback; the hook revokes it on reset/replace. */
  url: string | null;
  /** Elapsed recording time in ms (stable; the hook ticks it). */
  durationMs: number;
  /** User-facing error message, if any. */
  error: string | null;
  /** Distinguishes permission errors from generic failures for the UI. */
  errorKind: "permission" | "unsupported" | "upload" | "generic" | null;
}

export type RecorderEvent =
  | { type: "REQUEST_PERMISSION" }
  | { type: "PERMISSION_GRANTED" }
  | { type: "PERMISSION_DENIED"; message: string }
  | { type: "UNSUPPORTED"; message: string }
  | { type: "START_RECORDING" }
  | { type: "TICK"; ms: number }
  | { type: "STOP_RECORDING" }
  | { type: "RECORDING_READY"; blob: Blob; url: string; durationMs?: number }
  | { type: "START_PLAYBACK" }
  | { type: "STOP_PLAYBACK" }
  | { type: "START_UPLOAD" }
  | { type: "UPLOAD_SUCCESS" }
  | { type: "UPLOAD_FAILURE"; message: string }
  | { type: "RESET" }
  | { type: "FAIL"; message: string };

export const initialRecorderState: RecorderState = {
  status: "idle",
  blob: null,
  url: null,
  durationMs: 0,
  error: null,
  errorKind: null,
};

/** True if `event` is a legal transition from the current `status`. */
export function canHandle(status: RecorderStatus, event: RecorderEvent): boolean {
  switch (event.type) {
    case "REQUEST_PERMISSION":
      return status === "idle" || status === "error";
    case "PERMISSION_GRANTED":
      return status === "requesting-permission";
    case "PERMISSION_DENIED":
    case "UNSUPPORTED":
      return status === "requesting-permission" || status === "idle";
    case "START_RECORDING":
      return status === "ready";
    case "TICK":
      return status === "recording";
    case "STOP_RECORDING":
      return status === "recording";
    case "RECORDING_READY":
      return status === "recording" || status === "stopping";
    case "START_PLAYBACK":
      return status === "recorded" || status === "uploaded";
    case "STOP_PLAYBACK":
      return status === "playing";
    case "START_UPLOAD":
      return status === "recorded";
    case "UPLOAD_SUCCESS":
      return status === "uploading";
    case "UPLOAD_FAILURE":
      return status === "uploading";
    case "FAIL":
      // Failing is allowed from any active state.
      return true;
    case "RESET":
      return true;
  }
}

export function recorderReducer(
  state: RecorderState,
  event: RecorderEvent,
): RecorderState {
  // Ignore illegal transitions — keeps the machine consistent.
  if (!canHandle(state.status, event)) return state;

  switch (event.type) {
    case "REQUEST_PERMISSION":
      return { ...state, status: "requesting-permission", error: null, errorKind: null };
    case "PERMISSION_GRANTED":
      return { ...state, status: "ready", error: null, errorKind: null };
    case "PERMISSION_DENIED":
      return { ...state, status: "error", error: event.message, errorKind: "permission" };
    case "UNSUPPORTED":
      return { ...state, status: "error", error: event.message, errorKind: "unsupported" };
    case "START_RECORDING":
      return { ...state, status: "recording", durationMs: 0, error: null, errorKind: null };
    case "TICK":
      return { ...state, durationMs: event.ms };
    case "STOP_RECORDING":
      return { ...state, status: "stopping" };
    case "RECORDING_READY":
      return {
        ...state,
        status: "recorded",
        blob: event.blob,
        url: event.url,
        durationMs: event.durationMs ?? state.durationMs,
      };
    case "START_PLAYBACK":
      return { ...state, status: "playing" };
    case "STOP_PLAYBACK":
      return { ...state, status: "recorded" };
    case "START_UPLOAD":
      return { ...state, status: "uploading", error: null, errorKind: null };
    case "UPLOAD_SUCCESS":
      return { ...state, status: "uploaded", error: null, errorKind: null };
    case "UPLOAD_FAILURE":
      // Preserve the recording so the user can retry without re-recording.
      return { ...state, status: "recorded", error: event.message, errorKind: "upload" };
    case "FAIL":
      // Keep any captured blob; the user shouldn't silently lose their take.
      return { ...state, status: "error", error: event.message, errorKind: "generic" };
    case "RESET":
      return { ...initialRecorderState };
  }
}

/** Format elapsed milliseconds as mm:ss for the timer display. */
export function formatRecorderClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60).toString().padStart(2, "0");
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** Is there a captured recording the user could lose? (For nav guards.) */
export function hasUnsavedRecording(state: RecorderState): boolean {
  return state.blob !== null && state.status !== "uploaded";
}

/** Is the recorder actively using the microphone? */
export function isCapturing(status: RecorderStatus): boolean {
  return status === "recording" || status === "stopping";
}
