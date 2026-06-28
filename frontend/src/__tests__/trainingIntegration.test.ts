/**
 * Pass 21.1 — Training OS Integration frontend tests.
 *
 * These tests verify:
 * - All new files exist
 * - Key exports are present
 * - Lesson player page structure
 * - ContinueTrainingCard renders expected states
 * - Dashboard integration wiring
 * - Coach Curriculum panel exists
 * - Analytics events are defined
 * - PWA manifest
 * - navItems includes training
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

function existsPublic(rel: string): boolean {
  return fs.existsSync(path.join(FRONTEND, "public", rel));
}

// ═══════════════════════════════════════════════════════════════════════════
// 1. File existence
// ═══════════════════════════════════════════════════════════════════════════

describe("File existence — Pass 21.1", () => {
  const required = [
    "components/training/ContinueTrainingCard.tsx",
    "app/(workspace)/lesson/page.tsx",
  ];

  required.forEach((rel) => {
    it(`${rel} exists`, () => {
      expect(exists(rel)).toBe(true);
    });
  });

  it("manifest.json exists in public/", () => {
    expect(existsPublic("manifest.json")).toBe(true);
  });

  it("coach/CurriculumPanel.tsx exists", () => {
    expect(exists("components/coach/CurriculumPanel.tsx")).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2. PWA manifest
// ═══════════════════════════════════════════════════════════════════════════

describe("PWA manifest", () => {
  let manifest: Record<string, unknown>;

  beforeAll(() => {
    manifest = JSON.parse(readPublic("manifest.json"));
  });

  it("has name = Dissio", () => {
    expect(manifest.name).toBe("Dissio");
  });

  it("has start_url = /training", () => {
    expect(manifest.start_url).toBe("/training");
  });

  it("has display = standalone", () => {
    expect(manifest.display).toBe("standalone");
  });

  it("has theme_color", () => {
    expect(manifest.theme_color).toBeTruthy();
  });

  it("has icons array", () => {
    expect(Array.isArray(manifest.icons)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 3. layout.tsx — PWA meta
// ═══════════════════════════════════════════════════════════════════════════

describe("layout.tsx PWA integration", () => {
  let src: string;

  beforeAll(() => {
    src = read("app/layout.tsx");
  });

  it("includes manifest reference", () => {
    expect(src).toMatch(/manifest/i);
  });

  it("includes appleWebApp or apple-mobile-web-app", () => {
    expect(src).toMatch(/apple/i);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 4. ContinueTrainingCard
// ═══════════════════════════════════════════════════════════════════════════

describe("ContinueTrainingCard", () => {
  let src: string;

  beforeAll(() => {
    src = read("components/training/ContinueTrainingCard.tsx");
  });

  it("exports ContinueTrainingCard", () => {
    expect(src).toContain("export function ContinueTrainingCard");
  });

  it("handles null nextAction (start plan state)", () => {
    expect(src).toContain("Start your training plan");
  });

  it("links to /lesson for lesson_id", () => {
    expect(src).toContain("/lesson?lesson=");
  });

  it("links to /training as fallback", () => {
    expect(src).toContain('href="/training"');
  });

  it("shows loading skeleton", () => {
    expect(src).toContain("animate-pulse");
  });

  it("renders plan week info when active_plan present", () => {
    expect(src).toContain("current_week");
  });

  it("has source label mapping", () => {
    expect(src).toContain("training_plan");
    expect(src).toContain("mastery_gap");
    expect(src).toContain("needs_refresh");
  });

  it("has coach_assignment source", () => {
    expect(src).toContain("coach_assignment");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5. Lesson player page
// ═══════════════════════════════════════════════════════════════════════════

describe("Lesson player page (/lesson)", () => {
  let src: string;

  beforeAll(() => {
    src = read("app/(workspace)/lesson/page.tsx");
  });

  it("uses Suspense for searchParams", () => {
    expect(src).toContain("Suspense");
  });

  it("reads lesson from ?lesson= searchParam", () => {
    expect(src).toContain("searchParams.get");
    expect(src).toContain('"lesson"');
  });

  it("redirects unauthenticated users", () => {
    expect(src).toContain("login?next=/training");
  });

  it("fetches lesson from /training/curriculum/lesson/", () => {
    expect(src).toContain("/training/curriculum/lesson/");
  });

  it("calls logLessonStarted", () => {
    expect(src).toContain("logLessonStarted");
  });

  it("calls logLessonCompleted", () => {
    expect(src).toContain("logLessonCompleted");
  });

  it("has session autosave (PATCH /training/sessions)", () => {
    expect(src).toContain("/training/sessions/");
    expect(src).toContain("PATCH");
  });

  it("has session start (POST /training/sessions)", () => {
    expect(src).toContain("/training/sessions");
    expect(src).toContain("POST");
  });

  it("has lesson step 'lesson'", () => {
    expect(src).toContain('"lesson"');
  });

  it("has drill step", () => {
    expect(src).toContain("drill");
  });

  it("has speech step linking to /session", () => {
    expect(src).toContain("/session");
  });

  it("has compare step", () => {
    expect(src).toContain("compare");
  });

  it("marks lesson complete via POST /training/progress/lesson", () => {
    expect(src).toContain("/training/progress/lesson");
  });

  it("shows done state with back-to-training link", () => {
    expect(src).toContain("/training");
  });

  it("shows recommended_next link", () => {
    expect(src).toContain("recommended_next");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 6. Dashboard — Continue Training integration
// ═══════════════════════════════════════════════════════════════════════════

describe("Dashboard — ContinueTrainingCard integration", () => {
  let src: string;

  beforeAll(() => {
    src = read("app/(workspace)/dashboard/page.tsx");
  });

  it("imports ContinueTrainingCard", () => {
    expect(src).toContain("ContinueTrainingCard");
  });

  it("fetches /training/next-action", () => {
    expect(src).toContain("/training/next-action");
  });

  it("has trainingLoading state", () => {
    expect(src).toContain("trainingLoading");
  });

  it("has nextTrainingAction state", () => {
    expect(src).toContain("nextTrainingAction");
  });

  it("renders Continue Training section", () => {
    expect(src).toContain("Continue training");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. Coach Curriculum Panel
// ═══════════════════════════════════════════════════════════════════════════

describe("CurriculumPanel (coach)", () => {
  let src: string;

  beforeAll(() => {
    src = read("components/coach/CurriculumPanel.tsx");
  });

  it("exports default CurriculumPanel", () => {
    expect(src).toContain("export default function CurriculumPanel");
  });

  it("accepts teamId and coachId props", () => {
    expect(src).toContain("teamId");
    expect(src).toContain("coachId");
  });

  it("fetches curriculum from /training/curriculum", () => {
    expect(src).toContain("/training/curriculum");
  });

  it("calls validate endpoint", () => {
    expect(src).toContain("/training/curriculum/validate");
  });

  it("shows validation result", () => {
    expect(src).toContain("validation");
  });

  it("shows lesson list", () => {
    expect(src).toContain("lessons.map");
  });

  it("links to lesson player", () => {
    expect(src).toContain("/lesson?lesson=");
  });

  it("shows student progress", () => {
    expect(src).toContain("progress");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 8. Team page — Curriculum tab added
// ═══════════════════════════════════════════════════════════════════════════

describe("Team page — Curriculum tab", () => {
  let src: string;

  beforeAll(() => {
    src = read("app/(workspace)/team/page.tsx");
  });

  it("imports CurriculumPanel", () => {
    expect(src).toContain("CurriculumPanel");
  });

  it("includes curriculum in Panel type", () => {
    expect(src).toContain('"curriculum"');
  });

  it("renders CurriculumPanel when panel === curriculum", () => {
    expect(src).toContain("panel === \"curriculum\"");
  });

  it("has Curriculum tab button in PANELS", () => {
    expect(src).toContain("Curriculum");
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 9. Analytics — Training OS events
// ═══════════════════════════════════════════════════════════════════════════

describe("Analytics — Training OS events", () => {
  let src: string;

  beforeAll(() => {
    src = read("lib/analytics.ts");
  });

  const events = [
    "logDiagnosticStarted",
    "logDiagnosticCompleted",
    "logLessonStarted",
    "logLessonCompleted",
    "logTrainingDrillStarted",
    "logTrainingDrillCompleted",
    "logSpeechSubmitted",
    "logRerecordCompleted",
    "logPlanResumed",
    "logPlanAbandoned",
    "logCoachOverride",
    "logMasteryStateChange",
    "logUploadFailure",
    "logAnalysisFailure",
  ];

  events.forEach((fn) => {
    it(`exports ${fn}`, () => {
      expect(src).toContain(`export function ${fn}`);
    });
  });

  it("never logs transcript in any event", () => {
    expect(src).not.toMatch(/transcript_text|audio_data|speech_text/);
  });

  it("never logs student names/email directly", () => {
    expect(src).not.toMatch(/student_name|email.*metadata/);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 10. navItems — Training entry
// ═══════════════════════════════════════════════════════════════════════════

describe("navItems — Training entry", () => {
  let src: string;

  beforeAll(() => {
    src = read("lib/navItems.ts");
  });

  it("includes /training route", () => {
    expect(src).toContain('"/training"');
  });

  it("includes /diagnostic in training match", () => {
    expect(src).toContain('"/diagnostic"');
  });

  it("uses GraduationCap or BookOpen icon for training", () => {
    expect(src).toMatch(/GraduationCap|BookOpen/);
  });
});
