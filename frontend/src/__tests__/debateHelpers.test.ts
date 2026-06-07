/**
 * Unit tests for debate helper pure functions.
 * Run with: npm test
 */

import {
  deriveLowestSkill,
  skillPercent,
  formatDuration,
  formatDrillTimeLimit,
  priorityToIssueKeyword,
  issueSeverityColor,
  ISSUE_TYPE_LABELS,
  getSpeechStatusConfig,
  getSpeechStatusLabel,
  getSpeechStatusColor,
  getPrimaryIssue,
  getAffectedArgumentLabels,
  mapIssueToDrillType,
  normalizeIssueType,
  normalizeSeverity,
} from "../lib/debateHelpers";

// ── deriveLowestSkill ──────────────────────────────────────────────────────────

describe("deriveLowestSkill", () => {
  it("returns the lowest scoring skill", () => {
    const result = deriveLowestSkill({
      clash: 15,
      weighing: 8,
      extensions: 12,
      drops: 16,
      judge_adaptation: 11,
    });
    expect(result?.key).toBe("weighing");
    expect(result?.value).toBe(8);
    expect(result?.label).toBe("Impact Weighing");
  });

  it("handles ties by returning first minimum", () => {
    const result = deriveLowestSkill({
      clash: 10,
      weighing: 10,
      extensions: 10,
      drops: 10,
      judge_adaptation: 10,
    });
    expect(result).not.toBeNull();
    expect(result?.value).toBe(10);
  });

  it("returns null for empty-ish skill averages", () => {
    // All skills are 0 — should still return one, not null
    const result = deriveLowestSkill({
      clash: 0,
      weighing: 0,
      extensions: 0,
      drops: 0,
      judge_adaptation: 0,
    });
    expect(result).not.toBeNull();
  });
});

// ── skillPercent ───────────────────────────────────────────────────────────────

describe("skillPercent", () => {
  it("converts 10/20 to 50%", () => {
    expect(skillPercent(10, 20)).toBe(50);
  });

  it("converts 20/20 to 100%", () => {
    expect(skillPercent(20, 20)).toBe(100);
  });

  it("clamps above-max values", () => {
    expect(skillPercent(25, 20)).toBe(100);
  });

  it("clamps below-zero values", () => {
    expect(skillPercent(-5, 20)).toBe(0);
  });
});

// ── formatDuration ─────────────────────────────────────────────────────────────

describe("formatDuration", () => {
  it("formats seconds-only", () => {
    expect(formatDuration(45)).toBe("45s");
  });

  it("formats minutes-only", () => {
    expect(formatDuration(120)).toBe("2m");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(90)).toBe("1m 30s");
  });

  it("returns — for negative", () => {
    expect(formatDuration(-1)).toBe("—");
  });

  it("returns — for NaN", () => {
    expect(formatDuration(NaN)).toBe("—");
  });

  it("formats 0 as 0s", () => {
    expect(formatDuration(0)).toBe("0s");
  });
});

// ── formatDrillTimeLimit ───────────────────────────────────────────────────────

describe("formatDrillTimeLimit", () => {
  it("returns — for null", () => {
    expect(formatDrillTimeLimit(null)).toBe("—");
  });

  it("returns — for undefined", () => {
    expect(formatDrillTimeLimit(undefined)).toBe("—");
  });

  it("formats 60s as 1m", () => {
    expect(formatDrillTimeLimit(60)).toBe("1m");
  });

  it("formats 90s as 1m 30s", () => {
    expect(formatDrillTimeLimit(90)).toBe("1m 30s");
  });
});

// ── priorityToIssueKeyword ─────────────────────────────────────────────────────

describe("priorityToIssueKeyword", () => {
  it("detects warrant keyword", () => {
    expect(priorityToIssueKeyword("Missing warrant on Contention 1")).toBe("warrant");
  });

  it("detects evidence keyword", () => {
    expect(priorityToIssueKeyword("Evidence is unsupported or vague")).toBe("evidence");
  });

  it("detects weighing keyword", () => {
    expect(priorityToIssueKeyword("Need to weigh impacts by magnitude")).toBe("weigh");
  });

  it("detects drop keyword", () => {
    expect(priorityToIssueKeyword("Dropped argument on opponent's offense")).toBe("drop");
  });

  it("returns null for unknown", () => {
    expect(priorityToIssueKeyword("General improvement needed")).toBeNull();
  });

  it("is case-insensitive", () => {
    expect(priorityToIssueKeyword("WARRANT CLARITY")).toBe("warrant");
  });
});

// ── issueSeverityColor ─────────────────────────────────────────────────────────

describe("issueSeverityColor", () => {
  it("high → danger", () => {
    expect(issueSeverityColor("high")).toBe("danger");
  });

  it("medium → warn", () => {
    expect(issueSeverityColor("medium")).toBe("warn");
  });

  it("low → ink-subtle", () => {
    expect(issueSeverityColor("low")).toBe("ink-subtle");
  });
});

// ── ISSUE_TYPE_LABELS ──────────────────────────────────────────────────────────

describe("ISSUE_TYPE_LABELS", () => {
  it("has labels for all known issue types", () => {
    const expectedTypes = [
      "missing_warrant",
      "weak_evidence",
      "unclear_impact",
      "no_weighing",
      "dropped_argument",
      "weak_extension",
      "no_clash",
      "new_argument",
      "organization",
      "delivery",
    ];
    expectedTypes.forEach((type) => {
      expect(ISSUE_TYPE_LABELS[type as keyof typeof ISSUE_TYPE_LABELS]).toBeDefined();
    });
  });
});

// ── getSpeechStatusConfig ──────────────────────────────────────────────────────

describe("getSpeechStatusConfig", () => {
  it("returns correct config for done", () => {
    const cfg = getSpeechStatusConfig("done");
    expect(cfg.label).toBe("Feedback ready");
    expect(cfg.badge).toBe("green");
    expect(cfg.isTerminal).toBe(true);
    expect(cfg.isProcessing).toBe(false);
  });

  it("returns correct config for analyzing", () => {
    const cfg = getSpeechStatusConfig("analyzing");
    expect(cfg.badge).toBe("amber");
    expect(cfg.isProcessing).toBe(true);
  });

  it("returns correct config for error", () => {
    const cfg = getSpeechStatusConfig("error");
    expect(cfg.badge).toBe("red");
    expect(cfg.isTerminal).toBe(true);
  });

  it("returns fallback for unknown status", () => {
    const cfg = getSpeechStatusConfig("mystery_status");
    expect(cfg.label).toBe("Unknown");
    expect(cfg.badge).toBe("default");
  });
});

describe("getSpeechStatusLabel", () => {
  it("returns label for known status", () => {
    expect(getSpeechStatusLabel("pending")).toBe("Pending");
    expect(getSpeechStatusLabel("done")).toBe("Feedback ready");
  });

  it("returns Unknown for unrecognized status", () => {
    expect(getSpeechStatusLabel("xyz")).toBe("Unknown");
  });
});

describe("getSpeechStatusColor", () => {
  it("maps done to ok", () => {
    expect(getSpeechStatusColor("done")).toBe("ok");
  });

  it("maps error to danger", () => {
    expect(getSpeechStatusColor("error")).toBe("danger");
  });
});

// ── getPrimaryIssue ────────────────────────────────────────────────────────────

const MOCK_ISSUES = [
  {
    issue_type: "no_weighing" as const,
    severity: "medium" as const,
    title: "No weighing",
    explanation: "Impacts not compared.",
    why_it_matters: "Judge can't evaluate.",
    recommendation: "Add comparisons.",
    affected_argument_labels: [],
    recommended_drill_type: "weighing",
  },
  {
    issue_type: "missing_warrant" as const,
    severity: "high" as const,
    title: "Missing warrant",
    explanation: "No logical link.",
    why_it_matters: "Flow judges skip it.",
    recommendation: "Add because sentence.",
    affected_argument_labels: ["C1"],
    recommended_drill_type: "warranting",
  },
];

describe("getPrimaryIssue", () => {
  it("returns highest severity issue", () => {
    const primary = getPrimaryIssue(MOCK_ISSUES);
    expect(primary?.issue_type).toBe("missing_warrant");
    expect(primary?.severity).toBe("high");
  });

  it("returns null for empty array", () => {
    expect(getPrimaryIssue([])).toBeNull();
  });

  it("returns null for undefined", () => {
    expect(getPrimaryIssue(undefined)).toBeNull();
  });
});

// ── getAffectedArgumentLabels ──────────────────────────────────────────────────

describe("getAffectedArgumentLabels", () => {
  it("returns deduplicated labels from all issues", () => {
    const issues = [
      { ...MOCK_ISSUES[0], affected_argument_labels: ["C1", "C2"] },
      { ...MOCK_ISSUES[1], affected_argument_labels: ["C1", "C3"] },
    ];
    const labels = getAffectedArgumentLabels(issues);
    expect(labels).toContain("C1");
    expect(labels).toContain("C2");
    expect(labels).toContain("C3");
    expect(labels.length).toBe(3); // deduplicated
  });

  it("returns empty for undefined", () => {
    expect(getAffectedArgumentLabels(undefined)).toEqual([]);
  });
});

// ── mapIssueToDrillType ────────────────────────────────────────────────────────

describe("mapIssueToDrillType", () => {
  it("maps missing_warrant to warranting", () => {
    expect(mapIssueToDrillType("missing_warrant")).toBe("warranting");
  });

  it("maps no_weighing to weighing", () => {
    expect(mapIssueToDrillType("no_weighing")).toBe("weighing");
  });

  it("maps dropped_argument to drops", () => {
    expect(mapIssueToDrillType("dropped_argument")).toBe("drops");
  });
});

// ── normalizeIssueType / normalizeSeverity ────────────────────────────────────

describe("normalizeIssueType", () => {
  it("returns valid types unchanged", () => {
    expect(normalizeIssueType("missing_warrant")).toBe("missing_warrant");
    expect(normalizeIssueType("no_weighing")).toBe("no_weighing");
  });

  it("returns null for invalid type", () => {
    expect(normalizeIssueType("bad_type")).toBeNull();
    expect(normalizeIssueType("")).toBeNull();
  });
});

describe("normalizeSeverity", () => {
  it("passes through valid severities", () => {
    expect(normalizeSeverity("low")).toBe("low");
    expect(normalizeSeverity("high")).toBe("high");
  });

  it("normalizes medium", () => {
    expect(normalizeSeverity("medium")).toBe("medium");
  });

  it("defaults unknown to medium", () => {
    expect(normalizeSeverity("critical")).toBe("medium");
    expect(normalizeSeverity("")).toBe("medium");
  });
});
