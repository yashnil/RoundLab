/**
 * Shared capture save-state model.
 *
 * Record, upload, and paste each have their own controller, but the student
 * needs one honest answer to: "is my work saved, and can I leave?". This pure
 * module normalizes those controllers into a single persistence status and the
 * exact copy that may be shown for it. It NEVER claims input is saved unless the
 * caller passes a state that proves it.
 */

import type { RecorderStatus } from "@/lib/recorder";
import type { UploadStatus } from "@/hooks/useSpeechUpload";

export type CaptureInputMode = "record" | "upload" | "paste";

export type CapturePersistenceStatus =
  | "empty"
  | "local-only"
  | "uploading"
  | "saving"
  | "saved"
  | "analysis-starting"
  | "analysis-running"
  | "analysis-failed"
  | "error";

export type CaptureTone = "neutral" | "info" | "success" | "warning" | "error";

export interface CaptureStatusViewModel {
  status: CapturePersistenceStatus;
  title: string;
  description: string;
  /** Whether the student can navigate away without losing/risking work. */
  canSafelyLeave: boolean;
  /** Whether the current state offers a retry. */
  retryable: boolean;
  tone: CaptureTone;
}

export interface CaptureStatusInput {
  mode: CaptureInputMode;
  recorderStatus: RecorderStatus;
  uploadStatus: UploadStatus;
  /** True once the speech record has a persisted audio_url. */
  hasSavedAudio: boolean;
  /** True when there is an active analysis job. */
  analysisActive: boolean;
  /** True when analysis has failed and not been recovered. */
  analysisFailed: boolean;
  /** True when a pasted draft exists but hasn't been submitted. */
  pasteDirty: boolean;
  /** True while a pasted draft is being submitted. */
  submittingPaste: boolean;
}

/** Derive the single persistence status from the live controllers. */
export function deriveCaptureStatus(input: CaptureStatusInput): CapturePersistenceStatus {
  const {
    mode, recorderStatus, uploadStatus, hasSavedAudio,
    analysisActive, analysisFailed, pasteDirty, submittingPaste,
  } = input;

  // Analysis outcomes take precedence — the audio is already saved by then.
  if (analysisFailed) return "analysis-failed";
  if (analysisActive) return "analysis-running";

  if (mode === "record") {
    if (recorderStatus === "uploading") return "uploading";
    if (recorderStatus === "error") return "error";
    if (recorderStatus === "recording" || recorderStatus === "stopping") return "local-only";
    if (recorderStatus === "recorded" || recorderStatus === "playing") return "local-only";
    if (recorderStatus === "uploaded" || hasSavedAudio) return "saved";
    return "empty";
  }

  if (mode === "upload") {
    if (uploadStatus === "uploading") return "uploading";
    if (uploadStatus === "error") return "error";
    if (uploadStatus === "uploaded" || hasSavedAudio) return "saved";
    if (uploadStatus === "ready") return "local-only";
    return "empty";
  }

  // paste
  if (submittingPaste) return "saving";
  if (hasSavedAudio) return "saved";
  if (pasteDirty) return "local-only";
  return "empty";
}

/** Map a persistence status to user-facing copy + tone. Honest by construction. */
export function captureStatusView(status: CapturePersistenceStatus): CaptureStatusViewModel {
  switch (status) {
    case "empty":
      return {
        status, tone: "neutral", canSafelyLeave: true, retryable: false,
        title: "Nothing captured yet",
        description: "Record, upload, or paste your speech to get started.",
      };
    case "local-only":
      return {
        status, tone: "warning", canSafelyLeave: false, retryable: false,
        title: "Not saved yet",
        description: "Your speech is stored only in this browser. Continue to save it before leaving.",
      };
    case "uploading":
      return {
        status, tone: "info", canSafelyLeave: false, retryable: false,
        title: "Uploading…",
        description: "Uploading your recording. Keep this page open.",
      };
    case "saving":
      return {
        status, tone: "info", canSafelyLeave: false, retryable: false,
        title: "Saving…",
        description: "Saving your speech text. Keep this page open.",
      };
    case "saved":
      return {
        status, tone: "success", canSafelyLeave: true, retryable: false,
        title: "Saved to Dissio",
        description: "Your speech is saved. You can analyze it now.",
      };
    case "analysis-starting":
      return {
        status, tone: "info", canSafelyLeave: false, retryable: false,
        title: "Starting analysis…",
        description: "Your speech is saved. Starting analysis…",
      };
    case "analysis-running":
      return {
        status, tone: "info", canSafelyLeave: true, retryable: false,
        title: "Analyzing your speech",
        description: "Your speech is saved. Keep this page open for the fastest path to your report — or return to this speech later to reconnect.",
      };
    case "analysis-failed":
      return {
        status, tone: "error", canSafelyLeave: true, retryable: true,
        title: "Analysis didn’t start",
        description: "Your recording is safe, but analysis did not finish. Retry without recording again.",
      };
    case "error":
      return {
        status, tone: "error", canSafelyLeave: true, retryable: true,
        title: "Something needs your attention",
        description: "There was a problem with this step. Check the message and try again.",
      };
  }
}

/** Whether to warn before the student navigates away (unsaved work at risk). */
export function shouldWarnBeforeLeaving(status: CapturePersistenceStatus): boolean {
  return status === "local-only" || status === "uploading" || status === "saving";
}
