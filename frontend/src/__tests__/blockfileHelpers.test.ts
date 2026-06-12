import {
  blockEntryTypeLabel,
  coverageStatusLabel,
  coverageStatusClass,
  coverageStatusBadgeStyle,
  documentRoleLabel,
  deriveBlockReadiness,
  deriveNextBestAction,
  workoutStepBlockfileLabel,
} from "@/lib/blockfileHelpers";
import type {
  BlockCoverageResponse, BlockCoverageCheck, Workout, WorkoutStep,
} from "@/types";

// ── Factories ─────────────────────────────────────────────────────────────────

function makeCoverageCheck(
  status: BlockCoverageCheck["status"],
  claim_text = "Free speech claim.",
): BlockCoverageCheck {
  return {
    id: "check-1",
    user_id: "u-1",
    speech_id: "sp-1",
    argument_id: null,
    claim_text,
    check_type: "block",
    status,
    matched_block_entry_ids: [],
    top_similarity: status === "covered" ? 0.72 : status === "missing" ? 0.22 : null,
    rationale: "Test rationale",
    missing_piece: status !== "covered" ? "Add warrant." : null,
    suggested_drill_json: null,
    created_at: "2026-06-09T10:00:00Z",
    updated_at: "2026-06-09T10:00:00Z",
  };
}

function makeCoverage(overrides: Partial<BlockCoverageResponse> = {}): BlockCoverageResponse {
  return {
    speech_id: "sp-1",
    checks: [makeCoverageCheck("covered"), makeCoverageCheck("missing")],
    covered_count: 1,
    partially_covered_count: 0,
    missing_count: 1,
    no_available_block_count: 0,
    total_block_entries: 5,
    ...overrides,
  };
}

function makeWorkout(status: Workout["status"] = "in_progress"): Workout {
  return {
    id: "w-1",
    user_id: "u-1",
    speech_id: "sp-1",
    title: "Workout",
    workout_type: "tournament_prep",
    status,
    workout_json: {
      steps: [],
      re_record_goal: "Improve warrant clarity.",
      coach_note: "Focus on warrants.",
      generated_from: {},
    },
    created_at: "2026-06-09T10:00:00Z",
    updated_at: "2026-06-09T10:00:00Z",
  };
}

function makeWorkoutStep(overrides: Partial<WorkoutStep> = {}): WorkoutStep {
  return {
    id: "s-1",
    title: "Test step",
    category: "argument",
    focus: "warranting",
    estimated_minutes: 5,
    source: "feedback",
    problem: "Thin warrant",
    instruction: "Add mechanism",
    success_criteria: "Warrant answers 'how'",
    completed: false,
    ...overrides,
  };
}

// ── blockEntryTypeLabel ───────────────────────────────────────────────────────

describe("blockEntryTypeLabel", () => {
  it("maps all known types", () => {
    expect(blockEntryTypeLabel("block")).toBe("Block");
    expect(blockEntryTypeLabel("frontline")).toBe("Frontline");
    expect(blockEntryTypeLabel("answer")).toBe("Answer");
    expect(blockEntryTypeLabel("turn")).toBe("Turn");
    expect(blockEntryTypeLabel("defense")).toBe("Defense");
    expect(blockEntryTypeLabel("weighing")).toBe("Weighing");
    expect(blockEntryTypeLabel("overview")).toBe("Overview");
    expect(blockEntryTypeLabel("unknown")).toBe("Entry");
  });

  it("passes unknown types through", () => {
    expect(blockEntryTypeLabel("custom")).toBe("custom");
  });
});

// ── coverageStatusLabel ───────────────────────────────────────────────────────

describe("coverageStatusLabel", () => {
  it("maps all statuses", () => {
    expect(coverageStatusLabel("covered")).toBe("Covered");
    expect(coverageStatusLabel("partially_covered")).toBe("Partially covered");
    expect(coverageStatusLabel("missing")).toBe("Missing");
    expect(coverageStatusLabel("no_available_block")).toBe("No block uploaded");
  });

  it("passes unknown through", () => {
    expect(coverageStatusLabel("other")).toBe("other");
  });
});

// ── coverageStatusClass ───────────────────────────────────────────────────────

describe("coverageStatusClass", () => {
  it("covered is green", () => {
    expect(coverageStatusClass("covered")).toContain("ok");
  });
  it("missing is red/danger", () => {
    expect(coverageStatusClass("missing")).toContain("danger");
  });
  it("partially_covered is warn", () => {
    expect(coverageStatusClass("partially_covered")).toContain("warn");
  });
  it("no_available_block is faint", () => {
    expect(coverageStatusClass("no_available_block")).toContain("faint");
  });
});

// ── coverageStatusBadgeStyle ──────────────────────────────────────────────────

describe("coverageStatusBadgeStyle", () => {
  it("returns an object with background, border, color", () => {
    const style = coverageStatusBadgeStyle("covered");
    expect(style).toHaveProperty("background");
    expect(style).toHaveProperty("border");
    expect(style).toHaveProperty("color");
  });

  it("each status returns distinct color", () => {
    const covered  = coverageStatusBadgeStyle("covered").color;
    const missing  = coverageStatusBadgeStyle("missing").color;
    const partial  = coverageStatusBadgeStyle("partially_covered").color;
    const noBlock  = coverageStatusBadgeStyle("no_available_block").color;
    expect(new Set([covered, missing, partial, noBlock]).size).toBe(4);
  });
});

// ── documentRoleLabel ─────────────────────────────────────────────────────────

describe("documentRoleLabel", () => {
  it("maps all document roles", () => {
    expect(documentRoleLabel("evidence")).toBe("Evidence");
    expect(documentRoleLabel("case")).toBe("Case file");
    expect(documentRoleLabel("blockfile")).toBe("Blockfile");
    expect(documentRoleLabel("frontline")).toBe("Frontline");
    expect(documentRoleLabel("mixed")).toBe("Mixed");
  });

  it("returns Evidence for null/undefined", () => {
    expect(documentRoleLabel(null)).toBe("Evidence");
    expect(documentRoleLabel(undefined)).toBe("Evidence");
  });
});

// ── deriveBlockReadiness ──────────────────────────────────────────────────────

describe("deriveBlockReadiness", () => {
  it("returns no coverage when coverage is null", () => {
    const r = deriveBlockReadiness(3, null);
    expect(r.hasCoverage).toBe(false);
    expect(r.totalEntries).toBe(3);
    expect(r.strongestGap).toBeDefined();
  });

  it("reflects coverage counts", () => {
    const coverage = makeCoverage();
    const r = deriveBlockReadiness(5, coverage);
    expect(r.coveredCount).toBe(1);
    expect(r.missingCount).toBe(1);
    expect(r.hasCoverage).toBe(true);
    expect(r.totalEntries).toBe(5);
  });

  it("missing status produces strongest gap about missing block", () => {
    const coverage = makeCoverage({ checks: [makeCoverageCheck("missing", "Section 230 claim.")] });
    const r = deriveBlockReadiness(5, coverage);
    expect(r.strongestGap).toContain("Missing");
  });

  it("partial status gap when no missing", () => {
    const coverage = makeCoverage({
      checks: [makeCoverageCheck("partially_covered", "Privacy claim.")],
      missing_count: 0,
    });
    const r = deriveBlockReadiness(5, coverage);
    expect(r.strongestGap).toContain("Incomplete");
  });

  it("no gap when all covered", () => {
    const coverage = makeCoverage({
      checks: [makeCoverageCheck("covered"), makeCoverageCheck("covered")],
      covered_count: 2,
      missing_count: 0,
    });
    const r = deriveBlockReadiness(5, coverage);
    expect(r.strongestGap).toBeNull();
  });
});

// ── deriveNextBestAction ──────────────────────────────────────────────────────

describe("deriveNextBestAction", () => {
  const base = {
    drillsIncomplete: 0,
    hasEvidenceRisk: false,
    hasMissingBlocks: false,
    hasBlockEntries: false,
    hasFeedback: true,
    speechStatus: "done",
    speechId: "sp-1",
  };

  it("active workout returns continue_workout", () => {
    const action = deriveNextBestAction({ ...base, workout: makeWorkout("in_progress") });
    expect(action.type).toBe("continue_workout");
  });

  it("completed workout skips to drills", () => {
    const action = deriveNextBestAction({
      ...base,
      workout: makeWorkout("completed"),
      drillsIncomplete: 2,
    });
    expect(action.type).toBe("complete_drill");
  });

  it("no workout + incomplete drills returns complete_drill", () => {
    const action = deriveNextBestAction({ ...base, workout: null, drillsIncomplete: 2 });
    expect(action.type).toBe("complete_drill");
  });

  it("missing blocks returns check_block_coverage", () => {
    const action = deriveNextBestAction({ ...base, workout: null, hasMissingBlocks: true });
    expect(action.type).toBe("check_block_coverage");
  });

  it("evidence risk returns fix_evidence", () => {
    const action = deriveNextBestAction({ ...base, workout: null, hasEvidenceRisk: true });
    expect(action.type).toBe("fix_evidence");
  });

  it("no blocks and has feedback returns upload_blockfile", () => {
    const action = deriveNextBestAction({ ...base, workout: null, hasBlockEntries: false });
    expect(action.type).toBe("upload_blockfile");
  });

  it("has blocks and everything done returns rerecord", () => {
    const action = deriveNextBestAction({ ...base, workout: null, hasBlockEntries: true });
    expect(action.type).toBe("rerecord");
  });

  it("missing blocks is higher priority than evidence risk", () => {
    const action = deriveNextBestAction({
      ...base,
      workout: null,
      hasMissingBlocks: true,
      hasEvidenceRisk: true,
    });
    expect(action.type).toBe("check_block_coverage");
  });
});

// ── workoutStepBlockfileLabel ─────────────────────────────────────────────────

describe("workoutStepBlockfileLabel", () => {
  it("returns Block Application for blockfile category", () => {
    const step = makeWorkoutStep({ category: "blockfile" });
    expect(workoutStepBlockfileLabel(step)).toBe("Block Application");
  });

  it("returns category string for other categories", () => {
    const step = makeWorkoutStep({ category: "argument" });
    expect(workoutStepBlockfileLabel(step)).toBe("argument");
  });
});
