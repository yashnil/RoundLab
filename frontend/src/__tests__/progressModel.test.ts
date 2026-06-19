import {
  deriveCurrentFocus,
  derivePracticeCoverage,
  deriveMilestones,
  deriveWeeklyPlan,
  drillEffectivenessNote,
  progressDataState,
} from "@/lib/progressModel";
import type { ProgressSummary, Speech } from "@/types";

function progress(over: Partial<ProgressSummary>): ProgressSummary {
  return {
    speech_count: 3,
    feedback_ready_count: 3,
    drills_assigned_count: 2,
    drill_attempts_count: 2,
    drills_completed_count: 1,
    drill_completion_rate: 0.5,
    incomplete_drills: [],
    skill_averages: { clash: 14, weighing: 8, extensions: 16, drops: 18, judge_adaptation: 12 },
    xp: 100, level: 2, xp_to_next_level: 50, badges: [],
    ...over,
  };
}

function speech(over: Partial<Speech>): Speech {
  return {
    id: "s", user_id: "u", title: "T", speech_type: "constructive", side: "pro",
    judge_type: "flow", topic: null, audio_url: null, duration_seconds: 60, status: "done",
    created_at: "", updated_at: "", parent_speech_id: null, source_drill_id: null, ...over,
  };
}

describe("deriveCurrentFocus", () => {
  it("picks the lowest skill and flags low confidence under 2 reports", () => {
    expect(deriveCurrentFocus(progress({}))!.skill).toBe("Impact weighing");
    expect(deriveCurrentFocus(progress({ feedback_ready_count: 1 }))!.lowConfidence).toBe(true);
  });
  it("returns null without skill averages", () => {
    expect(deriveCurrentFocus(progress({ skill_averages: null }))).toBeNull();
  });
});

describe("derivePracticeCoverage", () => {
  it("marks practiced types and counts them", () => {
    const cov = derivePracticeCoverage([speech({ speech_type: "constructive" }), speech({ speech_type: "constructive" })]);
    const constructive = cov.find((c) => c.type === "constructive")!;
    expect(constructive.count).toBe(2);
    expect(constructive.practiced).toBe(true);
    expect(cov.find((c) => c.type === "summary")!.practiced).toBe(false);
  });
});

describe("deriveMilestones", () => {
  it("derives done states from progress + speeches", () => {
    const m = deriveMilestones(progress({}), [speech({ id: "p" }), speech({ id: "c", parent_speech_id: "p" })]);
    expect(m.find((x) => x.id === "first-rerecord")!.done).toBe(true);
    expect(m.find((x) => x.id === "all-types")!.done).toBe(false);
  });
});

describe("deriveWeeklyPlan", () => {
  it("always returns drills + full speech + re-record + evidence", () => {
    const plan = deriveWeeklyPlan(progress({}), [speech({ status: "done" })]);
    expect(plan.map((p) => p.id)).toEqual(["drill-1", "full-speech", "re-record", "evidence"]);
    expect(plan.every((p) => p.href.length > 0)).toBe(true);
  });
  it("steers the full-speech item toward a neglected type", () => {
    const plan = deriveWeeklyPlan(progress({}), [speech({ speech_type: "constructive", status: "done" })]);
    expect(plan.find((p) => p.id === "full-speech")!.href).not.toContain("constructive");
  });
});

describe("drillEffectivenessNote + progressDataState", () => {
  it("is honest when there are no attempts or too little data", () => {
    expect(drillEffectivenessNote(progress({ drill_attempts_count: 0 }))).toContain("No drill attempts");
    expect(drillEffectivenessNote(progress({ feedback_ready_count: 1 }))).toContain("Not enough");
  });
  it("classifies data state", () => {
    expect(progressDataState(progress({ speech_count: 0 }))).toBe("empty");
    expect(progressDataState(progress({ feedback_ready_count: 1 }))).toBe("sparse");
    expect(progressDataState(progress({}))).toBe("ready");
  });
});
