/**
 * Honest processing-stage model.
 *
 * Dissio's backend exposes a coarse job status (queued/running/succeeded/
 * failed), not per-category telemetry. So we present a small, truthful set of
 * high-level stages and list the analysis CATEGORIES as an *explanatory* view —
 * never marking a category complete from elapsed time, never a fake percentage.
 */

export type ProcStageStatus = "done" | "active" | "upcoming" | "failed";

export interface ProcStage {
  id: "input" | "analysis" | "assembling" | "ready";
  label: string;
  status: ProcStageStatus;
}

/** Coarse job status mirrored from the analysis hook. */
export type ProcJobStatus = "queued" | "running" | "succeeded" | "failed" | null;

export interface ProcessingStageInput {
  jobStatus: ProcJobStatus;
  /** True once the report data (feedback) has loaded. */
  hasReport: boolean;
  /** True when analysis failed (and not recovered). */
  failed: boolean;
}

/**
 * The categories Dissio examines during "analysis running". Shown as an
 * explanatory checklist — they are NOT independently completed in the UI.
 */
export const ANALYSIS_CATEGORIES = [
  "Argument structure",
  "Evidence use",
  "Clash",
  "Weighing",
  "Judge adaptation",
  "Delivery",
  "Drill opportunities",
] as const;

export function deriveProcessingStages(input: ProcessingStageInput): ProcStage[] {
  const { jobStatus, hasReport, failed } = input;

  // Input is always secured by the time processing renders.
  const inputStage: ProcStage = { id: "input", label: "Input secured", status: "done" };

  if (failed) {
    return [
      inputStage,
      { id: "analysis", label: "Analysis running", status: "failed" },
      { id: "assembling", label: "Report assembling", status: "upcoming" },
      { id: "ready", label: "Report ready", status: "upcoming" },
    ];
  }

  if (hasReport) {
    return [
      inputStage,
      { id: "analysis", label: "Analysis running", status: "done" },
      { id: "assembling", label: "Report assembling", status: "done" },
      { id: "ready", label: "Report ready", status: "done" },
    ];
  }

  const analysisActive = jobStatus === "queued" || jobStatus === "running";
  const analysisDone = jobStatus === "succeeded";

  return [
    inputStage,
    {
      id: "analysis",
      label: "Analysis running",
      status: analysisDone ? "done" : analysisActive ? "active" : "upcoming",
    },
    {
      id: "assembling",
      label: "Report assembling",
      status: analysisDone ? "active" : "upcoming",
    },
    { id: "ready", label: "Report ready", status: "upcoming" },
  ];
}

/** The current active (or failed) stage's label, for the live-region headline. */
export function processingHeadline(stages: ProcStage[]): string {
  const failed = stages.find((s) => s.status === "failed");
  if (failed) return "Analysis didn’t finish";
  const active = stages.find((s) => s.status === "active");
  if (active) return active.label;
  return stages.every((s) => s.status === "done") ? "Report ready" : "Preparing analysis";
}

/** Whether the timeline is in a terminal state (no further animation needed). */
export function isProcessingTerminal(stages: ProcStage[]): boolean {
  return stages.every((s) => s.status === "done") || stages.some((s) => s.status === "failed");
}
