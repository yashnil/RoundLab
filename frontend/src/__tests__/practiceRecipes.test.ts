import {
  PRACTICE_RECIPES,
  recipeHref,
  recipesByGroup,
} from "@/lib/practiceRecipes";
import { SPEECH_TYPE_INFO, JUDGE_TYPE_INFO } from "@/lib/practiceSetup";

describe("PRACTICE_RECIPES", () => {
  it("has unique ids", () => {
    const ids = PRACTICE_RECIPES.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("uses only real speech types and judge lenses", () => {
    for (const r of PRACTICE_RECIPES) {
      expect(r.type in SPEECH_TYPE_INFO).toBe(true);
      if (r.judge) expect(r.judge in JUDGE_TYPE_INFO).toBe(true);
    }
  });

  it("covers both full and quick groups", () => {
    expect(recipesByGroup("full").length).toBeGreaterThan(0);
    expect(recipesByGroup("quick").length).toBeGreaterThan(0);
    expect(recipesByGroup("full").length + recipesByGroup("quick").length).toBe(
      PRACTICE_RECIPES.length,
    );
  });

  it("includes the headline recipes from the spec", () => {
    const ids = PRACTICE_RECIPES.map((r) => r.id);
    expect(ids).toEqual(
      expect.arrayContaining([
        "full-constructive",
        "rebuttal-clash",
        "summary-collapse",
        "final-focus-voter",
        "warrant-repair",
        "weighing-sprint",
        "lay-explanation",
        "evidence-attribution",
      ]),
    );
  });
});

describe("recipeHref", () => {
  it("always deep-links into /session with the speech type", () => {
    for (const r of PRACTICE_RECIPES) {
      const href = recipeHref(r);
      expect(href.startsWith("/session?")).toBe(true);
      const params = new URLSearchParams(href.split("?")[1]);
      expect(params.get("type")).toBe(r.type);
    }
  });

  it("encodes judge, side, and goal presets when present", () => {
    const recipe = PRACTICE_RECIPES.find((r) => r.id === "full-constructive")!;
    const params = new URLSearchParams(recipeHref(recipe).split("?")[1]);
    expect(params.get("judge")).toBe("flow");
    expect(params.get("goal")).toBe(recipe.goal);
  });

  it("never produces a goal param for a recipe without a goal", () => {
    const noGoal = { ...PRACTICE_RECIPES[0], goal: undefined };
    const params = new URLSearchParams(recipeHref(noGoal).split("?")[1]);
    expect(params.has("goal")).toBe(false);
  });
});
