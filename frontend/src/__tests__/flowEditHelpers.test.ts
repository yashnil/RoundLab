import {
  addArgument,
  deleteArgument,
  duplicateArgument,
  initEditArgs,
  isFlowCorrectedAndNeedsRegen,
  updateArgument,
} from "@/lib/flowEditHelpers";
import type { ArgumentItem, ArgumentMap, FeedbackReport } from "@/types";

// ── Fixtures ────────────────────────────────────────────────────────────────

function makeArg(overrides?: Partial<ArgumentItem>): ArgumentItem {
  return {
    id: "arg_1",
    label: "Contention 1",
    claim: "Claim text",
    warrant: "Warrant text",
    evidence: "Evidence text",
    impact: "Impact text",
    argument_type: "offense",
    issues: ["missing_warrant"],
    confidence: 0.8,
    ...overrides,
  };
}

function makeArgMap(overrides?: Partial<ArgumentMap>): ArgumentMap {
  return {
    id: "map-1",
    speech_id: "speech-1",
    arguments: [makeArg()],
    created_at: "2026-06-09T00:00:00Z",
    source_type: "ai",
    user_corrected_at: null,
    ...overrides,
  };
}

function makeFeedback(overrides?: Partial<FeedbackReport>): FeedbackReport {
  return {
    id: "fb-1",
    speech_id: "speech-1",
    overall_score: 70,
    scores: { clash: 14, weighing: 14, extensions: 14, drops: 14, judge_adaptation: 14 },
    summary: "Test",
    strengths: [],
    weaknesses: [],
    raw_feedback: null,
    created_at: "2026-06-09T00:00:00Z",
    ...overrides,
  };
}

// ── initEditArgs ─────────────────────────────────────────────────────────────

describe("initEditArgs", () => {
  it("returns a deep copy — mutating the copy does not affect the original", () => {
    const original = [makeArg({ issues: ["missing_warrant"] })];
    const copy = initEditArgs(original);

    copy[0].label = "Changed";
    copy[0].issues.push("no_weighing");

    expect(original[0].label).toBe("Contention 1");
    expect(original[0].issues).toHaveLength(1);
  });

  it("preserves all field values", () => {
    const original = [makeArg()];
    const copy = initEditArgs(original);
    expect(copy[0]).toMatchObject({
      id: "arg_1",
      label: "Contention 1",
      claim: "Claim text",
      warrant: "Warrant text",
      impact: "Impact text",
      argument_type: "offense",
      confidence: 0.8,
    });
  });
});

// ── addArgument ──────────────────────────────────────────────────────────────

describe("addArgument", () => {
  it("appends a blank argument", () => {
    const args = [makeArg()];
    const result = addArgument(args);
    expect(result).toHaveLength(2);
    expect(result[1].label).toBe("");
    expect(result[1].claim).toBe("");
    expect(result[1].id).toBeNull();
  });

  it("does not mutate the original array", () => {
    const args = [makeArg()];
    addArgument(args);
    expect(args).toHaveLength(1);
  });

  it("new argument has offense type by default", () => {
    const result = addArgument([]);
    expect(result[0].argument_type).toBe("offense");
  });
});

// ── deleteArgument ───────────────────────────────────────────────────────────

describe("deleteArgument", () => {
  it("removes the argument at the given index", () => {
    const args = [makeArg({ label: "A" }), makeArg({ label: "B" }), makeArg({ label: "C" })];
    const result = deleteArgument(args, 1);
    expect(result).toHaveLength(2);
    expect(result[0].label).toBe("A");
    expect(result[1].label).toBe("C");
  });

  it("does not mutate the original array", () => {
    const args = [makeArg({ label: "A" }), makeArg({ label: "B" })];
    deleteArgument(args, 0);
    expect(args).toHaveLength(2);
  });

  it("removes the only argument (caller guards against this)", () => {
    const args = [makeArg()];
    const result = deleteArgument(args, 0);
    expect(result).toHaveLength(0);
  });
});

// ── duplicateArgument ────────────────────────────────────────────────────────

describe("duplicateArgument", () => {
  it("inserts a copy immediately after the source", () => {
    const args = [makeArg({ label: "A" }), makeArg({ label: "B" })];
    const result = duplicateArgument(args, 0);
    expect(result).toHaveLength(3);
    expect(result[0].label).toBe("A");
    expect(result[1].label).toBe("A"); // copy
    expect(result[2].label).toBe("B");
  });

  it("duplicate has id set to null", () => {
    const args = [makeArg({ id: "arg_1" })];
    const result = duplicateArgument(args, 0);
    expect(result[1].id).toBeNull();
  });

  it("duplicate issues array is independent", () => {
    const args = [makeArg({ issues: ["missing_warrant"] })];
    const result = duplicateArgument(args, 0);
    result[1].issues.push("no_weighing");
    expect(result[0].issues).toHaveLength(1);
  });

  it("does not mutate the original array", () => {
    const args = [makeArg()];
    duplicateArgument(args, 0);
    expect(args).toHaveLength(1);
  });
});

// ── updateArgument ───────────────────────────────────────────────────────────

describe("updateArgument", () => {
  it("merges changes into the argument at the given index", () => {
    const args = [makeArg({ label: "Old" }), makeArg({ label: "Other" })];
    const result = updateArgument(args, 0, { label: "New", claim: "New claim" });
    expect(result[0].label).toBe("New");
    expect(result[0].claim).toBe("New claim");
    expect(result[0].warrant).toBe("Warrant text"); // unchanged
    expect(result[1].label).toBe("Other"); // sibling unchanged
  });

  it("does not mutate the original array", () => {
    const args = [makeArg({ label: "Old" })];
    updateArgument(args, 0, { label: "New" });
    expect(args[0].label).toBe("Old");
  });
});

// ── isFlowCorrectedAndNeedsRegen ─────────────────────────────────────────────

describe("isFlowCorrectedAndNeedsRegen", () => {
  it("returns false when argMap is null", () => {
    expect(isFlowCorrectedAndNeedsRegen(null, makeFeedback())).toBe(false);
  });

  it("returns false when feedback is null", () => {
    expect(isFlowCorrectedAndNeedsRegen(makeArgMap(), null)).toBe(false);
  });

  it("returns false when source_type is 'ai'", () => {
    const argMap = makeArgMap({ source_type: "ai", user_corrected_at: "2026-06-09T10:00:00Z" });
    expect(isFlowCorrectedAndNeedsRegen(argMap, makeFeedback())).toBe(false);
  });

  it("returns false when user_corrected_at is null", () => {
    const argMap = makeArgMap({ source_type: "user_corrected", user_corrected_at: null });
    expect(isFlowCorrectedAndNeedsRegen(argMap, makeFeedback())).toBe(false);
  });

  it("returns true when corrected but never regenerated", () => {
    const argMap = makeArgMap({
      source_type: "user_corrected",
      user_corrected_at: "2026-06-09T10:00:00Z",
    });
    const feedback = makeFeedback({ raw_feedback: null });
    expect(isFlowCorrectedAndNeedsRegen(argMap, feedback)).toBe(true);
  });

  it("returns true when correction is newer than last regen", () => {
    const argMap = makeArgMap({
      source_type: "user_corrected",
      user_corrected_at: "2026-06-09T12:00:00Z",
    });
    const feedback = makeFeedback({
      raw_feedback: {
        flow_correction_regenerated_at: "2026-06-09T10:00:00Z",
      },
    });
    expect(isFlowCorrectedAndNeedsRegen(argMap, feedback)).toBe(true);
  });

  it("returns false when coaching was regenerated after the correction", () => {
    const argMap = makeArgMap({
      source_type: "user_corrected",
      user_corrected_at: "2026-06-09T10:00:00Z",
    });
    const feedback = makeFeedback({
      raw_feedback: {
        flow_correction_regenerated_at: "2026-06-09T12:00:00Z",
      },
    });
    expect(isFlowCorrectedAndNeedsRegen(argMap, feedback)).toBe(false);
  });

  it("returns false when correction and regen timestamps are equal", () => {
    const ts = "2026-06-09T10:00:00Z";
    const argMap = makeArgMap({ source_type: "user_corrected", user_corrected_at: ts });
    const feedback = makeFeedback({
      raw_feedback: { flow_correction_regenerated_at: ts },
    });
    expect(isFlowCorrectedAndNeedsRegen(argMap, feedback)).toBe(false);
  });
});
