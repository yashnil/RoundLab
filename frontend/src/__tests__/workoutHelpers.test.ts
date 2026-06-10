import {
  estimateWorkoutMinutes,
  deriveWorkoutProgress,
  getWorkoutFocusLabel,
  getWorkoutStepCategoryLabel,
  getNextIncompleteStep,
  buildReRecordGoal,
  shouldShowWorkoutCTA,
  workoutStatusLabel,
  formatWorkoutPlan,
} from "@/lib/workoutHelpers";
import { formatPracticePlan } from "@/lib/reportHelpers";
import type { Workout, WorkoutStep, WorkoutJson, SharedReportPayload } from "@/types";

// ── Factories ──────────────────────────────────────────────────────────────────

function makeStep(overrides: Partial<WorkoutStep> = {}): WorkoutStep {
  return {
    id: "step-1",
    title: "Strengthen warrant",
    category: "argument",
    focus: "warranting",
    estimated_minutes: 5,
    source: "feedback",
    problem: "Warrant is thin",
    instruction: "Add a mechanism",
    success_criteria: "Warrant answers 'how'",
    completed: false,
    ...overrides,
  };
}

function makeWorkoutJson(steps: WorkoutStep[], overrides: Partial<WorkoutJson> = {}): WorkoutJson {
  return {
    steps,
    re_record_goal: "Show clear warrants on all three contentions",
    coach_note: "Focus on the mechanism sentence",
    generated_from: {},
    ...overrides,
  };
}

function makeWorkout(overrides: Partial<Workout> = {}): Workout {
  const steps = [
    makeStep({ id: "s1", estimated_minutes: 5 }),
    makeStep({ id: "s2", category: "evidence", focus: "evidence", estimated_minutes: 4, completed: false }),
    makeStep({ id: "s3", category: "rerecord", focus: "rerecord", estimated_minutes: 3, completed: false }),
  ];
  return {
    id: "w-1",
    user_id: "u-1",
    speech_id: "sp-1",
    title: "Tournament Prep: Constructive",
    description: "Focused on warrant clarity",
    estimated_minutes: 12,
    workout_type: "tournament_prep",
    status: "not_started",
    focus_area: "warranting",
    workout_json: makeWorkoutJson(steps),
    created_at: "2026-06-09T10:00:00Z",
    updated_at: "2026-06-09T10:00:00Z",
    ...overrides,
  };
}

function makeSharedPayload(overrides: Partial<SharedReportPayload> = {}): SharedReportPayload {
  return {
    token: "test-token",
    speech_type: "constructive",
    side: "pro",
    topic: "Test resolution",
    judge_type: "flow",
    created_at: "2026-06-09T10:00:00Z",
    feedback: {
      overall_score: 72,
      scores: null,
      summary: null,
      top_3_priorities: ["Add warrants", "Weigh impacts", "Signpost"],
      weaknesses: ["Thin warrants"],
      strengths: ["Good structure"],
      structured_issues: null,
    },
    delivery: {
      words_per_minute: 185,
      filler_word_count: 3,
      delivery_score: null,
      pacing_band: "on_pace",
      repeated_phrases_json: null,
    },
    drills: [
      {
        title: "Warrant drill",
        description: "Practice adding mechanism sentences",
        skill_target: "warrant_clarity",
        difficulty: "beginner",
        prompt: "Practice the mechanism sentence",
        success_criteria: ["State the mechanism"],
      },
    ],
    arguments: [],
    transcript_text: null,
    evidence_summary: null,
    comparison: null,
    include_flags: {
      transcript: false,
      flow: true,
      feedback: true,
      drills: true,
      delivery: true,
      evidence_summary: false,
      improvement: false,
    },
    ...overrides,
  };
}

// ── estimateWorkoutMinutes ─────────────────────────────────────────────────────

describe("estimateWorkoutMinutes", () => {
  it("sums estimated_minutes across all steps", () => {
    const steps = [
      makeStep({ estimated_minutes: 5 }),
      makeStep({ estimated_minutes: 3 }),
      makeStep({ estimated_minutes: 7 }),
    ];
    expect(estimateWorkoutMinutes(steps)).toBe(15);
  });

  it("returns 0 for empty step list", () => {
    expect(estimateWorkoutMinutes([])).toBe(0);
  });

  it("handles missing estimated_minutes as 0", () => {
    const step = makeStep({ estimated_minutes: undefined as unknown as number });
    expect(estimateWorkoutMinutes([step])).toBe(0);
  });
});

// ── deriveWorkoutProgress ──────────────────────────────────────────────────────

describe("deriveWorkoutProgress", () => {
  it("returns 0/N for a fresh workout", () => {
    const workout = makeWorkout();
    const { completed, total, pct } = deriveWorkoutProgress(workout);
    expect(completed).toBe(0);
    expect(total).toBe(3);
    expect(pct).toBe(0);
  });

  it("reflects partial completion", () => {
    const steps = [
      makeStep({ id: "s1", completed: true }),
      makeStep({ id: "s2", completed: false }),
      makeStep({ id: "s3", completed: false }),
    ];
    const workout = makeWorkout({ workout_json: makeWorkoutJson(steps) });
    const { completed, total, pct } = deriveWorkoutProgress(workout);
    expect(completed).toBe(1);
    expect(total).toBe(3);
    expect(pct).toBe(33);
  });

  it("returns 100% when all steps done", () => {
    const steps = [
      makeStep({ id: "s1", completed: true }),
      makeStep({ id: "s2", completed: true }),
    ];
    const workout = makeWorkout({ workout_json: makeWorkoutJson(steps) });
    const { pct } = deriveWorkoutProgress(workout);
    expect(pct).toBe(100);
  });

  it("returns 0 pct when step list is empty", () => {
    const workout = makeWorkout({ workout_json: makeWorkoutJson([]) });
    const { completed, total, pct } = deriveWorkoutProgress(workout);
    expect(completed).toBe(0);
    expect(total).toBe(0);
    expect(pct).toBe(0);
  });
});

// ── getWorkoutFocusLabel ───────────────────────────────────────────────────────

describe("getWorkoutFocusLabel", () => {
  it("maps known focus keys to labels", () => {
    expect(getWorkoutFocusLabel("warranting")).toBe("Warrant Clarity");
    expect(getWorkoutFocusLabel("evidence")).toBe("Evidence Alignment");
    expect(getWorkoutFocusLabel("weighing")).toBe("Impact Weighing");
    expect(getWorkoutFocusLabel("drops")).toBe("Drop Prevention");
    expect(getWorkoutFocusLabel("extensions")).toBe("Extension Quality");
    expect(getWorkoutFocusLabel("collapse")).toBe("Collapse Discipline");
    expect(getWorkoutFocusLabel("delivery")).toBe("Delivery Control");
    expect(getWorkoutFocusLabel("clash")).toBe("Direct Clash");
    expect(getWorkoutFocusLabel("rerecord")).toBe("Re-record");
  });

  it("passes unknown keys through as-is", () => {
    expect(getWorkoutFocusLabel("unknown_key")).toBe("unknown_key");
  });
});

// ── getWorkoutStepCategoryLabel ────────────────────────────────────────────────

describe("getWorkoutStepCategoryLabel", () => {
  it("maps all known categories", () => {
    expect(getWorkoutStepCategoryLabel("argument")).toBe("Argument");
    expect(getWorkoutStepCategoryLabel("evidence")).toBe("Evidence");
    expect(getWorkoutStepCategoryLabel("delivery")).toBe("Delivery");
    expect(getWorkoutStepCategoryLabel("rerecord")).toBe("Re-record");
  });

  it("passes unknown category through", () => {
    expect(getWorkoutStepCategoryLabel("custom")).toBe("custom");
  });
});

// ── getNextIncompleteStep ──────────────────────────────────────────────────────

describe("getNextIncompleteStep", () => {
  it("returns first incomplete step", () => {
    const steps = [
      makeStep({ id: "s1", completed: true }),
      makeStep({ id: "s2", completed: false }),
      makeStep({ id: "s3", completed: false }),
    ];
    const workout = makeWorkout({ workout_json: makeWorkoutJson(steps) });
    const next = getNextIncompleteStep(workout);
    expect(next?.id).toBe("s2");
  });

  it("returns null when all steps complete", () => {
    const steps = [
      makeStep({ id: "s1", completed: true }),
      makeStep({ id: "s2", completed: true }),
    ];
    const workout = makeWorkout({ workout_json: makeWorkoutJson(steps) });
    expect(getNextIncompleteStep(workout)).toBeNull();
  });

  it("returns null for empty step list", () => {
    const workout = makeWorkout({ workout_json: makeWorkoutJson([]) });
    expect(getNextIncompleteStep(workout)).toBeNull();
  });
});

// ── buildReRecordGoal ──────────────────────────────────────────────────────────

describe("buildReRecordGoal", () => {
  it("returns the re_record_goal from the workout json", () => {
    const workout = makeWorkout();
    expect(buildReRecordGoal(workout)).toBe("Show clear warrants on all three contentions");
  });
});

// ── shouldShowWorkoutCTA ───────────────────────────────────────────────────────

describe("shouldShowWorkoutCTA", () => {
  it("returns true when speech is done and has feedback and drills", () => {
    expect(shouldShowWorkoutCTA("done", true, true)).toBe(true);
  });

  it("returns false when speech is not done", () => {
    expect(shouldShowWorkoutCTA("pending", true, true)).toBe(false);
    expect(shouldShowWorkoutCTA("error", true, true)).toBe(false);
    expect(shouldShowWorkoutCTA(undefined, true, true)).toBe(false);
  });

  it("returns false when hasFeedback is false", () => {
    expect(shouldShowWorkoutCTA("done", false, true)).toBe(false);
  });

  it("returns false when hasDrills is false", () => {
    expect(shouldShowWorkoutCTA("done", true, false)).toBe(false);
  });
});

// ── workoutStatusLabel ─────────────────────────────────────────────────────────

describe("workoutStatusLabel", () => {
  it("maps all known statuses", () => {
    expect(workoutStatusLabel("not_started")).toBe("Not started");
    expect(workoutStatusLabel("in_progress")).toBe("In progress");
    expect(workoutStatusLabel("completed")).toBe("Completed");
  });
});

// ── formatWorkoutPlan ──────────────────────────────────────────────────────────

describe("formatWorkoutPlan", () => {
  it("includes the workout title and estimated time", () => {
    const workout = makeWorkout();
    const plan = formatWorkoutPlan(workout);
    expect(plan).toContain("Tournament Prep: Constructive");
    expect(plan).toContain("minutes");
  });

  it("includes focus label when focus_area is set", () => {
    const workout = makeWorkout({ focus_area: "warranting" });
    const plan = formatWorkoutPlan(workout);
    expect(plan).toContain("Warrant Clarity");
  });

  it("includes all step titles", () => {
    const steps = [
      makeStep({ id: "s1", title: "Warrant rep" }),
      makeStep({ id: "s2", title: "Evidence audit", category: "evidence" }),
    ];
    const workout = makeWorkout({ workout_json: makeWorkoutJson(steps) });
    const plan = formatWorkoutPlan(workout);
    expect(plan).toContain("Warrant rep");
    expect(plan).toContain("Evidence audit");
  });

  it("includes re-record goal", () => {
    const workout = makeWorkout();
    const plan = formatWorkoutPlan(workout);
    expect(plan).toContain("Show clear warrants on all three contentions");
  });

  it("includes coach note", () => {
    const workout = makeWorkout();
    const plan = formatWorkoutPlan(workout);
    expect(plan).toContain("Coach note: Focus on the mechanism sentence");
  });

  it("omits focus line when focus_area is not set", () => {
    const workout = makeWorkout({ focus_area: undefined });
    const plan = formatWorkoutPlan(workout);
    expect(plan).not.toContain("Focus:");
  });
});

// ── formatPracticePlan with workout ───────────────────────────────────────────

describe("formatPracticePlan — workout integration", () => {
  it("includes workout section when workout is provided", () => {
    const payload = makeSharedPayload();
    const workout = makeWorkout();
    const plan = formatPracticePlan(payload, workout);
    expect(plan).toContain("Tournament Prep Workout");
    expect(plan).toContain("Tournament Prep: Constructive");
    expect(plan).toContain("Re-record goal:");
    expect(plan).toContain("Show clear warrants on all three contentions");
  });

  it("falls back to simple re-record block when workout is null", () => {
    const payload = makeSharedPayload();
    const plan = formatPracticePlan(payload, null);
    expect(plan).toContain("Next re-record goal:");
    expect(plan).not.toContain("Tournament Prep Workout");
  });

  it("falls back when workout is undefined", () => {
    const payload = makeSharedPayload();
    const plan = formatPracticePlan(payload);
    expect(plan).toContain("Next re-record goal:");
    expect(plan).not.toContain("Tournament Prep Workout");
  });

  it("includes workout steps in the practice plan text", () => {
    const steps = [
      makeStep({ id: "s1", title: "Strengthen warrant", estimated_minutes: 5 }),
      makeStep({ id: "s2", title: "Audit evidence", category: "evidence", estimated_minutes: 4 }),
    ];
    const workout = makeWorkout({ workout_json: makeWorkoutJson(steps) });
    const plan = formatPracticePlan(makeSharedPayload(), workout);
    expect(plan).toContain("Strengthen warrant");
    expect(plan).toContain("Audit evidence");
  });

  it("includes focus label in workout section", () => {
    const workout = makeWorkout({ focus_area: "weighing" });
    const plan = formatPracticePlan(makeSharedPayload(), workout);
    expect(plan).toContain("Impact Weighing");
  });
});
