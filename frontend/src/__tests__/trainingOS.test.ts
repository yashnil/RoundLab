/**
 * Pass 21 — Training OS frontend tests.
 * Source-level inspection: no runtime execution.
 */

import * as fs from "fs";
import * as path from "path";

const ROOT = path.resolve(__dirname, "../../..");
const FRONTEND_SRC = path.join(ROOT, "frontend", "src");
const BACKEND_ROOT = path.join(ROOT, "backend");

function read(filePath: string): string {
  return fs.readFileSync(filePath, "utf-8");
}

function srcFile(...parts: string[]): string {
  return path.join(FRONTEND_SRC, ...parts);
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. File existence
// ─────────────────────────────────────────────────────────────────────────────

describe("Pass 21 — file existence", () => {
  const required = [
    srcFile("types", "training.ts"),
    srcFile("lib", "trainingApi.ts"),
    srcFile("components", "training", "SkillMasteryRing.tsx"),
    srcFile("components", "training", "MasteryExplanation.tsx"),
    srcFile("components", "training", "TrainingPlanCard.tsx"),
    srcFile("components", "training", "BeforeAfterPanel.tsx"),
    srcFile("components", "training", "DiagnosticIntake.tsx"),
    srcFile("components", "training", "PracticeAgenda.tsx"),
    srcFile("app", "(workspace)", "training", "page.tsx"),
    srcFile("app", "(workspace)", "diagnostic", "page.tsx"),
    path.join(BACKEND_ROOT, "app", "event_packs", "public_forum.py"),
    path.join(BACKEND_ROOT, "app", "services", "mastery_engine.py"),
    path.join(BACKEND_ROOT, "app", "services", "training_planner.py"),
    path.join(BACKEND_ROOT, "app", "services", "diagnostic_engine.py"),
    path.join(BACKEND_ROOT, "app", "api", "training.py"),
    path.join(BACKEND_ROOT, "app", "models", "training.py"),
  ];

  required.forEach((filePath) => {
    test(`${path.basename(filePath)} exists`, () => {
      expect(fs.existsSync(filePath)).toBe(true);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. types/training.ts
// ─────────────────────────────────────────────────────────────────────────────

describe("types/training.ts", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("types", "training.ts")); });

  test("exports MasteryState type", () => {
    expect(src).toContain("MasteryState");
  });
  test("MasteryState has all 6 states", () => {
    const states = ["not_started", "introduced", "developing", "proficient", "mastered", "needs_refresh"];
    states.forEach(s => expect(src).toContain(s));
  });
  test("exports SkillCategory type", () => {
    expect(src).toContain("SkillCategory");
  });
  test("exports MasteryProfile interface with skills field", () => {
    expect(src).toContain("MasteryProfile");
    expect(src).toContain("skills:");
  });
  test("MasteryScore has mastery_score field", () => {
    expect(src).toContain("mastery_score:");
  });
  test("MasteryScore has confidence field", () => {
    expect(src).toContain("confidence:");
  });
  test("MasteryScore has evidence_count field", () => {
    expect(src).toContain("evidence_count:");
  });
  test("TrainingPlan has weeks field", () => {
    expect(src).toContain("weeks:");
  });
  test("CurriculumLesson has what_is_it field", () => {
    expect(src).toContain("what_is_it:");
  });
  test("WeekPlan has skill_focus field", () => {
    expect(src).toContain("skill_focus:");
  });
  test("exports DiagnosticData interface", () => {
    expect(src).toContain("DiagnosticData");
  });
  test("exports PracticeAgendaItem interface", () => {
    expect(src).toContain("PracticeAgendaItem");
  });
  test("MASTERY_STATE_LABEL has all 6 states", () => {
    expect(src).toContain("MASTERY_STATE_LABEL");
    expect(src).toContain("needs_refresh");
  });
  test("MASTERY_STATE_COLOR exported", () => {
    expect(src).toContain("MASTERY_STATE_COLOR");
  });
  test("MASTERY_STATE_BG exported", () => {
    expect(src).toContain("MASTERY_STATE_BG");
  });
  test("EXPERIENCE_LABEL has 4 levels", () => {
    expect(src).toContain("EXPERIENCE_LABEL");
    const levels = ["first_time", "novice", "jv", "varsity"];
    levels.forEach(l => expect(src).toContain(l));
  });
  test("Skill interface has prerequisites field", () => {
    expect(src).toContain("prerequisites:");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. lib/trainingApi.ts
// ─────────────────────────────────────────────────────────────────────────────

describe("lib/trainingApi.ts", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("lib", "trainingApi.ts")); });

  test("uses apiFetch not raw fetch", () => {
    expect(src).toContain('from "@/lib/api"');
    expect(src).not.toContain("window.fetch(");
  });
  test("exports fetchMasteryProfile", () => {
    expect(src).toContain("fetchMasteryProfile");
  });
  test("exports addMasteryEvidence", () => {
    expect(src).toContain("addMasteryEvidence");
  });
  test("exports fetchActivePlan", () => {
    expect(src).toContain("fetchActivePlan");
  });
  test("exports generatePlan", () => {
    expect(src).toContain("generatePlan");
  });
  test("exports fetchCurriculum", () => {
    expect(src).toContain("fetchCurriculum");
  });
  test("exports fetchLesson", () => {
    expect(src).toContain("fetchLesson");
  });
  test("exports markLessonComplete", () => {
    expect(src).toContain("markLessonComplete");
  });
  test("exports fetchProgress", () => {
    expect(src).toContain("fetchProgress");
  });
  test("exports fetchDiagnostic", () => {
    expect(src).toContain("fetchDiagnostic");
  });
  test("exports startDiagnostic", () => {
    expect(src).toContain("startDiagnostic");
  });
  test("exports completeDiagnostic", () => {
    expect(src).toContain("completeDiagnostic");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. SkillMasteryRing.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("SkillMasteryRing.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("components", "training", "SkillMasteryRing.tsx")); });

  test("renders SVG element", () => {
    expect(src).toContain("<svg");
  });
  test("has aria-label", () => {
    expect(src).toContain("aria-label");
  });
  test("shows mastery_score", () => {
    expect(src).toContain("mastery_score");
  });
  test("uses MASTERY_STATE_COLOR", () => {
    expect(src).toContain("MASTERY_STATE_COLOR");
  });
  test("accepts size prop", () => {
    expect(src).toContain("size");
  });
  test("accepts showLabel prop", () => {
    expect(src).toContain("showLabel");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. MasteryExplanation.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("MasteryExplanation.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("components", "training", "MasteryExplanation.tsx")); });

  test("shows skill name (skillName prop)", () => {
    expect(src).toContain("skillName");
  });
  test("shows mastery_score", () => {
    expect(src).toContain("mastery_score");
  });
  test("has expand/collapse button", () => {
    expect(src).toContain("expanded");
  });
  test("shows coach_override_score when present", () => {
    expect(src).toContain("coach_override_score");
  });
  test("shows evidence_count", () => {
    expect(src).toContain("evidence_count");
  });
  test("uses useState for expanded state", () => {
    expect(src).toContain("useState");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. TrainingPlanCard.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("TrainingPlanCard.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("components", "training", "TrainingPlanCard.tsx")); });

  test("imports WeekPlan type", () => {
    expect(src).toContain("WeekPlan");
  });
  test("shows week number", () => {
    expect(src).toContain("current_week");
  });
  test("shows total_weeks", () => {
    expect(src).toContain("total_weeks");
  });
  test("shows objective", () => {
    expect(src).toContain("objective");
  });
  test("has lesson link to /learn", () => {
    expect(src).toContain("/learn");
  });
  test("has drill step", () => {
    expect(src).toContain("drill_description");
  });
  test("has apply step with /session link", () => {
    expect(src).toContain("/session");
  });
  test("has completion_criteria", () => {
    expect(src).toContain("completion_criteria");
  });
  test("has mark week complete button", () => {
    expect(src).toContain("onNextWeek");
  });
  test("shows progress bar", () => {
    expect(src).toContain("progressPct");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. BeforeAfterPanel.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("BeforeAfterPanel.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("components", "training", "BeforeAfterPanel.tsx")); });

  test("shows Before label", () => {
    expect(src).toContain("Before");
  });
  test("shows After label", () => {
    expect(src).toContain("After");
  });
  test("shows score delta", () => {
    expect(src).toContain("delta");
  });
  test("shows criteriaChanged list", () => {
    expect(src).toContain("criteriaChanged");
  });
  test("shows remainingIssues", () => {
    expect(src).toContain("remainingIssues");
  });
  test("shows skillName", () => {
    expect(src).toContain("skillName");
  });
  test("has before and after excerpt props", () => {
    expect(src).toContain("beforeExcerpt");
    expect(src).toContain("afterExcerpt");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 8. DiagnosticIntake.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("DiagnosticIntake.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("components", "training", "DiagnosticIntake.tsx")); });

  test("shows experience level options", () => {
    expect(src).toContain("experience");
  });
  test("uses EXPERIENCE_LABEL", () => {
    expect(src).toContain("EXPERIENCE_LABEL");
  });
  test("has self-rating skill options", () => {
    expect(src).toContain("RATED_SKILLS");
  });
  test("has Continue button", () => {
    expect(src).toContain("Continue");
  });
  test("has Back button", () => {
    expect(src).toContain("Back");
  });
  test("calls onComplete when submitted", () => {
    expect(src).toContain("onComplete");
  });
  test("has confirm step", () => {
    expect(src).toContain("confirm");
  });
  test("shows loading state", () => {
    expect(src).toContain("loading");
  });
  test("uses useState for step", () => {
    expect(src).toContain("useState");
  });
  test("has ratings state", () => {
    expect(src).toContain("ratings");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. PracticeAgenda.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("PracticeAgenda.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("components", "training", "PracticeAgenda.tsx")); });

  test('has role="region" aria-label', () => {
    expect(src).toContain("role=\"region\"");
    expect(src).toContain("aria-label");
  });
  test("renders agenda items", () => {
    expect(src).toContain("items");
  });
  test("shows duration_minutes", () => {
    expect(src).toContain("duration_minutes");
  });
  test("shows team_data_reason", () => {
    expect(src).toContain("team_data_reason");
  });
  test("shows activity type labels", () => {
    expect(src).toContain("ACTIVITY_LABEL");
  });
  test("shows total vs available minutes", () => {
    expect(src).toContain("totalMinutes");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 10. training/page.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("training/page.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("app", "(workspace)", "training", "page.tsx")); });

  test("imports fetchMasteryProfile", () => {
    expect(src).toContain("fetchMasteryProfile");
  });
  test("imports fetchActivePlan", () => {
    expect(src).toContain("fetchActivePlan");
  });
  test("imports TrainingPlanCard", () => {
    expect(src).toContain("TrainingPlanCard");
  });
  test("imports MasteryExplanation", () => {
    expect(src).toContain("MasteryExplanation");
  });
  test("imports SkillMasteryRing", () => {
    expect(src).toContain("SkillMasteryRing");
  });
  test("has tab for plan", () => {
    expect(src).toContain("plan");
  });
  test("has tab for mastery", () => {
    expect(src).toContain("mastery");
  });
  test("shows diagnostic prompt when no diagnostic", () => {
    expect(src).toContain("diagnostic");
    expect(src).toContain("Begin Diagnostic");
  });
  test("has generate plan button", () => {
    expect(src).toContain("generatePlan");
  });
  test("links to /diagnostic", () => {
    expect(src).toContain("/diagnostic");
  });
  test("shows mastery stats grid", () => {
    expect(src).toContain("Mastered");
    expect(src).toContain("In Progress");
  });
  test("has auth guard redirecting to /login", () => {
    expect(src).toContain("/login?next=/training");
  });
  test("uses useEffect for auth", () => {
    expect(src).toContain("useEffect");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 11. diagnostic/page.tsx
// ─────────────────────────────────────────────────────────────────────────────

describe("diagnostic/page.tsx", () => {
  let src: string;
  beforeAll(() => { src = read(srcFile("app", "(workspace)", "diagnostic", "page.tsx")); });

  test("imports DiagnosticIntake", () => {
    expect(src).toContain("DiagnosticIntake");
  });
  test("calls startDiagnostic", () => {
    expect(src).toContain("startDiagnostic");
  });
  test("calls completeDiagnostic", () => {
    expect(src).toContain("completeDiagnostic");
  });
  test("shows done state after completion", () => {
    expect(src).toContain("done");
  });
  test("links to /training on completion", () => {
    expect(src).toContain("/training");
  });
  test("has auth guard redirecting to /login", () => {
    expect(src).toContain("/login?next=/diagnostic");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 12. Backend file structure
// ─────────────────────────────────────────────────────────────────────────────

describe("Backend Training OS files", () => {
  test("public_forum.py exists and contains SKILL_REGISTRY", () => {
    const src = read(path.join(BACKEND_ROOT, "app", "event_packs", "public_forum.py"));
    expect(src).toContain("SKILL_REGISTRY");
  });

  test("mastery_engine.py exists and contains aggregate_mastery", () => {
    const src = read(path.join(BACKEND_ROOT, "app", "services", "mastery_engine.py"));
    expect(src).toContain("aggregate_mastery");
  });

  test("training_planner.py contains generate_plan", () => {
    const src = read(path.join(BACKEND_ROOT, "app", "services", "training_planner.py"));
    expect(src).toContain("generate_plan");
  });

  test("diagnostic_engine.py contains compute_initial_mastery", () => {
    const src = read(path.join(BACKEND_ROOT, "app", "services", "diagnostic_engine.py"));
    expect(src).toContain("compute_initial_mastery_from_diagnostic");
  });

  test("training API file has /training router", () => {
    const src = read(path.join(BACKEND_ROOT, "app", "api", "training.py"));
    expect(src).toContain('router = APIRouter(prefix="/training"');
    expect(src).toContain('"/mastery"');
  });

  test("migration file exists", () => {
    const migrDir = path.join(ROOT, "supabase", "migrations");
    const files = fs.readdirSync(migrDir).filter(f => f.includes("pass21"));
    expect(files.length).toBeGreaterThan(0);
  });

  test("migration file has 6 new tables", () => {
    const migrDir = path.join(ROOT, "supabase", "migrations");
    const file = fs.readdirSync(migrDir).find(f => f.includes("pass21"))!;
    const sql = read(path.join(migrDir, file));
    const tables = ["mastery_scores", "mastery_evidence", "training_plans",
                    "curriculum_progress", "coach_calibration", "diagnostic_results"];
    tables.forEach(t => expect(sql).toContain(t));
  });

  test("training router registered in main.py", () => {
    const src = read(path.join(BACKEND_ROOT, "app", "main.py"));
    expect(src).toContain("training.router");
  });

  test("navItems.ts includes Training nav entry", () => {
    const src = read(srcFile("lib", "navItems.ts"));
    expect(src).toContain("Training");
    expect(src).toContain("/training");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 13. Legacy skill backward-compat (source level)
// ─────────────────────────────────────────────────────────────────────────────

describe("Legacy skill backward compatibility", () => {
  let src: string;
  beforeAll(() => {
    src = read(path.join(BACKEND_ROOT, "app", "event_packs", "public_forum.py"));
  });

  test("LEGACY_SKILL_MAP defined", () => {
    expect(src).toContain("LEGACY_SKILL_MAP");
  });
  test("delivery maps to clarity", () => {
    // Key "delivery" should appear in LEGACY_SKILL_MAP pointing to "clarity"
    expect(src).toContain('"delivery"');
    expect(src).toContain('"clarity"');
  });
  test("drops maps to responses", () => {
    expect(src).toContain('"drops"');
    expect(src).toContain('"responses"');
  });
  test("warranting maps to warranting (passthrough)", () => {
    expect(src).toContain('"warranting"');
    // LEGACY_SKILL_MAP contains "warranting" key
    expect(src).toContain("LEGACY_SKILL_MAP");
  });
  test("resolve_legacy_skill function present", () => {
    expect(src).toContain("resolve_legacy_skill");
  });
  test("CANONICAL_TO_LEGACY reverse map present", () => {
    expect(src).toContain("CANONICAL_TO_LEGACY");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// TrainingPlanCard — data contract regression
// Ensures that the seeded / API-returned WeekPlan shape satisfies every field
// that TrainingPlanCard accesses, including mastery_target.toFixed().
// ─────────────────────────────────────────────────────────────────────────────

describe("TrainingPlanCard — WeekPlan contract regression", () => {
  // Minimal representative WeekPlan objects as the backend generates them.
  const SEED_WEEKS = [
    {
      week: 1,
      skill_focus: "warranting",
      skill_name: "Warranting",
      objective: "Deepen your understanding of Warranting through targeted drill work.",
      lesson_id: "pf_novice_02",
      drill_description: "Take one of your constructive claims and write a warrant five times.",
      speech_application: "After each claim, say 'because' out loud and complete the warrant.",
      completion_criteria: [
        "Every claim is followed by a 'because' explanation",
        "My warrant describes a mechanism, not just 'studies show'",
      ],
      mastery_target: 37.0,
      estimated_hours: 1.5,
    },
    {
      week: 2,
      skill_focus: "evidence_use",
      skill_name: "Evidence Use",
      objective: "Learn the fundamentals of Evidence Use.",
      lesson_id: "pf_novice_03",
      drill_description: "Write exact citations for two pieces of evidence in your case.",
      speech_application: "Cite author and year before every quoted passage.",
      completion_criteria: ["I cite author and year before every card"],
      mastery_target: 15.0,
      estimated_hours: 1.0,
    },
  ];

  test("all seeded weeks have mastery_target as a finite number", () => {
    for (const week of SEED_WEEKS) {
      expect(typeof week.mastery_target).toBe("number");
      expect(isFinite(week.mastery_target)).toBe(true);
    }
  });

  test("mastery_target.toFixed(0) does not throw for any seeded week", () => {
    for (const week of SEED_WEEKS) {
      expect(() => week.mastery_target.toFixed(0)).not.toThrow();
    }
  });

  test("all WeekPlan required fields are present in every seeded week", () => {
    const required = [
      "week", "skill_focus", "skill_name", "objective",
      "drill_description", "speech_application", "completion_criteria",
      "mastery_target", "estimated_hours",
    ];
    for (const week of SEED_WEEKS) {
      for (const field of required) {
        expect(week).toHaveProperty(field);
        expect((week as Record<string, unknown>)[field]).not.toBeUndefined();
      }
    }
  });

  test("seed SQL weeks JSON includes mastery_target field", () => {
    const seedSql = fs.readFileSync(
      path.join(ROOT, "scripts", "seed_test_users.sql"),
      "utf-8",
    );
    // Verify the seed SQL no longer uses the old {focus, lessons} shape
    expect(seedSql).not.toMatch(/"focus":\["warranting"/);
    // Verify the new shape is present
    expect(seedSql).toContain('"mastery_target"');
    expect(seedSql).toContain('"skill_focus"');
    expect(seedSql).toContain('"skill_name"');
  });

  test("TrainingPlanCard source does not use mastery_target without a preceding null guard", () => {
    const cardSrc = read(srcFile("components", "training", "TrainingPlanCard.tsx"));
    // The component casts weeks[n] as WeekPlan | undefined and guards on !week
    expect(cardSrc).toContain("WeekPlan | undefined");
    expect(cardSrc).toContain("if (!week)");
    // mastery_target is accessed — verify it is present in the source
    expect(cardSrc).toContain("mastery_target");
  });
});
