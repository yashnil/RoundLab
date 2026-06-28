import {
  speechTypeLabel,
  judgeTypeLabel,
  scoreColor,
  formatDelta,
  deltaBadgeClass,
  formatPracticePlan,
  buildShareUrl,
} from "@/lib/reportHelpers";
import type { SharedReportPayload } from "@/types";

// ── speechTypeLabel ────────────────────────────────────────────────────────────

describe("speechTypeLabel", () => {
  it("returns Constructive for constructive", () => {
    expect(speechTypeLabel("constructive")).toBe("Constructive");
  });

  it("returns Final Focus for final_focus", () => {
    expect(speechTypeLabel("final_focus")).toBe("Final Focus");
  });

  it("passes through unknown type unchanged", () => {
    expect(speechTypeLabel("unknown_type")).toBe("unknown_type");
  });
});

// ── judgeTypeLabel ─────────────────────────────────────────────────────────────

describe("judgeTypeLabel", () => {
  it("returns Lay judge for lay", () => {
    expect(judgeTypeLabel("lay")).toBe("Lay judge");
  });

  it("returns empty string for null", () => {
    expect(judgeTypeLabel(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(judgeTypeLabel(undefined)).toBe("");
  });
});

// ── scoreColor ─────────────────────────────────────────────────────────────────

describe("scoreColor", () => {
  it("returns ok class for 80+", () => {
    expect(scoreColor(85)).toContain("ok");
    expect(scoreColor(80)).toContain("ok");
  });

  it("returns warn class for 60-79", () => {
    expect(scoreColor(65)).toContain("warn");
  });

  it("returns danger class below 60", () => {
    expect(scoreColor(50)).toContain("danger");
  });

  it("returns subtle class for null", () => {
    expect(scoreColor(null)).toContain("subtle");
  });
});

// ── formatDelta ────────────────────────────────────────────────────────────────

describe("formatDelta", () => {
  it("prefixes positive with +", () => {
    expect(formatDelta(5)).toBe("+5");
  });

  it("does not prefix negative with +", () => {
    expect(formatDelta(-3)).toBe("-3");
  });

  it("returns dash for null", () => {
    expect(formatDelta(null)).toBe("—");
  });

  it("appends unit", () => {
    expect(formatDelta(10, " pts")).toBe("+10 pts");
  });
});

// ── deltaBadgeClass ────────────────────────────────────────────────────────────

describe("deltaBadgeClass", () => {
  it("ok for positive", () => {
    expect(deltaBadgeClass(3)).toContain("ok");
  });

  it("danger for negative", () => {
    expect(deltaBadgeClass(-2)).toContain("danger");
  });

  it("subtle for zero", () => {
    expect(deltaBadgeClass(0)).toContain("subtle");
  });

  it("faint for null", () => {
    expect(deltaBadgeClass(null)).toContain("faint");
  });
});

// ── buildShareUrl ──────────────────────────────────────────────────────────────

describe("buildShareUrl", () => {
  it("returns a path with the token", () => {
    const url = buildShareUrl("abc123");
    expect(url).toContain("/share/abc123");
  });
});

// ── formatPracticePlan ─────────────────────────────────────────────────────────

function makePayload(overrides: Partial<SharedReportPayload> = {}): SharedReportPayload {
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
        description: "Practice building strong warrants.",
        skill_target: "warranting",
        prompt: "Take your weakest argument and add a mechanism.",
        success_criteria: ["Clearly state the mechanism"],
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
      transcript: false,
      flow: false,
      feedback: true,
      drills: true,
      delivery: true,
      evidence_summary: false,
      improvement: false,
    },
    ...overrides,
  };
}

describe("formatPracticePlan", () => {
  it("includes Dissio header", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("Dissio Practice Plan");
  });

  it("includes speech type", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("Constructive");
  });

  it("includes top priorities when present", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("Improve warrants");
    expect(text).toContain("Add weighing");
  });

  it("includes drill titles", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("Warrant Builder");
  });

  it("includes delivery info", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("165 WPM");
  });

  it("includes re-record goal section", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("Next re-record goal");
  });

  it("handles missing feedback gracefully", () => {
    const text = formatPracticePlan(makePayload({ feedback: null }));
    expect(text).toContain("Dissio Practice Plan");
  });

  it("handles missing drills gracefully", () => {
    const text = formatPracticePlan(makePayload({ drills: null }));
    expect(text).toContain("Dissio Practice Plan");
  });

  it("ends with Dissio attribution", () => {
    const text = formatPracticePlan(makePayload());
    expect(text).toContain("Generated by Dissio");
  });
});
