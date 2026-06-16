import {
  computeProgress,
  phaseForProgress,
} from "@/components/evidence/EvidenceSearchProgress";

describe("computeProgress", () => {
  it("starts at 0", () => {
    expect(computeProgress(0)).toBe(0);
  });

  it("increases over time", () => {
    const a = computeProgress(5_000);
    const b = computeProgress(20_000);
    const c = computeProgress(45_000);
    expect(a).toBeLessThan(b);
    expect(b).toBeLessThan(c);
  });

  it("caps at 98 (never 100 until done)", () => {
    expect(computeProgress(60_000)).toBeLessThanOrEqual(98);
    expect(computeProgress(120_000)).toBeLessThanOrEqual(98);
  });

  it("reaches near 98 around the ~70s duration", () => {
    expect(computeProgress(70_000)).toBe(98);
    expect(computeProgress(90_000)).toBe(98);
  });

  it("defaults to a ~70s duration (not yet maxed at 60s)", () => {
    expect(computeProgress(60_000)).toBeLessThan(98);
  });

  it("respects a custom duration", () => {
    expect(computeProgress(18_000, 18_000)).toBe(98);
  });

  it("is monotonic across the run", () => {
    let prev = -1;
    for (let ms = 0; ms <= 80_000; ms += 2_000) {
      const v = computeProgress(ms);
      expect(v).toBeGreaterThanOrEqual(prev);
      prev = v;
    }
  });
});

describe("phaseForProgress", () => {
  it("starts on Searching credible sources", () => {
    expect(phaseForProgress(0).label).toBe("Searching credible sources");
  });

  it("moves through phases as progress climbs", () => {
    expect(phaseForProgress(20).label).toBe("Opening source pages");
    expect(phaseForProgress(40).label).toBe("Extracting passages");
    expect(phaseForProgress(60).label).toBe("Cutting evidence");
    expect(phaseForProgress(80).label).toBe("Building debate prep");
    expect(phaseForProgress(100).label).toBe("Finalizing cards");
  });

  it("never returns undefined for in-range values", () => {
    for (let p = 0; p <= 100; p += 7) {
      expect(phaseForProgress(p).label).toBeTruthy();
    }
  });
});
