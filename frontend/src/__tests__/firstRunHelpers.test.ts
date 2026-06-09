import { deriveFirstRunState, FIRST_RUN_STATE_LABELS } from "@/lib/firstRunHelpers";
import type { ProgressSummary, PilotSummary, Speech } from "@/types";

// ── Factories ──────────────────────────────────────────────────────────────────

function makeProgress(overrides: Partial<ProgressSummary> = {}): ProgressSummary {
  return {
    speech_count:           0,
    feedback_ready_count:   0,
    drill_attempts_count:   0,
    drills_assigned_count:  0,
    drills_completed_count: 0,
    drill_completion_rate:  null,
    xp:                     0,
    level:                  1,
    xp_to_next_level:       100,
    badges:                 [],
    incomplete_drills:      [],
    skill_averages:         null,
    ...overrides,
  };
}

function makePilot(overrides: Partial<PilotSummary> = {}): PilotSummary {
  return {
    speech_count:              0,
    analyzed_speech_count:     0,
    drill_count:               0,
    drill_attempt_count:       0,
    completed_drill_count:     0,
    rerecord_count:            0,
    comparison_count:          0,
    feedback_rating_count:     0,
    average_feedback_rating:   null,
    drill_rating_count:        0,
    average_drill_rating:      null,
    return_for_second_speech:  false,
    completed_one_drill:       false,
    latest_skill_scores:       null,
    skill_trends:              null,
    common_issues:             [],
    ...overrides,
  };
}

function makeSpeech(overrides: Partial<Speech> = {}): Speech {
  return {
    id:                "s1",
    user_id:           "u1",
    title:             "Test speech",
    speech_type:       "constructive",
    side:              null,
    judge_type:        null,
    topic:             null,
    audio_url:         null,
    duration_seconds:  null,
    status:            "feedback_ready",
    created_at:        "2026-01-01T00:00:00Z",
    updated_at:        "2026-01-01T00:00:00Z",
    parent_speech_id:  null,
    parent_drill_id:   null,
    ...overrides,
  } as Speech;
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("deriveFirstRunState", () => {
  it("returns no_activity when progress is null", () => {
    expect(deriveFirstRunState({ progress: null })).toBe("no_activity");
  });

  it("returns no_activity when speech_count is 0", () => {
    expect(deriveFirstRunState({ progress: makeProgress() })).toBe("no_activity");
  });

  it("returns speech_started when speech exists but no feedback", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 1, feedback_ready_count: 0 }),
    })).toBe("speech_started");
  });

  it("returns report_ready when feedback done but no drills assigned", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 1, feedback_ready_count: 1, drills_assigned_count: 0 }),
    })).toBe("report_ready");
  });

  it("returns drill_ready when drills assigned but none attempted", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 1, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 0 }),
    })).toBe("drill_ready");
  });

  it("returns drill_attempted when drill done but no re-record", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 1, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 }),
      speeches: [makeSpeech({ parent_speech_id: null })],
    })).toBe("drill_attempted");
  });

  it("returns rerecord_ready when re-recorded via speech.parent_speech_id (no pilot)", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 2, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 }),
      speeches: [
        makeSpeech({ id: "s1", parent_speech_id: null }),
        makeSpeech({ id: "s2", parent_speech_id: "s1" }),
      ],
    })).toBe("rerecord_ready");
  });

  it("returns rerecord_ready when pilot.rerecord_count > 0", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 2, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 }),
      pilot: makePilot({ rerecord_count: 1 }),
    })).toBe("rerecord_ready");
  });

  it("returns improvement_ready when pilot.comparison_count > 0", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 2, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 }),
      pilot: makePilot({ rerecord_count: 1, comparison_count: 1 }),
    })).toBe("improvement_ready");
  });

  it("returns feedback_rated when pilot.feedback_rating_count > 0", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 2, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 }),
      pilot: makePilot({ rerecord_count: 1, comparison_count: 1, feedback_rating_count: 1 }),
    })).toBe("feedback_rated");
  });

  it("returns active_user when feedback_ready >= 3 AND drill_attempts >= 3", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 5, feedback_ready_count: 3, drills_assigned_count: 9, drill_attempts_count: 3 }),
    })).toBe("active_user");
  });

  it("active_user requires BOTH thresholds — only feedback_ready does not qualify", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 5, feedback_ready_count: 3, drills_assigned_count: 9, drill_attempts_count: 2 }),
    })).not.toBe("active_user");
  });

  it("active_user requires BOTH thresholds — only drill_attempts does not qualify", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 5, feedback_ready_count: 2, drills_assigned_count: 9, drill_attempts_count: 3 }),
    })).not.toBe("active_user");
  });

  it("active_user beats feedback_rated (checked first)", () => {
    // active_user threshold passed — should return active_user not feedback_rated
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 5, feedback_ready_count: 3, drills_assigned_count: 9, drill_attempts_count: 3 }),
      pilot: makePilot({ rerecord_count: 2, comparison_count: 2, feedback_rating_count: 2 }),
    })).toBe("active_user");
  });

  it("uses fallback speeches check when pilot is null/undefined", () => {
    // Parent speech exists in array → rerecord_ready without pilot
    const progress = makeProgress({ speech_count: 2, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 });
    const speeches = [makeSpeech({ id: "orig", parent_speech_id: null }), makeSpeech({ id: "re", parent_speech_id: "orig" })];
    expect(deriveFirstRunState({ progress, speeches })).toBe("rerecord_ready");
  });

  it("does NOT return rerecord_ready when pilot.rerecord_count === 0", () => {
    expect(deriveFirstRunState({
      progress: makeProgress({ speech_count: 1, feedback_ready_count: 1, drills_assigned_count: 3, drill_attempts_count: 1 }),
      pilot: makePilot({ rerecord_count: 0 }),
    })).toBe("drill_attempted");
  });

  it("returns no_activity when speeches default to empty array", () => {
    expect(deriveFirstRunState({ progress: makeProgress({ speech_count: 0 }) })).toBe("no_activity");
  });
});

describe("FIRST_RUN_STATE_LABELS", () => {
  it("has a label for every state", () => {
    const states = [
      "no_activity", "speech_started", "report_ready", "drill_ready",
      "drill_attempted", "rerecord_ready", "improvement_ready", "feedback_rated", "active_user",
    ];
    for (const state of states) {
      expect(FIRST_RUN_STATE_LABELS[state as keyof typeof FIRST_RUN_STATE_LABELS]).toBeTruthy();
    }
  });
});
