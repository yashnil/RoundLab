import {
  SPEECH_TYPE_INFO,
  JUDGE_TYPE_INFO,
  SPEECH_TYPE_ORDER,
  JUDGE_TYPE_ORDER,
  getSpeechTypeInfo,
  getJudgeTypeInfo,
  formatSpeechTarget,
  setupCtaLabel,
  readLastJudgeType,
  LAST_JUDGE_KEY,
} from "@/lib/practiceSetup";

describe("speech type info", () => {
  it("covers the five PF speech types in round order", () => {
    expect(SPEECH_TYPE_ORDER).toEqual([
      "constructive",
      "rebuttal",
      "summary",
      "final_focus",
      "crossfire",
    ]);
    SPEECH_TYPE_ORDER.forEach((t) => {
      expect(SPEECH_TYPE_INFO[t].purpose.length).toBeGreaterThan(0);
      expect(SPEECH_TYPE_INFO[t].targetSeconds).toBeGreaterThan(0);
    });
  });

  it("marks opponent context useful for rebuttal/summary/final focus, not constructive", () => {
    expect(SPEECH_TYPE_INFO.constructive.opponentContextUseful).toBe(false);
    expect(SPEECH_TYPE_INFO.rebuttal.opponentContextUseful).toBe(true);
    expect(SPEECH_TYPE_INFO.final_focus.opponentContextUseful).toBe(true);
  });

  it("getSpeechTypeInfo returns null for unknown types", () => {
    expect(getSpeechTypeInfo("constructive")?.label).toBe("Constructive");
    expect(getSpeechTypeInfo("nonsense")).toBeNull();
  });

  it("every speech type has a strategic goal for the rich selector", () => {
    SPEECH_TYPE_ORDER.forEach((t) => {
      expect(SPEECH_TYPE_INFO[t].strategicGoal.length).toBeGreaterThan(0);
    });
  });
});

describe("judge type info", () => {
  it("covers lay/flow/tech/coach with descriptions", () => {
    expect(JUDGE_TYPE_ORDER).toEqual(["lay", "flow", "tech", "coach"]);
    JUDGE_TYPE_ORDER.forEach((j) => {
      expect(JUDGE_TYPE_INFO[j].description.length).toBeGreaterThan(0);
    });
  });

  it("getJudgeTypeInfo returns null for unknown judges", () => {
    expect(getJudgeTypeInfo("flow")?.label).toBe("Flow judge");
    expect(getJudgeTypeInfo("")).toBeNull();
  });

  it("every judge lens has rewards, punishes, and emphasis for the selector + preview", () => {
    JUDGE_TYPE_ORDER.forEach((j) => {
      expect(JUDGE_TYPE_INFO[j].rewards.length).toBeGreaterThan(0);
      expect(JUDGE_TYPE_INFO[j].punishes.length).toBeGreaterThan(0);
      expect(JUDGE_TYPE_INFO[j].emphasis.length).toBeGreaterThan(0);
    });
  });
});

describe("formatSpeechTarget", () => {
  it("formats seconds as m:ss", () => {
    expect(formatSpeechTarget(240)).toBe("4:00");
    expect(formatSpeechTarget(180)).toBe("3:00");
    expect(formatSpeechTarget(120)).toBe("2:00");
    expect(formatSpeechTarget(95)).toBe("1:35");
  });
});

describe("setupCtaLabel", () => {
  it("is input-method/mode aware", () => {
    expect(setupCtaLabel(false)).toBe("Open recorder");
    expect(setupCtaLabel(true)).toBe("Start re-record");
  });
});

describe("smart defaults (SSR-safe)", () => {
  it("exposes a stable storage key and defaults to empty without a window", () => {
    expect(LAST_JUDGE_KEY).toBe("roundlab-last-judge");
    expect(typeof window).toBe("undefined");
    expect(readLastJudgeType()).toBe("");
  });
});
