/**
 * Pure derivation of the speech workspace's top-level view.
 *
 * Route rendering should depend on this single function instead of scattered
 * boolean combinations. It never invents a backend status — it combines the
 * canonical speech status with local capture/upload state.
 */

import type { SpeechStatus } from "@/types";

export type SpeechWorkspaceView =
  | "capture"
  | "uploading"
  | "processing"
  | "report"
  | "failure"
  | "not-found";

export type LocalUploadStatus = "idle" | "uploading" | "uploaded" | "error";

export interface SpeechWorkspaceInput {
  /** Canonical backend status, or null when the speech can't be loaded. */
  speechStatus: SpeechStatus | null;
  /** The speech record is missing/deleted. */
  notFound?: boolean;
  /** A local, not-yet-saved recording or file exists. */
  hasLocalRecording?: boolean;
  uploadStatus?: LocalUploadStatus;
  hasSavedAudio?: boolean;
  hasTranscript?: boolean;
  /** Feedback/report data is present. */
  hasReport?: boolean;
}

export function deriveSpeechWorkspaceView(
  input: SpeechWorkspaceInput,
): SpeechWorkspaceView {
  const { speechStatus, notFound, uploadStatus, hasReport } = input;

  if (notFound || speechStatus === null) return "not-found";

  // A failed analysis is terminal until the user retries.
  if (speechStatus === "error") return "failure";

  // A local upload in flight takes precedence over the (still pending) status.
  if (uploadStatus === "uploading") return "uploading";

  // Backend is actively transcribing or analyzing.
  if (speechStatus === "transcribing" || speechStatus === "analyzing") {
    return "processing";
  }

  // Completed: show the report when its data is present; otherwise keep the
  // student in processing rather than rendering an empty "report".
  if (speechStatus === "done") {
    return hasReport ? "report" : "processing";
  }

  // pending → still gathering media.
  return "capture";
}

/**
 * Whether it's safe for the student to navigate away. Processing on this
 * backend keeps the request flow open, so leaving during capture/upload/
 * processing risks losing progress.
 */
export function isSafeToLeave(view: SpeechWorkspaceView): boolean {
  return view === "report" || view === "failure" || view === "not-found";
}
