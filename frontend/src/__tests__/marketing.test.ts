import {
  MARKETING_NAV_LINKS,
  HOME_PROOF_POINTS,
  WORKFLOW_STEPS,
  TRUST_POINTS,
  SUPPORTED_TODAY,
  CURRENTLY_EXPLORING,
  isInternalTarget,
  hasBannedRoadmapLanguage,
  HOME_ANCHORS,
} from "@/lib/marketing";
import { MARKETING_FOOTER } from "@/components/marketing/MarketingFooter";

describe("isInternalTarget", () => {
  it("accepts on-page anchors the homepage defines", () => {
    for (const a of HOME_ANCHORS) expect(isInternalTarget(a)).toBe(true);
  });

  it("accepts existing routes and nested routes", () => {
    expect(isInternalTarget("/login")).toBe(true);
    expect(isInternalTarget("/evidence")).toBe(true);
    expect(isInternalTarget("/speech/abc123")).toBe(true);
    expect(isInternalTarget("/")).toBe(true);
  });

  it("rejects routes that do not exist", () => {
    expect(isInternalTarget("/privacy")).toBe(false);
    expect(isInternalTarget("/terms")).toBe(false);
    expect(isInternalTarget("/changelog")).toBe(false);
    expect(isInternalTarget("#nonexistent-anchor")).toBe(false);
  });
});

describe("marketing nav + footer link targets", () => {
  it("nav links all point at something real", () => {
    for (const link of MARKETING_NAV_LINKS) {
      expect(isInternalTarget(link.href)).toBe(true);
    }
  });

  it("footer links all point at something real", () => {
    for (const group of MARKETING_FOOTER) {
      for (const link of group.links) {
        expect(isInternalTarget(link.href)).toBe(true);
      }
    }
  });

  it("footer groups are non-empty and labeled", () => {
    expect(MARKETING_FOOTER.length).toBeGreaterThan(0);
    for (const group of MARKETING_FOOTER) {
      expect(group.label.length).toBeGreaterThan(0);
      expect(group.links.length).toBeGreaterThan(0);
    }
  });
});

describe("no stale roadmap language (anti-vibe gate)", () => {
  it("supported-today copy never claims shipped features are coming", () => {
    for (const cap of SUPPORTED_TODAY) {
      expect(hasBannedRoadmapLanguage(cap.title)).toBe(false);
      expect(hasBannedRoadmapLanguage(cap.body)).toBe(false);
    }
  });

  it("nav, proof, workflow, and trust copy avoid roadmap language", () => {
    const blobs = [
      ...MARKETING_NAV_LINKS.map((l) => l.label),
      ...HOME_PROOF_POINTS.map((p) => `${p.value} ${p.label}`),
      ...WORKFLOW_STEPS.map((s) => `${s.label} ${s.blurb}`),
      ...TRUST_POINTS.map((t) => `${t.title} ${t.body}`),
      CURRENTLY_EXPLORING,
    ];
    for (const b of blobs) expect(hasBannedRoadmapLanguage(b)).toBe(false);
  });
});

describe("supported-today integrity", () => {
  it("is non-empty and every capability links somewhere real", () => {
    expect(SUPPORTED_TODAY.length).toBeGreaterThan(0);
    for (const cap of SUPPORTED_TODAY) {
      expect(cap.title.length).toBeGreaterThan(0);
      expect(isInternalTarget(cap.href)).toBe(true);
    }
  });
});

describe("workflow rail reveals distinct steps", () => {
  it("has unique keys and the full Speak→Improve loop", () => {
    const keys = WORKFLOW_STEPS.map((s) => s.key);
    expect(new Set(keys).size).toBe(keys.length);
    expect(keys).toEqual(["speak", "flow", "ballot", "drill", "improve"]);
  });

  it("blurbs are distinct (no repeated sample)", () => {
    const blurbs = WORKFLOW_STEPS.map((s) => s.blurb);
    expect(new Set(blurbs).size).toBe(blurbs.length);
  });
});
