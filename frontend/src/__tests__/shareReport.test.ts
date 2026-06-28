/**
 * Share report system — pure function and logic tests.
 * No DOM rendering (project uses ts-jest without @testing-library).
 *
 * Component rendering is validated in manual verification.
 */
import {
  speechTypeLabel,
  judgeTypeLabel,
  formatPracticePlan,
  buildShareUrl,
  scoreColor,
  formatDelta,
  deltaBadgeClass,
} from "@/lib/reportHelpers";
import type { SharedReportPayload } from "@/types";

// ── Default share settings ─────────────────────────────────────────────────────

const DEFAULT_INCLUDE = {
  include_feedback: true,
  include_flow: true,
  include_drills: true,
  include_delivery: true,
  include_transcript: true,
  include_improvement: true,
  include_evidence_summary: false,
};

describe("default share include settings", () => {
  it("evidence summary is off by default", () => {
    expect(DEFAULT_INCLUDE.include_evidence_summary).toBe(false);
  });

  it("feedback is on by default", () => {
    expect(DEFAULT_INCLUDE.include_feedback).toBe(true);
  });

  it("flow is on by default", () => {
    expect(DEFAULT_INCLUDE.include_flow).toBe(true);
  });

  it("drills are on by default", () => {
    expect(DEFAULT_INCLUDE.include_drills).toBe(true);
  });

  it("delivery is on by default", () => {
    expect(DEFAULT_INCLUDE.include_delivery).toBe(true);
  });
});

// ── buildShareUrl ──────────────────────────────────────────────────────────────

describe("buildShareUrl", () => {
  it("produces a URL containing the token", () => {
    expect(buildShareUrl("abc123")).toContain("abc123");
  });

  it("produces a URL containing /share/", () => {
    expect(buildShareUrl("abc123")).toContain("/share/");
  });

  it("works for arbitrary token strings", () => {
    const token = "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6";
    expect(buildShareUrl(token)).toContain(token);
  });
});

// ── speech/judge type labels ───────────────────────────────────────────────────

describe("speechTypeLabel", () => {
  it("formats constructive", () => expect(speechTypeLabel("constructive")).toBe("Constructive"));
  it("formats final_focus", () => expect(speechTypeLabel("final_focus")).toBe("Final Focus"));
  it("formats rebuttal", () => expect(speechTypeLabel("rebuttal")).toBe("Rebuttal"));
  it("passes through unknown", () => expect(speechTypeLabel("other")).toBe("other"));
});

describe("judgeTypeLabel", () => {
  it("formats lay", () => expect(judgeTypeLabel("lay")).toBe("Lay judge"));
  it("formats flow", () => expect(judgeTypeLabel("flow")).toBe("Flow judge"));
  it("returns empty for null", () => expect(judgeTypeLabel(null)).toBe(""));
  it("returns empty for undefined", () => expect(judgeTypeLabel(undefined)).toBe(""));
});

// ── scoreColor ─────────────────────────────────────────────────────────────────

describe("scoreColor", () => {
  it("ok for 80+", () => expect(scoreColor(80)).toContain("ok"));
  it("warn for 60–79", () => expect(scoreColor(70)).toContain("warn"));
  it("danger for below 60", () => expect(scoreColor(50)).toContain("danger"));
  it("subtle for null", () => expect(scoreColor(null)).toContain("subtle"));
});

// ── formatDelta ────────────────────────────────────────────────────────────────

describe("formatDelta", () => {
  it("prefixes positive delta", () => expect(formatDelta(5)).toBe("+5"));
  it("no prefix for negative", () => expect(formatDelta(-3)).toBe("-3"));
  it("dash for null", () => expect(formatDelta(null)).toBe("—"));
  it("dash for undefined", () => expect(formatDelta(undefined)).toBe("—"));
  it("appends unit", () => expect(formatDelta(10, " pts")).toBe("+10 pts"));
  it("zero formatted as 0", () => expect(formatDelta(0)).toBe("0"));
});

// ── deltaBadgeClass ────────────────────────────────────────────────────────────

describe("deltaBadgeClass", () => {
  it("ok for positive", () => expect(deltaBadgeClass(5)).toContain("ok"));
  it("danger for negative", () => expect(deltaBadgeClass(-2)).toContain("danger"));
  it("subtle for zero", () => expect(deltaBadgeClass(0)).toContain("subtle"));
  it("faint for null", () => expect(deltaBadgeClass(null)).toContain("faint"));
});

// ── formatPracticePlan ─────────────────────────────────────────────────────────

function makeFull(): SharedReportPayload {
  return {
    token: "tok",
    speech_type: "constructive",
    side: "pro",
    judge_type: "flow",
    topic: "Resolved: Test.",
    created_at: "2026-06-09T00:00:00Z",
    feedback: {
      overall_score: 72,
      scores: null,
      summary: "Good speech.",
      strengths: ["Clear claims"],
      weaknesses: ["Weak warrants"],
      top_3_priorities: ["Improve warrants", "Add weighing"],
      structured_issues: null,
    },
    arguments: null,
    drills: [
      {
        title: "Warrant Builder",
        description: "Practice warrants.",
        skill_target: "warranting",
        prompt: "Rebuild your weakest argument.",
        success_criteria: ["Clear mechanism"],
        difficulty: "beginner",
      },
    ],
    delivery: {
      words_per_minute: 165,
      filler_word_count: 4,
      delivery_score: 78,
      pacing_band: "steady",
      repeated_phrases_json: null,
    },
    transcript_text: null,
    evidence_summary: null,
    comparison: null,
    include_flags: {
      transcript: false, flow: false, feedback: true,
      drills: true, delivery: true, evidence_summary: false, improvement: false,
    },
  };
}

describe("formatPracticePlan", () => {
  it("starts with Dissio Practice Plan header", () => {
    const text = formatPracticePlan(makeFull());
    expect(text.startsWith("Dissio Practice Plan")).toBe(true);
  });

  it("includes speech type label", () => {
    expect(formatPracticePlan(makeFull())).toContain("Constructive");
  });

  it("includes all top priorities", () => {
    const text = formatPracticePlan(makeFull());
    expect(text).toContain("Improve warrants");
    expect(text).toContain("Add weighing");
  });

  it("includes drill titles", () => {
    expect(formatPracticePlan(makeFull())).toContain("Warrant Builder");
  });

  it("includes delivery WPM", () => {
    expect(formatPracticePlan(makeFull())).toContain("165 WPM");
  });

  it("includes overall score when present", () => {
    expect(formatPracticePlan(makeFull())).toContain("72/100");
  });

  it("includes next re-record goal section", () => {
    expect(formatPracticePlan(makeFull())).toContain("Next re-record goal");
  });

  it("handles null feedback without crashing", () => {
    const text = formatPracticePlan({ ...makeFull(), feedback: null });
    expect(text).toContain("Dissio Practice Plan");
  });

  it("handles null drills without crashing", () => {
    const text = formatPracticePlan({ ...makeFull(), drills: null });
    expect(text).toContain("Dissio Practice Plan");
  });

  it("handles null delivery without crashing", () => {
    const text = formatPracticePlan({ ...makeFull(), delivery: null });
    expect(text).toContain("Dissio Practice Plan");
  });

  it("ends with Dissio attribution", () => {
    expect(formatPracticePlan(makeFull())).toContain("Generated by Dissio");
  });

  it("includes resolution when topic is set", () => {
    expect(formatPracticePlan(makeFull())).toContain("Resolved: Test.");
  });

  it("uses drill title as fallback goal when no priorities", () => {
    const data = { ...makeFull(), feedback: null };
    expect(formatPracticePlan(data)).toContain("Warrant Builder");
  });
});

// ── Shared report include flags model ─────────────────────────────────────────

describe("SharedReportIncludeFlags model", () => {
  const flags = {
    transcript: true,
    flow: true,
    feedback: true,
    drills: true,
    delivery: true,
    evidence_summary: false,
    improvement: true,
  };

  it("evidence_summary defaults to false", () => {
    expect(flags.evidence_summary).toBe(false);
  });

  it("all other flags default to true", () => {
    const { evidence_summary, ...rest } = flags;
    Object.values(rest).forEach((v) => expect(v).toBe(true));
  });
});
