import {
  selectNextAction,
  findReRecordCandidate,
  findFailedSpeech,
  findInProgressSpeech,
  findUnfinishedCapture,
  QUICK_START_OPTIONS,
  quickStartHref,
  formatSkill,
} from "@/lib/dashboardHelpers";
import type { Speech, ProgressSummary } from "@/types";

function speech(over: Partial<Speech>): Speech {
  return {
    id: "s1",
    user_id: "u1",
    title: "Speech",
    speech_type: "constructive",
    side: "pro",
    judge_type: "flow",
    topic: null,
    audio_url: null,
    duration_seconds: 120,
    status: "done",
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    parent_speech_id: null,
    source_drill_id: null,
    ...over,
  };
}

const noProgress: ProgressSummary | null = null;

describe("selectNextAction priority", () => {
  it("brand-new student → first practice", () => {
    const a = selectNextAction({ speeches: [], progress: noProgress });
    expect(a.kind).toBe("first-practice");
    expect(a.href).toBe("/session");
    expect(a.secondary?.href).toBe("/demo");
  });

  it("failed analysis wins over everything", () => {
    const speeches = [
      speech({ id: "ok", status: "done", updated_at: "2026-06-02T00:00:00Z" }),
      speech({ id: "bad", status: "error", updated_at: "2026-06-03T00:00:00Z" }),
    ];
    const progress = {
      incomplete_drills: [{ id: "d1" }],
    } as unknown as ProgressSummary;
    const a = selectNextAction({ speeches, progress });
    expect(a.kind).toBe("retry-analysis");
    expect(a.href).toBe("/speech/bad");
  });

  it("in-progress speech beats drills and re-record", () => {
    const speeches = [
      speech({ id: "p", status: "analyzing", updated_at: "2026-06-03T00:00:00Z" }),
      speech({ id: "ok", status: "done", updated_at: "2026-06-01T00:00:00Z" }),
    ];
    const a = selectNextAction({ speeches, progress: noProgress });
    expect(a.kind).toBe("resume-analysis");
    expect(a.href).toBe("/speech/p");
  });

  it("unfinished capture (set up, never recorded) beats drills and re-record", () => {
    const speeches = [
      speech({ id: "done", status: "done", updated_at: "2026-06-01T00:00:00Z" }),
      speech({ id: "setup", status: "pending", audio_url: null, updated_at: "2026-06-04T00:00:00Z" }),
    ];
    const progress = {
      incomplete_drills: [{ id: "d1", title: "x", skill_target: "weighing" }],
    } as unknown as ProgressSummary;
    const a = selectNextAction({ speeches, progress });
    expect(a.kind).toBe("finish-capture");
    expect(a.href).toBe("/speech/setup");
  });

  it("a pending speech that already has audio is not 'unfinished capture'", () => {
    const speeches = [speech({ id: "uploaded", status: "pending", audio_url: "http://x/a.mp3" })];
    expect(findUnfinishedCapture(speeches)).toBeNull();
  });

  it("recommended drill beats re-record when present", () => {
    const speeches = [speech({ id: "ok", status: "done" })];
    const progress = {
      incomplete_drills: [
        { id: "d1", title: "Warrant depth reps", skill_target: "warrant_quality" },
      ],
    } as unknown as ProgressSummary;
    const a = selectNextAction({ speeches, progress });
    expect(a.kind).toBe("recommended-drill");
    expect(a.href).toBe("/drills/d1");
    expect(a.title).toBe("Warrant depth reps");
  });

  it("done speech with no drills → re-record", () => {
    const speeches = [speech({ id: "ok", status: "done" })];
    const a = selectNextAction({ speeches, progress: { incomplete_drills: [] } as unknown as ProgressSummary });
    expect(a.kind).toBe("re-record");
    expect(a.href).toBe("/speech/ok");
  });

  it("once a thread is re-recorded, neither end is offered again", () => {
    const speeches = [
      speech({ id: "parent", status: "done", updated_at: "2026-06-01T00:00:00Z" }),
      speech({ id: "child", status: "done", parent_speech_id: "parent", updated_at: "2026-06-02T00:00:00Z" }),
    ];
    // parent already has a child; child is itself a re-record → no candidate.
    expect(findReRecordCandidate(speeches)).toBeNull();
  });

  it("offers the newest original done speech for re-record", () => {
    const speeches = [
      speech({ id: "old", status: "done", updated_at: "2026-06-01T00:00:00Z" }),
      speech({ id: "new", status: "done", updated_at: "2026-06-04T00:00:00Z" }),
    ];
    expect(findReRecordCandidate(speeches)?.id).toBe("new");
  });

  it("falls back to keep-practicing with focus skill", () => {
    const speeches = [
      speech({ id: "parent", status: "done" }),
      speech({ id: "child", status: "done", parent_speech_id: "parent" }),
    ];
    const a = selectNextAction({
      speeches,
      progress: { incomplete_drills: [] } as unknown as ProgressSummary,
      focusSkill: "weighing",
    });
    expect(a.kind).toBe("keep-practicing");
    expect(a.title.toLowerCase()).toContain("weighing");
  });
});

describe("finders", () => {
  it("findFailedSpeech returns newest error", () => {
    const speeches = [
      speech({ id: "e1", status: "error", updated_at: "2026-06-01T00:00:00Z" }),
      speech({ id: "e2", status: "error", updated_at: "2026-06-05T00:00:00Z" }),
    ];
    expect(findFailedSpeech(speeches)?.id).toBe("e2");
  });

  it("findInProgressSpeech ignores done/error", () => {
    expect(findInProgressSpeech([speech({ status: "done" })])).toBeNull();
    expect(findInProgressSpeech([speech({ status: "transcribing" })])).not.toBeNull();
  });
});

describe("quick start", () => {
  it("offers the five PF speech types", () => {
    expect(QUICK_START_OPTIONS.map((o) => o.type)).toEqual([
      "constructive",
      "rebuttal",
      "summary",
      "final_focus",
      "crossfire",
    ]);
  });

  it("deep-links the chosen type into setup", () => {
    expect(quickStartHref("rebuttal")).toBe("/session?type=rebuttal");
  });
});

describe("formatSkill", () => {
  it("humanizes snake/kebab skill keys", () => {
    expect(formatSkill("warrant_quality")).toBe("warrant quality");
    expect(formatSkill("judge-adaptation")).toBe("judge adaptation");
  });
});
