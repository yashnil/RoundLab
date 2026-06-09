import type { AnalysisJob, JobStatus } from "@/types";

export const JOB_STEP_LABELS: Record<string, string> = {
  transcribing: "Transcribing audio…",
  extracting_flow: "Extracting arguments…",
  generating_feedback: "Generating coach feedback…",
  generating_drills: "Building practice drills…",
  finalizing: "Finalizing report…",
};

export function getJobStepLabel(job: AnalysisJob): string {
  if (job.current_step && JOB_STEP_LABELS[job.current_step]) {
    return JOB_STEP_LABELS[job.current_step];
  }
  if (job.status === "queued") return "Queued for analysis…";
  if (job.status === "running") return "Analyzing speech…";
  if (job.status === "succeeded") return "Analysis complete";
  if (job.status === "failed") return "Analysis failed";
  if (job.status === "cancelled") return "Cancelled";
  return "Analyzing…";
}

const ERROR_CODE_MESSAGES: Record<string, string> = {
  no_audio: "No audio found for this speech. Upload audio and try again.",
  transcription_failed:
    "Audio transcription failed. Check that your recording is clear and try again.",
  transcript_too_short:
    "Recording is too short to analyze. Record at least 30 seconds.",
  extraction_failed:
    "Could not extract arguments from the transcript. Try re-recording.",
  feedback_failed:
    "Feedback generation failed. This is usually a temporary error — retry.",
  speech_not_found: "Speech not found. It may have been deleted.",
  unexpected_error: "An unexpected error occurred. Please retry.",
};

export function getJobFailureMessage(job: AnalysisJob): string {
  if (job.error_code && ERROR_CODE_MESSAGES[job.error_code]) {
    return ERROR_CODE_MESSAGES[job.error_code];
  }
  return job.error_message ?? "Analysis failed. Please retry.";
}

export type AnalysisRecoveryState =
  | { type: "idle" }
  | { type: "in_progress"; job: AnalysisJob }
  | { type: "failed"; job: AnalysisJob }
  | { type: "done" };

export function deriveAnalysisRecoveryState(
  jobs: AnalysisJob[],
  speechStatus: string,
): AnalysisRecoveryState {
  if (speechStatus === "done") return { type: "done" };

  const active = jobs.find(
    (j) => j.status === "running" || j.status === "queued",
  );
  if (active) return { type: "in_progress", job: active };

  const latest = jobs[0];
  if (latest?.status === "failed") return { type: "failed", job: latest };

  if (speechStatus === "error" && latest) return { type: "failed", job: latest };

  return { type: "idle" };
}

export function isJobActive(status: JobStatus): boolean {
  return status === "queued" || status === "running";
}
