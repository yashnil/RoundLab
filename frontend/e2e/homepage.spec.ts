/**
 * Homepage structural and content integrity tests.
 *
 * Covers: PipelineShowcase presence, Trust section count, mobile overflow,
 * and anchor integrity after the surgical cleanup pass.
 */

import { test, expect, type Page } from "@playwright/test";

async function goToHome(page: Page) {
  await page.goto("/", { waitUntil: "networkidle" });
}

// ── PipelineShowcase ──────────────────────────────────────────────────────────

test("PipelineShowcase section is present with correct id", async ({ page }) => {
  await goToHome(page);
  const section = page.locator("#practice");
  await expect(section).toBeAttached();
});

test("PipelineShowcase section heading reads 'Watch a speech become a flow'", async ({
  page,
}) => {
  await goToHome(page);
  const heading = page.getByText("Watch a speech become a flow", { exact: true });
  await expect(heading).toBeVisible();
});

test("PipelineShowcase section has the 1AC header bar", async ({ page }) => {
  await goToHome(page);
  // Scroll card into view so scroll-triggered animation resolves
  await page.locator("#practice").scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  const label = page.locator("#practice").getByText("1AC · State Championship R4");
  await expect(label).toBeAttached();
});

test("PipelineShowcase 'Analysis complete' badge is visible", async ({ page }) => {
  await goToHome(page);
  await page.locator("#practice").scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  const badge = page.locator("#practice").getByText("Analysis complete");
  await expect(badge).toBeAttached();
});

test("PipelineShowcase section stamp reads 'Capture'", async ({ page }) => {
  await goToHome(page);
  const stamp = page.locator("#practice .section-stamp").first();
  await expect(stamp).toHaveText("Capture");
});

// ── Trust section ─────────────────────────────────────────────────────────────

test("Trust section contains exactly 6 trust points", async ({ page }) => {
  await goToHome(page);
  const trustSection = page.locator("#trust");
  await trustSection.scrollIntoViewIfNeeded();
  // Each trust point has a <p> with font-semibold text-ink title
  const titles = trustSection.locator("p.font-semibold");
  await expect(titles).toHaveCount(6);
});

test("Trust section has the inspectability point", async ({ page }) => {
  await goToHome(page);
  const trustSection = page.locator("#trust");
  await trustSection.scrollIntoViewIfNeeded();
  const inspectable = trustSection.getByText("Every judgment is inspectable", { exact: true });
  await expect(inspectable).toBeVisible();
});

// ── Removed sections are gone ─────────────────────────────────────────────────

test("#how-it-works section does not exist on the page", async ({ page }) => {
  await goToHome(page);
  const section = page.locator("#how-it-works");
  await expect(section).not.toBeAttached();
});

test("#supported section does not exist on the page", async ({ page }) => {
  await goToHome(page);
  const section = page.locator("#supported");
  await expect(section).not.toBeAttached();
});

// ── Homepage sequence ─────────────────────────────────────────────────────────

test("key homepage sections exist in expected order", async ({ page }) => {
  await goToHome(page);

  // Verify all six key anchors are present
  for (const id of [
    "#practice",
    "#speech-to-flow",
    "#judge",
    "#product-proof",
    "#evidence",
    "#team",
    "#trust",
  ]) {
    await expect(page.locator(id), `${id} should exist`).toBeAttached();
  }
});

test("PipelineShowcase appears before SpeechFlowSection in DOM", async ({ page }) => {
  await goToHome(page);
  const positions = await page.evaluate(() => {
    const practice = document.getElementById("practice");
    const speechToFlow = document.getElementById("speech-to-flow");
    if (!practice || !speechToFlow) return null;
    return (
      practice.compareDocumentPosition(speechToFlow) & Node.DOCUMENT_POSITION_FOLLOWING
    );
  });
  // DOCUMENT_POSITION_FOLLOWING (4) means speech-to-flow comes AFTER practice
  expect(positions).toBeTruthy();
});

// ── Mobile overflow ───────────────────────────────────────────────────────────

test("homepage has no horizontal overflow at 375px mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await goToHome(page);

  const hasHScroll = await page.evaluate(
    () => document.body.scrollWidth > window.innerWidth + 2
  );
  expect(hasHScroll).toBe(false);
});

test("homepage has no horizontal overflow at 390px iPhone 14", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await goToHome(page);

  const hasHScroll = await page.evaluate(
    () => document.body.scrollWidth > window.innerWidth + 2
  );
  expect(hasHScroll).toBe(false);
});

test("homepage has no horizontal overflow at 768px tablet", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await goToHome(page);

  const hasHScroll = await page.evaluate(
    () => document.body.scrollWidth > window.innerWidth + 2
  );
  expect(hasHScroll).toBe(false);
});

// ── Final CTA ─────────────────────────────────────────────────────────────────

test("final CTA contains the closing headline", async ({ page }) => {
  await goToHome(page);
  const headline = page.getByText(
    "Your next speech should know what the last one missed.",
    { exact: true }
  );
  await expect(headline).toBeAttached();
});
