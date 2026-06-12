import type {
  BlockEntry,
  BlockCoverageCheck,
  BlockCoverageResponse,
  BlockCoverageStatus,
  BlockEntryType,
  DocumentRole,
  Workout,
  WorkoutStep,
} from "@/types";

// ── Entry type labels ─────────────────────────────────────────────────────────

export function blockEntryTypeLabel(type: BlockEntryType | string): string {
  const labels: Record<string, string> = {
    block:      "Block",
    frontline:  "Frontline",
    answer:     "Answer",
    turn:       "Turn",
    defense:    "Defense",
    weighing:   "Weighing",
    overview:   "Overview",
    unknown:    "Entry",
  };
  return labels[type] ?? type;
}

// ── Coverage status labels + classes ─────────────────────────────────────────

export function coverageStatusLabel(status: BlockCoverageStatus | string): string {
  const labels: Record<string, string> = {
    covered:            "Covered",
    partially_covered:  "Partially covered",
    missing:            "Missing",
    no_available_block: "No block uploaded",
  };
  return labels[status] ?? status;
}

export function coverageStatusClass(status: BlockCoverageStatus | string): string {
  const classes: Record<string, string> = {
    covered:            "text-ok",
    partially_covered:  "text-warn",
    missing:            "text-danger",
    no_available_block: "text-ink-faint",
  };
  return classes[status] ?? "text-ink-subtle";
}

export function coverageStatusBadgeStyle(status: BlockCoverageStatus | string): {
  background: string;
  border: string;
  color: string;
} {
  const map: Record<string, { background: string; border: string; color: string }> = {
    covered: {
      background: "oklch(0.620 0.170 145 / 0.10)",
      border: "1px solid oklch(0.620 0.170 145 / 0.28)",
      color: "var(--color-ok)",
    },
    partially_covered: {
      background: "oklch(0.760 0.160 60 / 0.10)",
      border: "1px solid oklch(0.760 0.160 60 / 0.30)",
      color: "var(--color-warn)",
    },
    missing: {
      background: "oklch(0.620 0.215 25 / 0.08)",
      border: "1px solid oklch(0.620 0.215 25 / 0.25)",
      color: "var(--color-danger)",
    },
    no_available_block: {
      background: "oklch(0.420 0 0 / 0.06)",
      border: "1px solid oklch(0.420 0 0 / 0.15)",
      color: "var(--color-ink-faint)",
    },
  };
  return map[status] ?? map.no_available_block;
}

// ── Document role labels ──────────────────────────────────────────────────────

export function documentRoleLabel(role: DocumentRole | string | null | undefined): string {
  if (!role) return "Evidence";
  const labels: Record<string, string> = {
    evidence:  "Evidence",
    case:      "Case file",
    blockfile: "Blockfile",
    frontline: "Frontline",
    mixed:     "Mixed",
  };
  return labels[role] ?? role;
}

// ── Readiness summary ─────────────────────────────────────────────────────────

export interface BlockReadinessSummary {
  totalEntries: number;
  coveredCount: number;
  partialCount: number;
  missingCount: number;
  noBlockCount: number;
  hasCoverage: boolean;
  strongestGap: string | null;
}

export function deriveBlockReadiness(
  totalEntries: number,
  coverage: BlockCoverageResponse | null,
): BlockReadinessSummary {
  if (!coverage) {
    return {
      totalEntries,
      coveredCount: 0,
      partialCount: 0,
      missingCount: 0,
      noBlockCount: 0,
      hasCoverage: false,
      strongestGap: totalEntries > 0 ? "Run block coverage to find gaps" : "No blocks uploaded",
    };
  }

  const strongestGap = (() => {
    const missing = coverage.checks.find((c) => c.status === "missing");
    if (missing) return `Missing block: ${missing.claim_text.slice(0, 80)}`;
    const partial = coverage.checks.find((c) => c.status === "partially_covered");
    if (partial) return `Incomplete response: ${partial.claim_text.slice(0, 80)}`;
    const noBlock = coverage.checks.find((c) => c.status === "no_available_block");
    if (noBlock) return "Some arguments have no uploaded block";
    return null;
  })();

  return {
    totalEntries,
    coveredCount: coverage.covered_count,
    partialCount: coverage.partially_covered_count,
    missingCount: coverage.missing_count,
    noBlockCount: coverage.no_available_block_count,
    hasCoverage: coverage.checks.length > 0,
    strongestGap,
  };
}

// ── Next best action ──────────────────────────────────────────────────────────

export type NextBestActionType =
  | "continue_workout"
  | "complete_drill"
  | "check_block_coverage"
  | "fix_evidence"
  | "rerecord"
  | "generate_workout"
  | "upload_blockfile";

export interface NextBestAction {
  type: NextBestActionType;
  label: string;
  description: string;
  href?: string;
}

export function deriveNextBestAction(opts: {
  workout: Workout | null | undefined;
  drillsIncomplete: number;
  hasEvidenceRisk: boolean;
  hasMissingBlocks: boolean;
  hasBlockEntries: boolean;
  hasFeedback: boolean;
  speechStatus: string | undefined;
  speechId: string;
}): NextBestAction {
  const {
    workout, drillsIncomplete, hasEvidenceRisk,
    hasMissingBlocks, hasBlockEntries, hasFeedback,
    speechStatus, speechId,
  } = opts;

  // 1. Active workout
  if (workout && workout.status !== "completed") {
    return {
      type: "continue_workout",
      label: "Continue workout",
      description: "Pick up your tournament prep where you left off.",
      href: `/speech/${speechId}#workout`,
    };
  }

  // 2. Incomplete drills
  if (drillsIncomplete > 0) {
    return {
      type: "complete_drill",
      label: `Complete drill (${drillsIncomplete} remaining)`,
      description: "Finish a practice drill to improve your targeted skill.",
      href: `/speech/${speechId}#drills`,
    };
  }

  // 3. Missing block coverage
  if (hasMissingBlocks) {
    return {
      type: "check_block_coverage",
      label: "Fix block gap",
      description: "A relevant uploaded block wasn't used in your rebuttal.",
      href: `/speech/${speechId}#block-coverage`,
    };
  }

  // 4. Evidence risk
  if (hasEvidenceRisk) {
    return {
      type: "fix_evidence",
      label: "Fix evidence alignment",
      description: "At least one claim doesn't match your uploaded evidence.",
      href: `/speech/${speechId}#evidence-support`,
    };
  }

  // 5. No blocks uploaded
  if (!hasBlockEntries && hasFeedback) {
    return {
      type: "upload_blockfile",
      label: "Upload a blockfile",
      description: "Add opponent argument responses to check your coverage.",
      href: "/evidence",
    };
  }

  // 6. Default: re-record
  return {
    type: "rerecord",
    label: "Re-record speech",
    description: "Apply your feedback improvements in a new recording.",
    href: `/speech/${speechId}`,
  };
}

// ── Workout step blockfile label ──────────────────────────────────────────────

export function workoutStepBlockfileLabel(step: WorkoutStep): string {
  if (step.category === "blockfile") return "Block Application";
  return step.category;
}
