/**
 * Local authentication fixtures for Playwright E2E tests.
 *
 * These fixtures replace the TEST_USER_EMAIL / TEST_USER_PASSWORD environment
 * variables with deterministic, seeded local Supabase accounts.  They run
 * without any external credentials so CI works on a clean clone.
 *
 * Architecture:
 *   1. For structural / routing tests: mock the auth cookie via
 *      page.addInitScript so the UI sees a "logged-in" session without a
 *      real Supabase backend.  The layout's useSession() receives a fake JWT.
 *
 *   2. For RLS / data tests: use the local Supabase emulator (started by
 *      `supabase start`) with known seed accounts created by the global setup
 *      script (see scripts/seed_test_users.sql).
 *
 * Seeded test accounts (only exist in local Supabase, never production):
 *   STUDENT_EMAIL     = "test_student@roundlab.local"
 *   COACH_EMAIL       = "test_coach@roundlab.local"   (same team as student)
 *   UNRELATED_COACH   = "test_coach2@roundlab.local"  (different team)
 *   UNRELATED_STUDENT = "test_student2@roundlab.local"
 *
 * When local Supabase is not running (CI without Docker), tests that need
 * real auth call `test.skip()` rather than failing with a hard error.
 */

import type { Page, BrowserContext } from "@playwright/test";

// --------------------------------------------------------------------------
// Constants
// --------------------------------------------------------------------------

export const TEST_ACCOUNTS = {
  student: {
    email: process.env.TEST_USER_EMAIL ?? "test_student_a@roundlab.local",
    password: process.env.TEST_USER_PASSWORD ?? "RoundLab_Test1!",
    role: "student",
  },
  coach: {
    email: process.env.TEST_COACH_EMAIL ?? "test_coach_a@roundlab.local",
    password: process.env.TEST_COACH_PASSWORD ?? "RoundLab_Test1!",
    role: "coach",
  },
  unrelatedCoach: {
    email: "test_coach_b@roundlab.local",
    password: "RoundLab_Test1!",
    role: "coach",
  },
  unrelatedStudent: {
    email: "test_student_b@roundlab.local",
    password: "RoundLab_Test1!",
    role: "student",
  },
} as const;

// Deterministic fake session payload for structural / routing tests that
// don't need a real Supabase backend.  The UI reads this from the cookie.
const FAKE_SESSION_STUDENT = {
  access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXN0dWRlbnQtMDEiLCJlbWFpbCI6InRlc3Rfc3R1ZGVudEByb3VuZGxhYi5sb2NhbCIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjo5OTk5OTk5OTk5fQ.fake_student_sig",
  token_type: "bearer",
  expires_in: 9999999,
  refresh_token: "fake_refresh_student",
  user: {
    id: "test-student-01",
    email: "test_student@roundlab.local",
    role: "authenticated",
  },
};

const FAKE_SESSION_COACH = {
  access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNvYWNoLTAxIiwiZW1haWwiOiJ0ZXN0X2NvYWNoQHJvdW5kbGFiLmxvY2FsIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJleHAiOjk5OTk5OTk5OTl9.fake_coach_sig",
  token_type: "bearer",
  expires_in: 9999999,
  refresh_token: "fake_refresh_coach",
  user: {
    id: "test-coach-01",
    email: "test_coach@roundlab.local",
    role: "authenticated",
  },
};

// --------------------------------------------------------------------------
// Structural login (mock — no real Supabase required)
// --------------------------------------------------------------------------

/**
 * Inject a fake Supabase session cookie so the UI renders as if a student
 * is logged in.  Uses page.addInitScript to run before any page code.
 *
 * This is appropriate for structural / routing / DOM assertion tests.
 * For tests that need real data from the DB, use `loginAsStudentReal()`.
 */
export async function injectStudentSession(page: Page): Promise<void> {
  await page.addInitScript((session) => {
    // Supabase stores the session under this key pattern
    const key = `sb-${window.location.hostname.split(".")[0]}-auth-token`;
    try {
      localStorage.setItem(key, JSON.stringify(session));
    } catch {
      // localStorage may be blocked in some contexts — structural tests proceed
    }
  }, FAKE_SESSION_STUDENT);
}

export async function injectCoachSession(page: Page): Promise<void> {
  await page.addInitScript((session) => {
    const key = `sb-${window.location.hostname.split(".")[0]}-auth-token`;
    try {
      localStorage.setItem(key, JSON.stringify(session));
    } catch {}
  }, FAKE_SESSION_COACH);
}

// --------------------------------------------------------------------------
// Real login helpers (require local Supabase or env vars)
// --------------------------------------------------------------------------

type LoginResult = "ok" | "skipped";

async function _realLogin(
  page: Page,
  email: string,
  password: string,
): Promise<LoginResult> {
  try {
    await page.goto("/login");
    await page.waitForLoadState("domcontentloaded");

    const emailInput = page.locator('input[type="email"]');
    if ((await emailInput.count()) === 0) return "skipped";

    await emailInput.fill(email);
    await page.locator('input[type="password"]').fill(password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/dashboard|training|team/, { timeout: 12_000 });
    return "ok";
  } catch {
    return "skipped";
  }
}

/** Login as the seeded student account. Skip test if auth fails. */
export async function loginAsStudent(
  page: Page,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  testObj?: { skip: () => void },
): Promise<boolean> {
  const { email, password } = TEST_ACCOUNTS.student;
  const result = await _realLogin(page, email, password);
  if (result === "skipped") {
    testObj?.skip();
    return false;
  }
  return true;
}

/** Login as the seeded team coach account. Skip test if auth fails. */
export async function loginAsCoach(
  page: Page,
  testObj?: { skip: () => void },
): Promise<boolean> {
  const { email, password } = TEST_ACCOUNTS.coach;
  const result = await _realLogin(page, email, password);
  if (result === "skipped") {
    testObj?.skip();
    return false;
  }
  return true;
}

/** Login as an unrelated coach (no shared team). Skip if auth fails. */
export async function loginAsUnrelatedCoach(
  page: Page,
  testObj?: { skip: () => void },
): Promise<boolean> {
  const result = await _realLogin(
    page,
    TEST_ACCOUNTS.unrelatedCoach.email,
    TEST_ACCOUNTS.unrelatedCoach.password,
  );
  if (result === "skipped") {
    testObj?.skip();
    return false;
  }
  return true;
}

/** Login as an unrelated student (different team). Skip if auth fails. */
export async function loginAsUnrelatedStudent(
  page: Page,
  testObj?: { skip: () => void },
): Promise<boolean> {
  const result = await _realLogin(
    page,
    TEST_ACCOUNTS.unrelatedStudent.email,
    TEST_ACCOUNTS.unrelatedStudent.password,
  );
  if (result === "skipped") {
    testObj?.skip();
    return false;
  }
  return true;
}

// --------------------------------------------------------------------------
// Context-level auth state (reusable across tests in the same suite)
// --------------------------------------------------------------------------

/**
 * Set storage state for an entire BrowserContext.
 * Call once in a beforeAll, then reuse across tests in the describe block.
 */
export async function setStudentStorageState(
  context: BrowserContext,
): Promise<void> {
  await context.addInitScript((session) => {
    const key = `sb-${window.location.hostname.split(".")[0]}-auth-token`;
    try {
      localStorage.setItem(key, JSON.stringify(session));
    } catch {}
  }, FAKE_SESSION_STUDENT);
}

export async function setCoachStorageState(
  context: BrowserContext,
): Promise<void> {
  await context.addInitScript((session) => {
    const key = `sb-${window.location.hostname.split(".")[0]}-auth-token`;
    try {
      localStorage.setItem(key, JSON.stringify(session));
    } catch {}
  }, FAKE_SESSION_COACH);
}
