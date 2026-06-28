/**
 * Shared helpers for Dissio e2e and accessibility tests.
 */

import { Page, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Run an axe accessibility scan on the current page state.
 * Fails if any critical or serious violations are found.
 * Documented suppressions are listed inline with reason.
 */
export async function checkA11y(
  page: Page,
  options?: {
    include?: string[];
    exclude?: string[];
    disableRules?: string[];
  },
): Promise<void> {
  const builder = new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]);

  if (options?.include) {
    builder.include(options.include);
  }
  if (options?.exclude) {
    builder.exclude(options.exclude);
  }
  if (options?.disableRules) {
    builder.disableRules(options.disableRules);
  }

  const results = await builder.analyze();
  const criticalAndSerious = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious",
  );

  if (criticalAndSerious.length > 0) {
    const details = criticalAndSerious
      .map(
        (v) =>
          `[${v.impact}] ${v.id}: ${v.description}\n  Affects: ${v.nodes.map((n) => n.target.join(", ")).join(" | ")}`,
      )
      .join("\n");
    throw new Error(`Axe found ${criticalAndSerious.length} critical/serious violation(s):\n${details}`);
  }
}

/**
 * Navigate to a page and wait for it to be stable (no loading spinner).
 */
export async function goTo(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}

/**
 * Tab through the page and collect all focused element descriptions.
 * Stops after `maxTabs` iterations to avoid infinite loops.
 */
export async function tabThrough(
  page: Page,
  maxTabs = 50,
): Promise<string[]> {
  const visited: string[] = [];
  for (let i = 0; i < maxTabs; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      return {
        tag: el.tagName.toLowerCase(),
        role: el.getAttribute("role") ?? "",
        label:
          el.getAttribute("aria-label") ??
          el.getAttribute("aria-labelledby") ??
          (el as HTMLElement).textContent?.trim().slice(0, 60) ??
          "",
        href: (el as HTMLAnchorElement).href ?? "",
      };
    });
    if (!info) break;
    visited.push(`${info.tag}[${info.role}] "${info.label}"`);
  }
  return visited;
}

/**
 * Assert that focus is on an element matching a given selector after an action.
 */
export async function expectFocusOn(page: Page, selector: string): Promise<void> {
  await expect(page.locator(selector)).toBeFocused({ timeout: 3_000 });
}
