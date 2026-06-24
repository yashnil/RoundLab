/**
 * Pass 16.5 — Source-level and type-structure tests.
 *
 * Verifies:
 * - No PLACEHOLDER_USER_ID anywhere in round code
 * - No raw fetch() in components that should use roundApi
 * - roundApi exports are all functions
 * - RoundPhaseHeader accepts phaseStartedAt prop (via source check)
 * - RoundSpeechCapture uses useRecorder and roundApi (source check)
 * - Round page auth gate present (source check)
 * - Adaptation review types exported
 * - StudentCrossfireQA type exported
 * - phase_started_at in RoundStateResponse type
 */

import fs from "fs";
import path from "path";

// ── Helpers ────────────────────────────────────────────────────────────────

const SRC = path.resolve(__dirname, "..");

function readSrc(rel: string): string {
  return fs.readFileSync(path.join(SRC, rel), "utf8");
}

// ── No placeholder user IDs ────────────────────────────────────────────────

describe("No PLACEHOLDER_USER_ID in round simulation code", () => {
  const roundFiles = [
    "app/round-simulation/page.tsx",
    "lib/roundApi.ts",
    "components/round/RoundSpeechCapture.tsx",
    "components/round/RoundPhaseHeader.tsx",
  ];

  for (const file of roundFiles) {
    it(`${file} has no PLACEHOLDER_USER_ID`, () => {
      const src = readSrc(file);
      expect(src).not.toContain("PLACEHOLDER_USER_ID");
      expect(src).not.toContain("placeholder-user-id");
    });
  }
});

// ── No raw fetch() in components ───────────────────────────────────────────

describe("Components use roundApi instead of raw fetch()", () => {
  it("RoundSpeechCapture does not use raw fetch()", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).not.toMatch(/\bfetch\(/);
  });

  it("RoundSpeechCapture imports roundApi", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain("roundApi");
  });

  it("round page does not use raw fetch()", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).not.toMatch(/\bfetch\(/);
  });

  it("round page imports roundApi", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("roundApi");
  });

  it("roundApi.ts does not use raw fetch()", () => {
    const src = readSrc("lib/roundApi.ts");
    expect(src).not.toMatch(/\bfetch\(/);
  });
});

// ── roundApi structure ─────────────────────────────────────────────────────

describe("roundApi exported function signatures", () => {
  const src = readSrc("lib/roundApi.ts");

  const expectedFunctions = [
    "createRound",
    "getRoundState",
    "startRound",
    "pauseRound",
    "resumeRound",
    "listRounds",
    "submitStudentSpeech",
    "generateOpponentSpeech",
    "getCrossfireQuestion",
    "submitCrossfireAnswer",
    "submitStudentCrossfireQuestion",
    "advancePhase",
    "generateDecision",
    "rejudgeRound",
    "generateDrills",
    "getRoundDrills",
    "getRoundFlow",
    "getEvidenceReport",
    "createAdaptationReview",
    "listAdaptationReviews",
  ];

  for (const fn of expectedFunctions) {
    it(`exports ${fn}`, () => {
      expect(src).toContain(`export function ${fn}`);
    });
  }

  it("does not pass user_id from frontend to request bodies", () => {
    // user_id should never be sent as a field — it comes from the JWT
    expect(src).not.toMatch(/user_id:\s*\w/);
  });
});

// ── roundApi idempotency key ───────────────────────────────────────────────

describe("roundApi idempotency key forwarding", () => {
  it("submitStudentSpeech includes idempotency_key in body", () => {
    const src = readSrc("lib/roundApi.ts");
    const fnStart = src.indexOf("function submitStudentSpeech");
    const fnEnd = src.indexOf("export function", fnStart + 1);
    const fnSrc = src.slice(fnStart, fnEnd);
    expect(fnSrc).toContain("idempotency_key");
  });

  it("generateOpponentSpeech includes idempotency_key in body", () => {
    const src = readSrc("lib/roundApi.ts");
    const fnStart = src.indexOf("function generateOpponentSpeech");
    const fnEnd = src.indexOf("export function", fnStart + 1);
    const fnSrc = src.slice(fnStart, fnEnd);
    expect(fnSrc).toContain("idempotency_key");
  });
});

// ── RoundPhaseHeader phaseStartedAt ───────────────────────────────────────

describe("RoundPhaseHeader phaseStartedAt prop", () => {
  it("RoundPhaseHeader accepts phaseStartedAt in Props interface", () => {
    const src = readSrc("components/round/RoundPhaseHeader.tsx");
    expect(src).toContain("phaseStartedAt");
  });

  it("RoundPhaseHeader uses phaseStartedAt for server-anchored timer", () => {
    const src = readSrc("components/round/RoundPhaseHeader.tsx");
    expect(src).toContain("elapsedFromServer");
  });

  it("RoundPhaseHeader shows 'Time check' warning badge", () => {
    const src = readSrc("components/round/RoundPhaseHeader.tsx");
    expect(src).toContain("Time check");
  });

  it("RoundPhaseHeader shows 'Over time' badge", () => {
    const src = readSrc("components/round/RoundPhaseHeader.tsx");
    expect(src).toContain("Over time");
  });

  it("RoundPhaseHeader has no auto-submit logic on timer expiry", () => {
    const src = readSrc("components/round/RoundPhaseHeader.tsx");
    // No auto-submit on time expiry
    expect(src).not.toContain("onSpeechSubmitted");
    expect(src).not.toContain("handleSubmit");
  });

  it("RoundPhaseHeader Sync button re-anchors to server time", () => {
    const src = readSrc("components/round/RoundPhaseHeader.tsx");
    expect(src).toContain("Sync");
    expect(src).toContain("elapsedFromServer");
  });
});

// ── RoundSpeechCapture recorder integration ────────────────────────────────

describe("RoundSpeechCapture recorder integration", () => {
  it("imports useRecorder hook", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain("useRecorder");
  });

  it("has Record tab in mode selection", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain('"record"');
  });

  it("has Type tab", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain('"type"');
  });

  it("has Paste tab", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain('"paste"');
  });

  it("includes idempotency key on speech submission", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    // Component passes camelCase idempotencyKey to roundApi; roundApi converts to idempotency_key
    expect(src).toContain("idempotencyKey");
  });

  it("handles permission denial with fallback message", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    // Uses errorKind === "permission" (not a literal "permission-denied" status string)
    expect(src).toContain("isPermissionError");
    expect(src).toContain("Try again");
  });

  it("has Re-record button for replacing a recording", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain("Re-record");
  });

  it("uploads audio to Supabase storage before submitting", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain("uploadAudioBlob");
    expect(src).toContain("speech-audio");
  });

  it("uses a double-submit guard ref", () => {
    const src = readSrc("components/round/RoundSpeechCapture.tsx");
    expect(src).toContain("submittedKeyRef");
  });
});

// ── Round page auth gate ───────────────────────────────────────────────────

describe("Round simulation page auth gate", () => {
  it("page checks Supabase session before showing round UI", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("auth.getSession");
  });

  it("page shows loading state while auth is being determined", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain('"loading"');
    expect(src).toContain("Loading");
  });

  it("page shows sign-in prompt when signed out", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain('"signed-out"');
    expect(src).toContain("Sign in");
  });

  it("page recovers active round from localStorage", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("roundlab_active_round");
    expect(src).toContain("localStorage");
  });

  it("page clears localStorage when round is completed or not found", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("localStorage.removeItem");
  });

  it("page saves round id to localStorage on creation", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("localStorage.setItem");
  });

  it("page subscribes to auth state changes", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("onAuthStateChange");
  });

  it("page unsubscribes from auth on unmount", () => {
    const src = readSrc("app/round-simulation/page.tsx");
    expect(src).toContain("unsubscribe");
  });
});

// ── Type definitions ───────────────────────────────────────────────────────

describe("Round type definitions for Pass 16.5", () => {
  it("RoundStateResponse has phase_started_at field", () => {
    const src = readSrc("types/round.ts");
    // Find the RoundStateResponse interface
    const start = src.indexOf("interface RoundStateResponse");
    const end = src.indexOf("}", start);
    const iface = src.slice(start, end);
    expect(iface).toContain("phase_started_at");
  });

  it("RoundAdaptationReview interface exported", () => {
    const src = readSrc("types/round.ts");
    expect(src).toContain("interface RoundAdaptationReview");
  });

  it("RoundAdaptationReview has adaptation_successes and adaptation_failures", () => {
    const src = readSrc("types/round.ts");
    const start = src.indexOf("interface RoundAdaptationReview");
    const end = src.indexOf("}", start);
    const iface = src.slice(start, end);
    expect(iface).toContain("adaptation_successes");
    expect(iface).toContain("adaptation_failures");
  });

  it("StudentCrossfireQA interface exported", () => {
    const src = readSrc("types/round.ts");
    expect(src).toContain("interface StudentCrossfireQA");
  });

  it("CrossfireExchange interface has questioner_side field", () => {
    const src = readSrc("types/round.ts");
    const start = src.indexOf("interface CrossfireExchange");
    const end = src.indexOf("}", start);
    const iface = src.slice(start, end);
    expect(iface).toContain("questioner_side");
  });
});

// ── Backend API models (import check) ─────────────────────────────────────

describe("roundApi references correct route paths", () => {
  const src = readSrc("lib/roundApi.ts");

  it("uses /round-simulations as base path", () => {
    expect(src).toContain('"/round-simulations"');
  });

  it("student question route ends in /crossfire/student-question", () => {
    expect(src).toContain("crossfire/student-question");
  });

  it("adaptation review route ends in /adaptation-reviews", () => {
    expect(src).toContain("adaptation-reviews");
  });

  it("pause route ends in /pause", () => {
    expect(src).toContain("/pause");
  });

  it("resume route ends in /resume", () => {
    expect(src).toContain("/resume");
  });
});
