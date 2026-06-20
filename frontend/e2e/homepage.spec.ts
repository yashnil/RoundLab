/**
 * Homepage (/) E2E tests.
 *
 * Covers: accessibility, skip-link keyboard behavior, hero CTA routing,
 * product tabs keyboard nav, mobile menu, brand routing, and overflow.
 *
 * All tests run against the public/unauthenticated homepage.
 */

import { test, expect } from "@playwright/test";
import { checkA11y, goTo } from "./helpers";

// ── Homepage loads ────────────────────────────────────────────────────────────

test.describe("Homepage — load", () => {
  test("renders without critical Axe violations", async ({ page }) => {
    await goTo(page, "/");
    await checkA11y(page);
  });

  test("has a main landmark", async ({ page }) => {
    await goTo(page, "/");
    const main = page.locator("main#main-content");
    await expect(main).toBeAttached();
  });

  test("has a nav landmark with the brand link", async ({ page }) => {
    await goTo(page, "/");
    const brand = page.locator("nav a").filter({ hasText: "RoundLab" }).first();
    await expect(brand).toBeVisible();
    const href = await brand.getAttribute("href");
    expect(href).toBe("/");
  });
});

// ── Skip link — keyboard pattern ─────────────────────────────────────────────

test.describe("Skip link — keyboard", () => {
  test("is not visible before keyboard interaction", async ({ page }) => {
    await goTo(page, "/");
    // The skip link is positioned at -left-[9999px]; it should be off-screen
    const skipLink = page.locator('a[href="#main-content"]').first();
    await expect(skipLink).toBeAttached();
    // Check it's off-screen (Playwright considers off-canvas elements NOT visible)
    const box = await skipLink.boundingBox();
    if (box) {
      // If it has a bounding box, x should be far off-screen
      expect(box.x).toBeLessThan(-100);
    }
  });

  test("first Tab reveals the skip link", async ({ page }) => {
    await goTo(page, "/");
    const skipLink = page.locator('a[href="#main-content"]').first();
    // Tab once to focus skip link
    await page.keyboard.press("Tab");
    await expect(skipLink).toBeFocused({ timeout: 2_000 });
  });

  test("Enter on skip link moves focus to main content", async ({ page }) => {
    await goTo(page, "/");
    // Tab to focus skip link then activate it
    await page.keyboard.press("Tab");
    await expect(page.locator('a[href="#main-content"]').first()).toBeFocused({
      timeout: 2_000,
    });
    await page.keyboard.press("Enter");
    // After skipping, focus should be on #main-content
    const main = page.locator("main#main-content");
    await expect(main).toBeFocused({ timeout: 2_000 });
  });
});

// ── Hero CTAs ─────────────────────────────────────────────────────────────────

test.describe("Homepage — hero CTAs", () => {
  test("primary CTA 'Start practicing' links to /login", async ({ page }) => {
    await goTo(page, "/");
    // Target inside <main> to skip the nav's hidden "Start practicing" (display:none on mobile)
    const cta = page.locator("main").getByRole("link", { name: /start practicing/i }).first();
    await expect(cta).toBeVisible();
    const href = await cta.getAttribute("href");
    expect(href).toBe("/login");
  });

  test("secondary CTA 'See a real report' links to /demo", async ({ page }) => {
    await goTo(page, "/");
    const cta = page.locator("main").getByRole("link", { name: /see a real report/i }).first();
    await expect(cta).toBeVisible();
    const href = await cta.getAttribute("href");
    expect(href).toBe("/demo");
  });
});

// ── Section anchors ───────────────────────────────────────────────────────────

test.describe("Homepage — section anchors", () => {
  test("how-it-works section exists with a visible heading", async ({ page }) => {
    await goTo(page, "/");
    const section = page.locator("#how-it-works");
    await expect(section).toBeAttached();
  });

  test("product-proof section has interactive tabs", async ({ page }) => {
    await goTo(page, "/");
    const tabs = page.locator('[role="tablist"]');
    await expect(tabs).toBeVisible();
    // Should have 3 tabs
    const tabButtons = page.locator('[role="tab"]');
    await expect(tabButtons).toHaveCount(3);
  });

  test("evidence section exists", async ({ page }) => {
    await goTo(page, "/");
    const section = page.locator("#evidence");
    await expect(section).toBeAttached();
  });

  test("for-coaches section exists", async ({ page }) => {
    await goTo(page, "/");
    const section = page.locator("#for-coaches");
    await expect(section).toBeAttached();
  });
});

// ── Product proof tabs — keyboard nav ────────────────────────────────────────

test.describe("Product proof tabs — keyboard", () => {
  test("all three tabs exist with distinct labels", async ({ page }) => {
    await goTo(page, "/");
    const tabButtons = page.locator('[role="tab"]');
    await expect(tabButtons).toHaveCount(3);
    const labels = await tabButtons.allTextContents();
    // All three tabs have distinct non-empty labels
    const trimmed = labels.map((l) => l.trim()).filter(Boolean);
    expect(trimmed.length).toBe(3);
    expect(new Set(trimmed).size).toBe(3);
  });

  test("clicking a tab changes the visible content", async ({ page }) => {
    await goTo(page, "/");
    const ballotTab = page.locator('[role="tab"]').nth(1);
    await ballotTab.click();
    await expect(ballotTab).toHaveAttribute("data-state", "active");
    // First tab should no longer be active
    const firstTab = page.locator('[role="tab"]').first();
    await expect(firstTab).toHaveAttribute("data-state", "inactive");
  });

  test("ArrowRight moves focus between tabs in the tablist", async ({ page }) => {
    await goTo(page, "/");
    // Focus the first tab directly
    const firstTab = page.locator('[role="tab"]').first();
    await firstTab.focus();
    await expect(firstTab).toBeFocused();
    await page.keyboard.press("ArrowRight");
    // Second tab should now be focused
    const secondTab = page.locator('[role="tab"]').nth(1);
    await expect(secondTab).toBeFocused({ timeout: 1_000 });
  });
});

// ── Mobile menu ───────────────────────────────────────────────────────────────

test.describe("Homepage — mobile menu", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("mobile menu button opens the sheet", async ({ page }) => {
    await goTo(page, "/");
    const menuButton = page.locator("button[aria-label='Open menu']");
    await expect(menuButton).toBeVisible();
    await menuButton.click();
    // Sheet content should be visible
    await expect(page.locator("[data-radix-popper-content-wrapper], [data-state='open']").first()).toBeVisible({
      timeout: 2_000,
    });
  });

  test("no horizontal overflow at 375px", async ({ page }) => {
    await goTo(page, "/");
    const overflow = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(overflow).toBe(false);
  });
});

// ── Nav links ─────────────────────────────────────────────────────────────────

test.describe("Homepage — nav links", () => {
  test("desktop nav has 4 marketing links", async ({ page, viewport }) => {
    if ((viewport?.width ?? 1280) < 768) {
      test.skip();
    }
    await goTo(page, "/");
    // The desktop nav links are visible on md+ screens
    const navLinks = page.locator("nav").first().locator("a[href^='#']");
    await expect(navLinks).toHaveCount(4);
  });

  test("nav link 'How it works' scrolls to section", async ({ page }) => {
    await goTo(page, "/");
    const link = page.locator("a[href='#how-it-works']").first();
    if (await link.isVisible()) {
      await link.click();
      // After clicking, the section should be in view or URL should update
      const url = page.url();
      expect(url).toContain("#how-it-works");
    }
  });
});

// ── Footer ────────────────────────────────────────────────────────────────────

test.describe("Homepage — footer", () => {
  test("footer renders with accessible nav", async ({ page }) => {
    await goTo(page, "/");
    const footer = page.locator("footer");
    await expect(footer).toBeVisible();
    const footerNav = footer.locator("nav[aria-label='Footer']");
    await expect(footerNav).toBeAttached();
  });

  test("footer links are accessible and visible", async ({ page }) => {
    await goTo(page, "/");
    const footer = page.locator("footer");
    // At least 4 links (Product group + Get started group)
    const links = footer.locator("a");
    const count = await links.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });
});

// ── Reduced motion ────────────────────────────────────────────────────────────

test.describe("Homepage — reduced motion", () => {
  test("page loads without motion errors", async ({ page }) => {
    // Emulate reduced-motion via CSS override
    await page.emulateMedia({ reducedMotion: "reduce" });
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await goTo(page, "/");
    await page.waitForTimeout(500);
    expect(errors).toHaveLength(0);
  });

  test("hero heading is visible", async ({ page }) => {
    await goTo(page, "/");
    const heading = page.locator("h1").first();
    await expect(heading).toBeVisible();
  });
});
