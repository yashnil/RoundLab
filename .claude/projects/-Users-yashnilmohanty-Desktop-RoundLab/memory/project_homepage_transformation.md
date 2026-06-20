---
name: homepage-transformation
description: "Homepage Transformation — Phase 2 (2026-06-17/20): progressive-disclosure homepage, shell skip-link fix, 8-section redesign"
metadata:
  type: project
---

Branch: ui/homepage-transformation

## Shell skip-link fix (AppShell.tsx)

**Root cause:** `sr-only focus:not-sr-only focus:fixed` pattern — `not-sr-only` removes clip/size but `fixed` doesn't atomically reposition, causing layout flash on hydration and route changes.

**Fix:** `absolute -left-[9999px] top-3 z-[100] ... focus:left-4` — always off-canvas via position, never in layout flow. Added `tabIndex={-1}` + `focus-visible:outline-none` to `<main id="main-content">`.

**Rule:** The authenticated shell now uses the off-canvas skip-link pattern. Public homepage (page.tsx) has its own skip link using the same pattern.

## Homepage redesign (8 sections)

Removed sections: Capture (PipelineShowcase — redundant with hero), separate Flow/Judge/Improve sections, Trust section, SupportedToday section.

New structure:
1. Hero (HeroDebateConsole) → keep, fixed contrast
2. Proof strip (HOME_PROOF_POINTS)
3. `#how-it-works` — WorkflowRail
4. `#product-proof` — ProductProofTabs (tabbed: Flow / Ballot / Improvement)
5. Why RoundLab — DIFFERENTIATOR_POINTS grid
6. `#evidence` — EvidenceProvenanceStrip (aria-hidden wrapped)
7. `#for-coaches` — TeamWorkflowStrip (aria-hidden wrapped)
8. Convert CTA → MarketingFooter

## marketing.ts changes

- HOME_ANCHORS: `["#how-it-works", "#product-proof", "#evidence", "#for-coaches"]`
- MARKETING_NAV_LINKS: "How it works" / "Product" / "Evidence" / "Coaches"
- Added DIFFERENTIATOR_POINTS export (5 debate-native differentiators)

## Contrast fixes

- Hero badge: `text-lav` → `text-ink` (lav at 11px fails AA in light mode, ~3.5:1)
- MarketingFooter: `text-ink-faint` → `text-ink-subtle` on group labels and copyright
- HeroDebateConsole: ALL inner text upgraded — `text-[9px] text-lav/text-ink-faint` → `text-eyebrow text-ink-subtle`

## HeroDebateConsole key changes

- Added `role="img"` to outer wrapper (required for `aria-label` on div)
- Inner panel: `bg-surface-1/95 backdrop-blur-sm` → `bg-surface-1` (solid; semi-transparent + backdrop-filter causes Axe to fail color computation)
- All inner `motion.div/motion.span` → plain `div/span` (framer-motion `initial={{ opacity: 0 }}` causes partial-opacity during Axe scan, failing color-contrast despite element being inside aria-hidden)
- All `text-[9px]` → `text-eyebrow`, all `text-ink-faint` → `text-ink-subtle`

## Axe color-contrast gotchas (CRITICAL LESSONS)

1. `aria-hidden="true"` on a PARENT div does NOT protect descendant text from Axe's color-contrast rule. Axe uses CSS selector `[aria-hidden="true"]` which matches only DIRECT elements, not descendants.

2. `backdrop-blur-sm` + `bg-surface-1/95` (semi-transparent bg) causes Axe to fail to compute background color accurately → false positive contrast failures.

3. framer-motion `initial={{ opacity: 0 }} animate={{ opacity: 1 }}` on inner elements causes Axe to scan them mid-animation at partial opacity → false positive contrast failures. Solution: use plain CSS/static styles for inner elements inside aria-hidden containers; keep motion.* only on the outermost visible wrapper.

4. `aria-label` on a plain `<div>` without a role violates `aria-prohibited-attr`. Add `role="img"` (or another appropriate landmark role) when using `aria-label` on non-semantic containers.

## New components

- `src/components/marketing/ProductProofTabs.tsx` — tabbed showcase (Flow/Ballot/Improvement)

## New E2E tests

- `e2e/homepage.spec.ts` — 23 tests across 3 browsers: Axe scan, skip-link keyboard, hero CTAs, section anchors, tabs, mobile menu, overflow, nav links, footer, reduced motion

## Test results

TypeScript: clean · Jest: 1371/1371 · build: green · Playwright: 185/185 (1 skipped = expected mobile skip for desktop nav test)
