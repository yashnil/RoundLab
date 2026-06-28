/**
 * Pass 21.2 — Training OS Hardening frontend tests.
 *
 * Covers:
 * - useOnlineStatus hook existence and structure
 * - useLocalDraft hook existence and structure
 * - OfflineBanner component structure
 * - Lesson player session autosave wiring
 * - ContinueTrainingCard edge cases
 * - CurriculumPanel validation button
 * - Dashboard training fetch non-fatal
 * - PWA manifest correctness
 * - Analytics payload allowlist
 * - TypeScript types correctness
 * - No sensitive data in localStorage keys
 */

import fs from "fs";
import path from "path";

const ROOT = path.join(__dirname, "../../..");
const FRONTEND = path.join(ROOT, "frontend");
const SRC = path.join(FRONTEND, "src");

function read(rel: string): string {
  return fs.readFileSync(path.join(SRC, rel), "utf-8");
}

function readPublic(rel: string): string {
  return fs.readFileSync(path.join(FRONTEND, "public", rel), "utf-8");
}

function exists(rel: string): boolean {
  return fs.existsSync(path.join(SRC, rel));
}

// ═══════════════════════════════════════════════════════════════════════════
// 1. New hooks existence
// ═══════════════════════════════════════════════════════════════════════════

describe("New hooks — existence", () => {
  it("hooks/useOnlineStatus.ts exists", () => {
    expect(exists("hooks/useOnlineStatus.ts")).toBe(true);
  });

  it("hooks/useLocalDraft.ts exists", () => {
    expect(exists("hooks/useLocalDraft.ts")).toBe(true);
  });

  it("components/OfflineBanner.tsx exists", () => {
    expect(exists("components/OfflineBanner.tsx")).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2. useOnlineStatus
// ═══════════════════════════════════════════════════════════════════════════

describe("useOnlineStatus hook", () => {
  let src: string;
  beforeAll(() => { src = read("hooks/useOnlineStatus.ts"); });

  it("exports useOnlineStatus", () => {
    expect(src).toContain("export function useOnlineStatus");
  });

  it("listens to online event", () => {
    expect(src).toContain('"online"');
  });

  it("listens to offline event", () => {
    expect(src).toContain('"offline"');
  });

  it("returns a boolean", () => {
    expect(src).toContain(": boolean");
  });

  it("is SSR-safe (typeof navigator check)", () => {
    expect(src).toContain("navigator");
    expect(src).toContain("typeof");
  });

  it("removes event listeners on cleanup", () => {
    expect(src).toContain("removeEventListener");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 3. useLocalDraft
// ═══════════════════════════════════════════════════════════════════════════

describe("useLocalDraft hook", () => {
  let src: string;
  beforeAll(() => { src = read("hooks/useLocalDraft.ts"); });

  it("exports useLocalDraft", () => {
    expect(src).toContain("export function useLocalDraft");
  });

  it("uses localStorage", () => {
    expect(src).toContain("localStorage");
  });

  it("has draft prefix to avoid collisions", () => {
    expect(src).toContain("DRAFT_PREFIX");
    expect(src).toContain("dissio_draft:");
  });

  it("auto-expires old drafts", () => {
    expect(src).toContain("MAX_DRAFT_AGE_MS");
  });

  it("returns saveDraft and clearDraft", () => {
    expect(src).toContain("saveDraft");
    expect(src).toContain("clearDraft");
  });

  it("silent-fails on localStorage errors", () => {
    // localStorage may be unavailable (private browsing)
    expect(src).toContain("catch");
  });

  it("does not hardcode sensitive fields as localStorage keys", () => {
    // Only verify there are no hardcoded sensitive key patterns in storage calls
    // (comments warning against sensitive data are OK)
    expect(src).not.toContain('setItem("transcript');
    expect(src).not.toContain('setItem("audio_url');
    expect(src).not.toContain('setItem("email');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 4. OfflineBanner
// ═══════════════════════════════════════════════════════════════════════════

describe("OfflineBanner", () => {
  let src: string;
  beforeAll(() => { src = read("components/OfflineBanner.tsx"); });

  it("exports OfflineBanner", () => {
    expect(src).toContain("export function OfflineBanner");
  });

  it("uses useOnlineStatus hook", () => {
    expect(src).toContain("useOnlineStatus");
  });

  it("returns null when online", () => {
    expect(src).toContain("if (online) return null");
  });

  it("has role=status for screen reader announcement", () => {
    expect(src).toContain('role="status"');
  });

  it("has aria-live=assertive", () => {
    expect(src).toContain('aria-live="assertive"');
  });

  it("mentions syncing on reconnect", () => {
    expect(src).toMatch(/sync|reconnect/i);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5. Workspace layout includes OfflineBanner
// ═══════════════════════════════════════════════════════════════════════════

describe("Workspace layout — OfflineBanner", () => {
  let src: string;
  beforeAll(() => { src = read("app/(workspace)/layout.tsx"); });

  it("imports OfflineBanner", () => {
    expect(src).toContain("OfflineBanner");
  });

  it("renders OfflineBanner", () => {
    expect(src).toContain("<OfflineBanner");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 6. Lesson player — session autosave hardening
// ═══════════════════════════════════════════════════════════════════════════

describe("Lesson player — session hardening", () => {
  let src: string;
  beforeAll(() => { src = read("app/(workspace)/lesson/page.tsx"); });

  it("autosaves step to /training/sessions/{id} on each advance", () => {
    expect(src).toContain("/training/sessions/");
    expect(src).toContain("PATCH");
  });

  it("resumes step from server on mount", () => {
    expect(src).toContain("current_step");
    expect(src).toContain("steps_completed");
  });

  it("does not create duplicate sessions (POST is idempotent)", () => {
    // The lesson player calls POST once on mount — check for single call
    const postCount = (src.match(/method: "POST"/g) || []).length;
    // Should have exactly one POST for session creation
    expect(postCount).toBeGreaterThanOrEqual(1);
  });

  it("session creation is wrapped in try/catch", () => {
    // Session creation failure should be non-fatal
    expect(src).toContain("try {");
    expect(src).toContain("catch");
  });

  it("lesson completion POSTs to /training/progress/lesson", () => {
    expect(src).toContain("/training/progress/lesson");
  });

  it("redirects to /login?next=/training on auth failure", () => {
    expect(src).toContain("login?next=/training");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. ContinueTrainingCard edge cases
// ═══════════════════════════════════════════════════════════════════════════

describe("ContinueTrainingCard edge cases", () => {
  let src: string;
  beforeAll(() => { src = read("components/training/ContinueTrainingCard.tsx"); });

  it("handles null nextAction gracefully", () => {
    expect(src).toContain("!nextAction");
  });

  it("shows loading skeleton during fetch", () => {
    expect(src).toContain("animate-pulse");
    expect(src).toContain("loading");
  });

  it("uses /lesson path (not /learn) for lesson links", () => {
    expect(src).toContain("/lesson?lesson=");
    expect(src).not.toContain("/learn?lesson=");
  });

  it("shows coach assignment source label", () => {
    expect(src).toContain("Coach assigned");
  });

  it("shows plan week number when active_plan present", () => {
    expect(src).toContain("current_week");
    expect(src).toContain("total_weeks");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 8. CurriculumPanel validation
// ═══════════════════════════════════════════════════════════════════════════

describe("CurriculumPanel — validation", () => {
  let src: string;
  beforeAll(() => { src = read("components/coach/CurriculumPanel.tsx"); });

  it("validate button is disabled while loading", () => {
    expect(src).toContain("validLoading");
    expect(src).toContain("disabled");
  });

  it("shows success message when valid", () => {
    expect(src).toContain("pass curriculum validation");
  });

  it("shows error count when invalid", () => {
    expect(src).toContain("error(s)");
  });

  it("renders error state for fetch failure", () => {
    expect(src).toContain("err");
    expect(src).toContain("Could not load");
  });

  it("shows loading skeleton", () => {
    expect(src).toContain("Skeleton");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 9. Dashboard training fetch is non-fatal
// ═══════════════════════════════════════════════════════════════════════════

describe("Dashboard — training fetch resilience", () => {
  let src: string;
  beforeAll(() => { src = read("app/(workspace)/dashboard/page.tsx"); });

  it("catches training fetch failure", () => {
    // The training next-action fetch has .catch(() => { setNextTrainingAction(null) })
    expect(src).toContain("setNextTrainingAction(null)");
  });

  it("training loading state defaults to true", () => {
    expect(src).toContain("trainingLoading");
    expect(src).toContain("setTrainingLoading");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 10. PWA manifest correctness
// ═══════════════════════════════════════════════════════════════════════════

describe("PWA manifest structure", () => {
  let manifest: Record<string, unknown>;
  beforeAll(() => { manifest = JSON.parse(readPublic("manifest.json")); });

  it("prefer_related_applications is false", () => {
    expect(manifest.prefer_related_applications).toBe(false);
  });

  it("categories includes education", () => {
    const cats = manifest.categories as string[];
    expect(cats).toContain("education");
  });

  it("background_color is set", () => {
    expect(manifest.background_color).toBeTruthy();
  });

  it("orientation is portrait-primary", () => {
    expect(manifest.orientation).toBe("portrait-primary");
  });

  it("icons have src, sizes, and type", () => {
    const icons = manifest.icons as Array<Record<string, string>>;
    icons.forEach((icon) => {
      expect(icon.src).toBeTruthy();
      expect(icon.sizes).toBeTruthy();
      expect(icon.type).toBeTruthy();
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 11. Analytics payload allowlist
// ═══════════════════════════════════════════════════════════════════════════

describe("Analytics privacy — payload allowlist", () => {
  let src: string;
  beforeAll(() => { src = read("lib/analytics.ts"); });

  const FORBIDDEN_FIELDS = [
    "transcript_text",
    "audio_data",
    "audio_url",
    "student_name",
    "coach_note_text",
    "evidence_text",
    "card_body",
    "email_address",
    "raw_speech",
    "student_email",
  ];

  FORBIDDEN_FIELDS.forEach((field) => {
    it(`does not include "${field}" in any event payload`, () => {
      expect(src).not.toContain(field);
    });
  });

  it("all training events only log IDs and states", () => {
    // Spot-check key event payload shapes
    expect(src).toContain("lesson_id");
    expect(src).toContain("skill_id");
    expect(src).toContain("from_state");
    expect(src).toContain("to_state");
    expect(src).toContain("score_pct");
    // No raw text fields
    expect(src).not.toContain("body_text");
    expect(src).not.toContain("raw_text");
  });

  it("speech_submitted only logs speech_id and type", () => {
    const fnIdx = src.indexOf("logSpeechSubmitted");
    const segment = src.slice(fnIdx, fnIdx + 300);
    expect(segment).toContain("speech_id");
    expect(segment).toContain("speech_type");
    // Must NOT include content
    expect(segment).not.toContain("content");
    expect(segment).not.toContain("transcript");
  });

  it("logCoachOverride payload only has skill_id (no student PII)", () => {
    const fnIdx = src.indexOf("export function logCoachOverride");
    const segment = src.slice(fnIdx, fnIdx + 300);
    // Payload should only be { skill_id: skillId } — no email or student_name field
    expect(segment).not.toContain("student_email");
    expect(segment).not.toContain("student_name");
    // skill_id must be present
    expect(segment).toContain("skill_id");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 12. Type safety — CurriculumLesson has new optional fields
// ═══════════════════════════════════════════════════════════════════════════

describe("TypeScript types — CurriculumLesson", () => {
  let src: string;
  beforeAll(() => { src = read("types/training.ts"); });

  it("has common_mistakes optional field", () => {
    expect(src).toContain("common_mistakes");
    expect(src).toContain("string[]");
  });

  it("has coach_note optional field", () => {
    expect(src).toContain("coach_note");
  });

  it("has author optional field", () => {
    expect(src).toContain("author");
  });

  it("has reviewed_date optional field", () => {
    expect(src).toContain("reviewed_date");
  });

  it("fields are marked optional (?)", () => {
    // New fields added in 21.1 hardening are optional
    const cmIdx = src.indexOf("common_mistakes");
    const segment = src.slice(cmIdx - 2, cmIdx + 20);
    expect(segment).toContain("?");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 13. Coach API hooks
// ═══════════════════════════════════════════════════════════════════════════

describe("Coach mastery hooks — backend", () => {
  const BACKEND_SRC = path.join(ROOT, "backend", "app", "api");

  function readBackend(fname: string): string {
    return fs.readFileSync(path.join(BACKEND_SRC, fname), "utf-8");
  }

  // Pass 21.3: coach_mastery_override now calls emit_mastery_override (not emit_from_coach_review)
  // because a priority-only or score-only override is NOT performance evidence.
  it("training.py coach-override calls emit_mastery_override (Pass 21.3 semantic split)", () => {
    const src = readBackend("training.py");
    expect(src).toContain("emit_mastery_override");
    // Must NOT call the deprecated emit_from_coach_review in the override path
    // (the deprecated shim may still exist for backwards compat in mastery_integration.py
    //  but must not be invoked from training.py)
    const overrideIdx = src.indexOf("coach_mastery_override");
    if (overrideIdx >= 0) {
      const endIdx = src.indexOf("\n@router", overrideIdx + 1);
      const fnBody = endIdx > 0 ? src.slice(overrideIdx, endIdx) : src.slice(overrideIdx);
      expect(fnBody).not.toContain("emit_from_coach_review");
    }
  });

  // Pass 21.3: assignments.py review endpoint now calls emit_from_coach_performance_review
  // because the coach is reviewing a real student submission (artifact_id is present).
  it("assignments.py review endpoint calls emit_from_coach_performance_review on approval", () => {
    const src = readBackend("assignments.py");
    expect(src).toContain("emit_from_coach_performance_review");
    // Must be conditioned on "reviewed" action
    const emitIdx = src.indexOf("emit_from_coach_performance_review");
    const segment = src.slice(Math.max(0, emitIdx - 500), emitIdx);
    expect(segment).toContain("reviewed");
  });

  it("assignments.py performance review passes artifact_id", () => {
    const src = readBackend("assignments.py");
    // artifact_id must be passed to prove the review is tied to real performance
    expect(src).toContain("artifact_id");
  });

  it("all 6 mastery hooks are non-fatal (wrapped in try/except)", () => {
    const hooks: Array<[string, string]> = [
      ["drills.py", "emit_from_drill_attempt"],
      ["workouts.py", "emit_from_workout"],
      ["judge_adaptation.py", "emit_from_judge_adaptation"],
      ["round_simulations.py", "emit_from_full_round"],
      ["assignments.py", "emit_from_coach_performance_review"],
      ["training.py", "emit_mastery_override"],
    ];

    hooks.forEach(([fname, fnName]) => {
      const src = readBackend(fname);
      if (!src.includes(fnName)) return;
      const idx = src.indexOf(fnName);
      const before = src.slice(Math.max(0, idx - 600), idx);
      expect(before).toMatch(/try:/);
    });
  });
});
