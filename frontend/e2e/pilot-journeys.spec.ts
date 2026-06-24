/**
 * Pilot journey smoke tests.
 *
 * These tests verify the public-facing shell of each journey without
 * requiring an authenticated session or live network calls.
 *
 * Journey coverage:
 *   1. New user → sees onboarding / empty dashboard
 *   2. Demo page → loads evidence components without crashing
 *   3. Evidence page → redirects unauthenticated users correctly
 *   4. Round Simulation → redirects or shows empty state
 *   5. Pilot page → loads checklist
 *
 * For full E2E with auth, use the authenticated test suite (not yet wired
 * due to absence of a shared test user in CI). These tests are safe for CI.
 */

import { test, expect } from "@playwright/test";
import { goTo } from "./helpers";

// ── Journey 1: Homepage → onboarding entry point ───────────────────────────

test.describe("Homepage onboarding entry", () => {
  test("homepage loads without error", async ({ page }) => {
    await goTo(page, "/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("homepage has a primary call-to-action", async ({ page }) => {
    await goTo(page, "/");
    // Should have at least one link or button
    const interactive = await page.locator("a[href], button").count();
    expect(interactive).toBeGreaterThan(0);
  });
});

// ── Journey 2: Demo page (no auth required) ────────────────────────────────

test.describe("Demo page journey", () => {
  test("demo page loads without crash", async ({ page }) => {
    await goTo(page, "/demo");
    await expect(page.locator("body")).toBeVisible();
  });

  test("demo page has meaningful content", async ({ page }) => {
    await goTo(page, "/demo");
    const headings = await page.locator("h1, h2, h3").count();
    expect(headings).toBeGreaterThan(0);
  });

  test("demo page has no JavaScript errors on load", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await goTo(page, "/demo");
    // Filter known benign hydration warnings
    const critical = errors.filter(
      (e) => !e.includes("hydration") && !e.includes("Warning:"),
    );
    expect(critical).toHaveLength(0);
  });
});

// ── Journey 3: Evidence page (auth-gated) ─────────────────────────────────

test.describe("Evidence page auth gate", () => {
  test("unauthenticated user redirected or sees login prompt", async ({ page }) => {
    await goTo(page, "/evidence");
    const url = page.url();
    const body = await page.locator("body").textContent();
    // Either redirected to login or shows a sign-in prompt
    const isLoginPage = url.includes("/login");
    const hasLoginText = (body ?? "").toLowerCase().includes("sign in") ||
                         (body ?? "").toLowerCase().includes("log in");
    expect(isLoginPage || hasLoginText).toBe(true);
  });
});

// ── Journey 4: Round Simulation (auth-gated) ──────────────────────────────

test.describe("Round Simulation page auth gate", () => {
  test("unauthenticated user redirected or sees login prompt", async ({ page }) => {
    await goTo(page, "/round-simulation");
    const url = page.url();
    const body = await page.locator("body").textContent();
    const isLoginPage = url.includes("/login");
    const hasLoginText = (body ?? "").toLowerCase().includes("sign in") ||
                         (body ?? "").toLowerCase().includes("log in");
    expect(isLoginPage || hasLoginText).toBe(true);
  });
});

// ── Journey 5: Pilot page ─────────────────────────────────────────────────

test.describe("Pilot checklist page", () => {
  test("pilot page loads without crash", async ({ page }) => {
    await goTo(page, "/pilot");
    await expect(page.locator("body")).toBeVisible();
  });

  test("pilot page has no critical JS errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await goTo(page, "/pilot");
    const critical = errors.filter(
      (e) => !e.includes("hydration") && !e.includes("Warning:"),
    );
    expect(critical).toHaveLength(0);
  });
});

// ── Journey 6: Library page (auth-gated) ──────────────────────────────────

test.describe("Evidence Library page auth gate", () => {
  test("unauthenticated user sees login prompt", async ({ page }) => {
    await goTo(page, "/library");
    const url = page.url();
    const body = await page.locator("body").textContent();
    const isLoginPage = url.includes("/login");
    const hasLoginText = (body ?? "").toLowerCase().includes("sign in") ||
                         (body ?? "").toLowerCase().includes("log in");
    expect(isLoginPage || hasLoginText).toBe(true);
  });
});

// ── Journey 7: Judge Adaptation (auth-gated) ──────────────────────────────

test.describe("Judge Adaptation page auth gate", () => {
  test("unauthenticated user redirected", async ({ page }) => {
    await goTo(page, "/judge-adaptation");
    const url = page.url();
    const body = await page.locator("body").textContent();
    const isLoginPage = url.includes("/login");
    const hasLoginText = (body ?? "").toLowerCase().includes("sign in") ||
                         (body ?? "").toLowerCase().includes("log in");
    expect(isLoginPage || hasLoginText).toBe(true);
  });
});

// ── API health check from browser ─────────────────────────────────────────

test.describe("Backend health endpoint", () => {
  test("health endpoint returns ok", async ({ page, baseURL }) => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const response = await page.request.get(`${apiBase}/health`);
    expect(response.status()).toBe(200);
    const json = await response.json();
    expect(json.status).toBe("ok");
  });
});
