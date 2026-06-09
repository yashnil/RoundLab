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
  deriveEvidenceRiskSummary,
} from "../lib/debateHelpers";
import type { ClaimEvidenceCheck } from "../types";

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

// ── derivePracticeNextAction ───────────────────────────────────────────────────

import type { ProgressSummary, Speech } from "../types";

const BASE_PROGRESS: ProgressSummary = {
  speech_count: 0,
  feedback_ready_count: 0,
  drills_assigned_count: 0,
  drill_attempts_count: 0,
  drills_completed_count: 0,
  drill_completion_rate: null,
  incomplete_drills: [],
  skill_averages: null,
  xp: 0,
  level: 1,
  xp_to_next_level: 100,
  badges: [],
};

const BASE_DRILL = {
  id: "drill-1",
  speech_id: "speech-1",
  title: "Impact Comparison Sprint",
  skill_target: "weighing",
  difficulty: "beginner",
  status: "assigned",
  speech_title: "Round 1 Constructive",
};

describe("derivePracticeNextAction", () => {
  it("returns start_first_speech when no speeches", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const action = derivePracticeNextAction(null, null);
    expect(action.state).toBe("start_first_speech");
    expect(action.primaryHref).toBe("/session");
    expect(action.loopStep).toBe(0);
  });

  it("returns start_first_speech when progress has 0 speeches", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const action = derivePracticeNextAction(BASE_PROGRESS, null);
    expect(action.state).toBe("start_first_speech");
  });

  it("returns wait_for_analysis for analyzing speech", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = { ...BASE_PROGRESS, speech_count: 1 };
    const speech = { id: "sp-1", status: "analyzing" } as Speech;
    const action = derivePracticeNextAction(progress, speech);
    expect(action.state).toBe("wait_for_analysis");
    expect(action.loopStep).toBe(1);
    expect(action.primaryHref).toBe("/speech/sp-1");
  });

  it("returns open_report for done speech with no feedback", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = { ...BASE_PROGRESS, speech_count: 1 };
    const speech = { id: "sp-1", status: "done" } as Speech;
    const action = derivePracticeNextAction(progress, speech);
    expect(action.state).toBe("open_report");
    expect(action.primaryHref).toBe("/speech/sp-1");
  });

  it("returns generate_drills when feedback exists but no drills", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = { ...BASE_PROGRESS, speech_count: 1, feedback_ready_count: 1 };
    const speech = { id: "sp-1", status: "done" } as Speech;
    const action = derivePracticeNextAction(progress, speech);
    expect(action.state).toBe("generate_drills");
    expect(action.loopStep).toBe(2);
  });

  it("returns start_drill for first drill with no attempts", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = {
      ...BASE_PROGRESS,
      speech_count: 1,
      feedback_ready_count: 1,
      drills_assigned_count: 3,
      drill_attempts_count: 0,
      incomplete_drills: [BASE_DRILL],
    };
    const action = derivePracticeNextAction(progress, null);
    expect(action.state).toBe("start_drill");
    expect(action.primaryHref).toBe("/drills/drill-1");
    expect(action.primaryLabel).toBe("Open drill workspace");
  });

  it("returns continue_drill when some attempts exist", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = {
      ...BASE_PROGRESS,
      speech_count: 1,
      feedback_ready_count: 1,
      drills_assigned_count: 3,
      drill_attempts_count: 2,
      incomplete_drills: [BASE_DRILL],
    };
    const action = derivePracticeNextAction(progress, null);
    expect(action.state).toBe("continue_drill");
    expect(action.primaryHref).toBe("/drills/drill-1");
  });

  it("returns re_record when all drills done and only 1 speech", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = {
      ...BASE_PROGRESS,
      speech_count: 1,
      feedback_ready_count: 1,
      drills_assigned_count: 3,
      drill_attempts_count: 3,
      incomplete_drills: [],
    };
    const action = derivePracticeNextAction(progress, null);
    expect(action.state).toBe("re_record");
    expect(action.primaryHref).toBe("/session");
    expect(action.loopStep).toBe(3);
  });

  it("returns view_improvement when 2+ speeches", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = {
      ...BASE_PROGRESS,
      speech_count: 2,
      feedback_ready_count: 2,
      drills_assigned_count: 3,
      drill_attempts_count: 3,
      incomplete_drills: [],
    };
    const speech = { id: "sp-2", status: "done" } as Speech;
    const action = derivePracticeNextAction(progress, speech);
    expect(action.state).toBe("view_improvement");
    expect(action.loopStep).toBe(4);
  });

  it("returns view_improvement when latest speech is a re-record and done", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = {
      ...BASE_PROGRESS,
      speech_count: 2,
      feedback_ready_count: 2,
      drills_assigned_count: 3,
      drill_attempts_count: 3,
      incomplete_drills: [],
    };
    const speech = { id: "sp-rerecord", status: "done", parent_speech_id: "sp-original" } as Speech;
    const action = derivePracticeNextAction(progress, speech);
    expect(action.state).toBe("view_improvement");
    expect(action.primaryHref).toBe("/speech/sp-rerecord");
    expect(action.loopStep).toBe(4);
  });

  it("returns wait_for_analysis when latest speech is a re-record and analyzing", () => {
    const { derivePracticeNextAction } = require("../lib/debateHelpers");
    const progress = {
      ...BASE_PROGRESS,
      speech_count: 2,
      feedback_ready_count: 1,
      drills_assigned_count: 3,
      drill_attempts_count: 3,
      incomplete_drills: [],
    };
    const speech = { id: "sp-rerecord", status: "analyzing", parent_speech_id: "sp-original" } as Speech;
    const action = derivePracticeNextAction(progress, speech);
    expect(action.state).toBe("wait_for_analysis");
    expect(action.primaryHref).toBe("/speech/sp-rerecord");
    expect(action.loopStep).toBe(3);
  });
});

// ── compareSpeeches ────────────────────────────────────────────────────────────

import type { FeedbackReport } from "../types";

const ORIG_FEEDBACK: Pick<FeedbackReport, "overall_score" | "scores" | "weaknesses"> = {
  overall_score: 62,
  scores: { clash: 10, weighing: 9, extensions: 14, drops: 16, judge_adaptation: 13 },
  weaknesses: ["Impact weighing not explicit"],
};

const NEW_FEEDBACK: Pick<FeedbackReport, "overall_score" | "scores" | "weaknesses"> = {
  overall_score: 70,
  scores: { clash: 10, weighing: 13, extensions: 14, drops: 16, judge_adaptation: 17 },
  weaknesses: ["Evidence comparison still thin"],
};

describe("compareSpeeches", () => {
  it("computes correct overall delta", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(ORIG_FEEDBACK, NEW_FEEDBACK, null);
    expect(result.overall_delta).toBe(8); // 70 - 62
    expect(result.has_parent).toBe(true);
  });

  it("computes targeted skill delta for weighing", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(ORIG_FEEDBACK, NEW_FEEDBACK, "weighing");
    expect(result.skill_delta).toBe(4); // 13 - 9
    expect(result.source_drill_skill).toBe("weighing");
    expect(result.original_skill_score).toBe(9);
    expect(result.new_skill_score).toBe(13);
  });

  it("maps warranting skill to clash dimension", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(ORIG_FEEDBACK, NEW_FEEDBACK, "warranting");
    // clash: 10 → 10 = delta 0
    expect(result.skill_delta).toBe(0);
    expect(result.original_skill_score).toBe(10);
  });

  it("returns null deltas when original feedback is missing", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(null, NEW_FEEDBACK, "weighing");
    expect(result.overall_delta).toBeNull();
    expect(result.skill_delta).toBeNull();
  });

  it("returns null deltas when new feedback is missing", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(ORIG_FEEDBACK, null, "weighing");
    expect(result.overall_delta).toBeNull();
    expect(result.skill_delta).toBeNull();
  });

  it("returns null deltas when both feedbacks are missing", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(null, null, null);
    expect(result.overall_delta).toBeNull();
    expect(result.skill_delta).toBeNull();
    expect(result.has_parent).toBe(true);
  });

  it("uses still_needs_work from the new feedback weaknesses", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(ORIG_FEEDBACK, NEW_FEEDBACK, null);
    expect(result.still_needs_work).toBe("Evidence comparison still thin");
  });

  it("summary mentions improvement when score increased significantly", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const result = compareSpeeches(ORIG_FEEDBACK, NEW_FEEDBACK, null);
    expect(result.summary.toLowerCase()).toMatch(/improve|up/);
  });

  it("summary mentions dip when score decreased", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const lowerNew = { ...NEW_FEEDBACK, overall_score: 55 };
    const result = compareSpeeches(ORIG_FEEDBACK, lowerNew, null);
    expect(result.summary.toLowerCase()).toContain("dipped");
  });

  it("summary mentions steady when score unchanged", () => {
    const { compareSpeeches } = require("../lib/debateHelpers");
    const sameScore = { ...NEW_FEEDBACK, overall_score: 62 };
    const result = compareSpeeches(ORIG_FEEDBACK, sameScore, null);
    expect(result.summary.toLowerCase()).toContain("steady");
  });
});

// ── deriveEvidenceRiskSummary ─────────────────────────────────────────────────

function makeCheck(support_level: string, id = "check-1"): ClaimEvidenceCheck {
  return {
    id,
    speech_id: "speech-1",
    user_id: "user-1",
    argument_label: "C1: Test",
    claim_text: "Test claim",
    evidence_text_from_speech: "Test evidence",
    matched_card_id: null,
    support_level: support_level as ClaimEvidenceCheck["support_level"],
    explanation: "Test explanation",
    created_at: "2026-06-09T00:00:00Z",
  };
}

describe("deriveEvidenceRiskSummary", () => {
  it("returns empty state when no checks", () => {
    const result = deriveEvidenceRiskSummary([]);
    expect(result.total_checked).toBe(0);
    expect(result.highest_risk_level).toBeNull();
    expect(result.summary).toContain("No evidence checks");
  });

  it("correctly counts supported checks", () => {
    const checks = [makeCheck("supported", "c1"), makeCheck("supported", "c2")];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.supported_count).toBe(2);
    expect(result.unsupported_count).toBe(0);
    expect(result.partial_count).toBe(0);
    expect(result.unverifiable_count).toBe(0);
    expect(result.highest_risk_level).toBeNull();
  });

  it("identifies unsupported as highest risk", () => {
    const checks = [
      makeCheck("supported", "c1"),
      makeCheck("partially_supported", "c2"),
      makeCheck("unsupported", "c3"),
    ];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.highest_risk_level).toBe("unsupported");
    expect(result.unsupported_count).toBe(1);
    expect(result.partial_count).toBe(1);
    expect(result.supported_count).toBe(1);
  });

  it("summary mentions unsupported count when present", () => {
    const checks = [makeCheck("unsupported", "c1"), makeCheck("supported", "c2")];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.summary).toMatch(/1.*not supported|not supported.*1/i);
  });

  it("summary mentions partial count when no unsupported", () => {
    const checks = [makeCheck("partially_supported", "c1"), makeCheck("supported", "c2")];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.summary).toMatch(/partially supported|partial/i);
  });

  it("summary mentions unverifiable when only unverifiable", () => {
    const checks = [makeCheck("unverifiable", "c1")];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.summary).toMatch(/no matching card|unverifiable/i);
    expect(result.highest_risk_level).toBe("unverifiable");
  });

  it("all supported yields null highest_risk_level", () => {
    const checks = [makeCheck("supported", "c1"), makeCheck("supported", "c2")];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.highest_risk_level).toBeNull();
    expect(result.summary).toMatch(/supported/i);
  });

  it("recommended_action is non-empty for every case", () => {
    for (const level of ["supported", "partially_supported", "unsupported", "unverifiable"] as const) {
      const result = deriveEvidenceRiskSummary([makeCheck(level)]);
      expect(result.recommended_action.length).toBeGreaterThan(0);
    }
    const emptyResult = deriveEvidenceRiskSummary([]);
    expect(emptyResult.recommended_action.length).toBeGreaterThan(0);
  });

  it("total_checked equals input length", () => {
    const checks = [makeCheck("supported", "c1"), makeCheck("unsupported", "c2"), makeCheck("unverifiable", "c3")];
    const result = deriveEvidenceRiskSummary(checks);
    expect(result.total_checked).toBe(3);
  });
});
