import { deriveCoachingFocus, SKILL_META } from "@/lib/coachingFocus";
import type { SkillAverages } from "@/types";

const skills: SkillAverages = {
  clash: 7,
  weighing: 4,
  extensions: 6,
  drops: 8,
  judge_adaptation: 5,
};

describe("deriveCoachingFocus", () => {
  it("picks the lowest-scoring skill as the focus", () => {
    const f = deriveCoachingFocus(skills, 3);
    expect(f?.skill).toBe("weighing");
    expect(f?.label).toBe("Weighing");
    expect(f?.score).toBe(4);
    expect(f?.why.length).toBeGreaterThan(0);
    expect(f?.suggestion.length).toBeGreaterThan(0);
  });

  it("returns null when there is no feedback yet", () => {
    expect(deriveCoachingFocus(skills, 0)).toBeNull();
  });

  it("returns null when skill averages are missing", () => {
    expect(deriveCoachingFocus(null, 5)).toBeNull();
  });

  it("covers all five PF skill dimensions", () => {
    expect(Object.keys(SKILL_META).sort()).toEqual(
      ["clash", "drops", "extensions", "judge_adaptation", "weighing"],
    );
  });
});
