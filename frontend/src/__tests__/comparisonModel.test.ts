import {
  deriveComparisonChanges,
  supportingScores,
  hasMeaningfulChange,
} from "@/lib/comparisonModel";
import type { SpeechComparisonResult } from "@/types";

function cmp(over: Partial<SpeechComparisonResult>): SpeechComparisonResult {
  return {
    has_parent: true,
    parent_speech_id: "p",
    source_drill_id: null,
    source_drill_skill: null,
    original_overall_score: null,
    new_overall_score: null,
    overall_delta: null,
    original_skill_score: null,
    new_skill_score: null,
    skill_delta: null,
    summary: "",
    still_needs_work: null,
    next_action: "",
    ...over,
  };
}

describe("deriveComparisonChanges", () => {
  it("leads with the targeted skill and marks improvement", () => {
    const items = deriveComparisonChanges(cmp({
      source_drill_skill: "impact_weighing",
      original_skill_score: 9,
      new_skill_score: 14,
      skill_delta: 5,
    }));
    expect(items[0].label).toBe("Impact weighing");
    expect(items[0].detail).toBe("9/20 → 14/20");
    expect(items[0].tone).toBe("improved");
  });

  it("reports fewer filler words as improved (lower is better)", () => {
    const items = deriveComparisonChanges(cmp({
      original_filler_count: 12,
      new_filler_count: 5,
      filler_delta: -7,
    }));
    const filler = items.find((i) => i.label === "Filler words")!;
    expect(filler.detail).toBe("12 → 5");
    expect(filler.tone).toBe("improved");
  });

  it("treats pace change as info, not good/bad", () => {
    const items = deriveComparisonChanges(cmp({
      original_wpm: 150, new_wpm: 170, wpm_delta: 20,
    }));
    expect(items.find((i) => i.label === "Speaking pace")!.tone).toBe("info");
  });

  it("reports a decline plainly", () => {
    const items = deriveComparisonChanges(cmp({
      source_drill_skill: "clash", original_skill_score: 15, new_skill_score: 11, skill_delta: -4,
    }));
    expect(items[0].tone).toBe("declined");
  });
});

describe("supportingScores", () => {
  it("exposes the overall ballot as a demoted chip", () => {
    const chips = supportingScores(cmp({ original_overall_score: 70, new_overall_score: 78, overall_delta: 8 }));
    expect(chips).toHaveLength(1);
    expect(chips[0].label).toBe("Overall ballot");
    expect(chips[0].suffix).toBe("/100");
  });

  it("is empty when no overall score exists", () => {
    expect(supportingScores(cmp({}))).toHaveLength(0);
  });
});

describe("hasMeaningfulChange", () => {
  it("is true with a real improved/declined dimension", () => {
    expect(hasMeaningfulChange(cmp({ source_drill_skill: "weighing", skill_delta: 3, original_skill_score: 10, new_skill_score: 13 }))).toBe(true);
  });

  it("is false when only pace (info) changed", () => {
    expect(hasMeaningfulChange(cmp({ original_wpm: 150, new_wpm: 160, wpm_delta: 10 }))).toBe(false);
  });
});
