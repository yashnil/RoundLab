import {
  getJobStepLabel,
  getJobFailureMessage,
  deriveAnalysisRecoveryState,
  isJobActive,
  JOB_STEP_LABELS,
} from "@/lib/jobHelpers";
import type { AnalysisJob } from "@/types";

function makeJob(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    id: "job-1",
    user_id: "user-1",
    speech_id: "speech-1",
    job_type: "speech_analysis",
    status: "queued",
    current_step: null,
    progress: null,
    error_message: null,
    error_code: null,
    result_json: null,
    attempt_count: 1,
    started_at: null,
    completed_at: null,
    created_at: "2026-06-09T00:00:00Z",
    updated_at: "2026-06-09T00:00:00Z",
    ...overrides,
  };
}

// ── getJobStepLabel ────────────────────────────────────────────────────────────

describe("getJobStepLabel", () => {
  it("returns step label from JOB_STEP_LABELS when current_step matches", () => {
    const job = makeJob({ status: "running", current_step: "transcribing" });
    expect(getJobStepLabel(job)).toBe(JOB_STEP_LABELS["transcribing"]);
  });

  it("returns step label for extracting_flow", () => {
    const job = makeJob({ status: "running", current_step: "extracting_flow" });
    expect(getJobStepLabel(job)).toBe(JOB_STEP_LABELS["extracting_flow"]);
  });

  it("falls back to status label when current_step is null and status is queued", () => {
    const job = makeJob({ status: "queued", current_step: null });
    expect(getJobStepLabel(job)).toBe("Queued for analysis…");
  });

  it("falls back to status label when current_step is null and status is running", () => {
    const job = makeJob({ status: "running", current_step: null });
    expect(getJobStepLabel(job)).toBe("Analyzing speech…");
  });

  it("returns succeeded label for succeeded jobs", () => {
    const job = makeJob({ status: "succeeded" });
    expect(getJobStepLabel(job)).toBe("Analysis complete");
  });

  it("returns failed label for failed jobs", () => {
    const job = makeJob({ status: "failed" });
    expect(getJobStepLabel(job)).toBe("Analysis failed");
  });

  it("returns a fallback label for unknown current_step", () => {
    const job = makeJob({ status: "running", current_step: "unknown_step" });
    expect(getJobStepLabel(job)).toBe("Analyzing speech…");
  });
});

// ── getJobFailureMessage ───────────────────────────────────────────────────────

describe("getJobFailureMessage", () => {
  it("returns mapped message for known error_code", () => {
    const job = makeJob({ status: "failed", error_code: "no_audio" });
    expect(getJobFailureMessage(job)).toContain("No audio");
  });

  it("returns mapped message for transcription_failed", () => {
    const job = makeJob({ status: "failed", error_code: "transcription_failed" });
    expect(getJobFailureMessage(job)).toContain("transcription failed");
  });

  it("falls back to error_message when code is unknown", () => {
    const job = makeJob({ status: "failed", error_code: "custom_code", error_message: "Custom error." });
    expect(getJobFailureMessage(job)).toBe("Custom error.");
  });

  it("returns default when both error_code and error_message are null", () => {
    const job = makeJob({ status: "failed", error_code: null, error_message: null });
    expect(getJobFailureMessage(job)).toContain("retry");
  });
});

// ── deriveAnalysisRecoveryState ────────────────────────────────────────────────

describe("deriveAnalysisRecoveryState", () => {
  it("returns done when speechStatus is done regardless of jobs", () => {
    const jobs = [makeJob({ status: "failed" })];
    expect(deriveAnalysisRecoveryState(jobs, "done").type).toBe("done");
  });

  it("returns in_progress when there is a running job", () => {
    const running = makeJob({ status: "running" });
    const result = deriveAnalysisRecoveryState([running], "analyzing");
    expect(result.type).toBe("in_progress");
    if (result.type === "in_progress") expect(result.job.id).toBe(running.id);
  });

  it("returns in_progress when there is a queued job", () => {
    const queued = makeJob({ status: "queued" });
    const result = deriveAnalysisRecoveryState([queued], "pending");
    expect(result.type).toBe("in_progress");
  });

  it("returns failed when most recent job is failed and speech is error", () => {
    const failed = makeJob({ status: "failed" });
    const result = deriveAnalysisRecoveryState([failed], "error");
    expect(result.type).toBe("failed");
    if (result.type === "failed") expect(result.job.id).toBe(failed.id);
  });

  it("returns failed when most recent job status is failed regardless of speech status", () => {
    const failed = makeJob({ status: "failed" });
    const result = deriveAnalysisRecoveryState([failed], "pending");
    expect(result.type).toBe("failed");
  });

  it("prefers running job over failed when both exist", () => {
    const failed = makeJob({ id: "j1", status: "failed" });
    const running = makeJob({ id: "j2", status: "running" });
    const result = deriveAnalysisRecoveryState([running, failed], "analyzing");
    expect(result.type).toBe("in_progress");
    if (result.type === "in_progress") expect(result.job.id).toBe("j2");
  });

  it("returns idle when no jobs and speech is pending", () => {
    expect(deriveAnalysisRecoveryState([], "pending").type).toBe("idle");
  });
});

// ── isJobActive ────────────────────────────────────────────────────────────────

describe("isJobActive", () => {
  it("returns true for queued", () => expect(isJobActive("queued")).toBe(true));
  it("returns true for running", () => expect(isJobActive("running")).toBe(true));
  it("returns false for succeeded", () => expect(isJobActive("succeeded")).toBe(false));
  it("returns false for failed", () => expect(isJobActive("failed")).toBe(false));
  it("returns false for cancelled", () => expect(isJobActive("cancelled")).toBe(false));
});
