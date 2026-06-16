import { computeRmsLevel, smoothLevel, levelToBars } from "@/lib/audioLevel";

describe("computeRmsLevel", () => {
  it("is 0 for silence (all centered at 128)", () => {
    expect(computeRmsLevel(new Uint8Array(64).fill(128))).toBe(0);
  });

  it("is 0 for an empty buffer", () => {
    expect(computeRmsLevel([])).toBe(0);
  });

  it("rises with amplitude and never exceeds 1", () => {
    const quiet = computeRmsLevel([138, 118, 138, 118]);
    const loud = computeRmsLevel([255, 0, 255, 0]);
    expect(quiet).toBeGreaterThan(0);
    expect(loud).toBeGreaterThan(quiet);
    expect(loud).toBeLessThanOrEqual(1);
  });
});

describe("smoothLevel", () => {
  it("eases toward the target", () => {
    expect(smoothLevel(0, 1, 0.5)).toBe(0.5);
    expect(smoothLevel(0.5, 1, 0.5)).toBe(0.75);
  });

  it("clamps the factor", () => {
    expect(smoothLevel(0, 1, 5)).toBe(1);
    expect(smoothLevel(0.4, 1, -1)).toBe(0.4);
  });
});

describe("levelToBars", () => {
  it("maps a level onto N bars", () => {
    expect(levelToBars(0, 10)).toBe(0);
    expect(levelToBars(1, 10)).toBe(10);
    expect(levelToBars(0.55, 10)).toBe(6);
  });
});
