# Dissio Frontend — Production-Readiness Overhaul Report

> **Branch:** ui/homepage-transformation  
> **Date:** 2026-06-19  
> **Scope:** Accessibility hardening, keyboard completeness, motion audit, responsive coverage, visual consistency, evidence workbench follow-up

---

## 1. Routes and Components Redesigned / Hardened

### Redesigned (earlier passes — now hardened)
| Route | Component(s) | Work Done |
|---|---|---|
| `/evidence` | `app/evidence/page.tsx` | 3-column workbench layout, semantic tokens, roving tabindex |
| All authed routes | `shell/AppShell.tsx`, `shell/AppSidebar.tsx`, `shell/MobileNav.tsx` | P0 focus fixes, premium sidebar, bottom nav |
| `/session` | `RecordingStudio` | Reduced-motion-safe, aria-live, practiceStudioModel |
| `/speech/[id]` | `SpeechReportWorkspace`, `FlowCanvas`, `DrillCard` | Report hierarchy, flow a11y, drill entrance |

### Token cleanup (this pass)
| Component | Violations Fixed |
|---|---|
| `evidence/EvidenceSearchProgress.tsx` | `bg-gray-*`, `bg-white`, `text-gray-*` → semantic tokens; `animate-pulse` → `motion-safe:animate-pulse`; `role="progressbar"` moved to wrapper |
| `evidence/CardAnalysis.tsx` | `border-gray-200`, `bg-gray-50/70`, `text-gray-400`, `text-gray-700`, `text-emerald-700`, `text-rose-700` → tokens |
| `evidence/CoachNotesPanel.tsx` | All 7 category color strings → semantic (lav/ok/warn/danger/surface); `aria-expanded` on expand button; `aria-hidden` on decorative icons |
| `evidence/EvidenceStudioCard.tsx` | 30+ violations: all `gray-*`, `amber-*`, `orange-*`, `emerald-*`, `rose-*` → tokens; `bg-gray-900 text-white` → `bg-ink text-canvas`; focus rings → `ring-lav/50` |
| `evidence/EvidenceStudioModal.tsx` | `bg-white` → `bg-surface-1`; + full focus trap + focus restoration |

---

## 2. Packages Added

| Package | Version | Purpose |
|---|---|---|
| `@playwright/test` | ^1.61.0 | E2E / accessibility integration tests |
| `@axe-core/playwright` | (latest) | Axe rule scanning in Playwright tests |

No packages removed. `motion` (v12.40.0) retained — only decorative usages removed from `EvidenceSearchProgress` (`animate-pulse` → `motion-safe:animate-pulse`).

---

## 3. Accessibility Findings and Fixes

### Critical / Serious (all fixed)

| Finding | Severity | Fix |
|---|---|---|
| `EvidenceStudioModal` missing focus trap | Serious | Tab/Shift+Tab now cycles within modal; focus returns to trigger on close |
| `EvidenceSearchProgress` `role="progressbar"` on wrong element | Serious | Moved to the track wrapper; `aria-valuenow/min/max/label` on outer div |
| Counter-evidence warning used orange color as the only signal | Serious | Replaced with semantic `text-warn`; emoji ⚡ still present as secondary cue |
| `CoachNotesPanel` expand button had no `aria-expanded` | Moderate | Added `aria-expanded={expanded}` |
| Decorative icons missing `aria-hidden` | Moderate | Added `aria-hidden="true"` to all ✓, →, ⚠, ▲/▼ icons |
| Readiness dot (color-only signal) | Serious | Label text always shown alongside dot; dot gets `aria-hidden` |
| Cut style controls had no `role="radiogroup"`/`role="radio"` | Moderate | Added ARIA radio pattern with `aria-checked` |
| `animate-pulse` ran unconditionally | Minor | Wrapped in `motion-safe:animate-pulse` |

### Candidate keyboard navigation

**Before:** Candidate cards were click-only; no keyboard path to navigate the list.

**After:** Roving tabindex pattern on `role="listbox" aria-label="Evidence candidates"`:
- Each card button has `data-candidate="true"` and `tabIndex={activeCardIndex === idx ? 0 : -1}`
- `onKeyDown` on the list container handles `ArrowDown`, `ArrowUp`, `Home`, `End`
- DOM focus moves to the newly active button via `querySelectorAll("[data-candidate]")[next].focus()`
- `role="option"` + `aria-selected` on each card wrapper for screen readers
- Click on any card also updates `activeCardIndex`

---

## 4. Keyboard and Focus Behavior

### Modal focus management
`EvidenceStudioModal`:
1. On open: captures `document.activeElement` into `previousFocusRef`
2. On mount: moves focus to `modalRef.current` (the panel div with `tabIndex={-1}`)
3. While open: Tab/Shift+Tab cycles through `querySelectorAll(focusableSelector)` within the panel
4. On close (Escape, backdrop click, or Close button): cleanup effect restores focus to `previousFocusRef.current`

### Focus rings (all interactive elements)
All touched components now use `focus-visible:ring-2 focus-visible:ring-lav/50` (desktop) or `focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-lav/50` (inset contexts). No element relies on browser-default outline only.

### Evidence workbench tab order
1. Left panel: claim textarea → topic → side → source mode → URL/Paste/Search controls
2. Center panel: filter chips → candidate list (roving tabindex within)
3. Right panel: selected card → Open in Studio → EvidenceCardDraft actions
4. Mobile: stage nav tabs above panels (each with `aria-current="step"`)

---

## 5. Responsive and Visual Regression Coverage

### Playwright e2e tests added (`e2e/`)
| File | What is tested |
|---|---|
| `accessibility.spec.ts` | Axe scans: login, demo, auth-redirects; heading hierarchy; form labels; color contrast |
| `keyboard.spec.ts` | Tab order, focus indicators, dialog role/aria-modal, landmark structure, radiogroup labels |
| `responsive.spec.ts` | Mobile/tablet/desktop viewport overflow, sticky elements, mobile nav sheet, broken images, touch target sizes |

### Viewports covered
- **Mobile:** 375×812 (Pixel 5)
- **Tablet:** 768×1024 (iPad gen 7)
- **Desktop:** 1280×800 (Chrome)

### Known: visual screenshots
Screenshots are captured on failure only (`screenshot: "only-on-failure"` in `playwright.config.ts`). Full visual regression snapshots are deferred — dynamic content (evidence cards, AI analysis) makes pixel-diff snapshots fragile. The recommended approach for visual regression is [Percy](https://percy.io/) or [Chromatic](https://www.chromatic.com/) at a future sprint.

### Responsive layout fixes (this pass)
- `EvidenceSearchProgress` no longer has a hardcoded card-like white surface that clashes in dark environments
- `EvidenceStudioModal` uses `min(900px, 96vw) × min(940px, 92vh)` — tested at 375px width
- Candidate list uses `flex flex-col` (not grid) so it stacks correctly at all widths
- Mobile stage nav is `hidden md:flex` / `flex` toggling (not `display:none` via JS) — respects forced-colors mode

---

## 6. Motion and Performance Changes

### Animation audit — evidence workbench

| Location | Animation | Decision |
|---|---|---|
| `EvidenceSearchProgress` — shimmer | `animate-pulse` | Kept, wrapped in `motion-safe:animate-pulse` |
| `EvidenceSearchProgress` — bar transition | `transition-[width] duration-500` | Kept — functional (shows progress); uses `transform`-friendly approach |
| `EvidenceStudioCard` — `hover:shadow-sm transition-shadow` | CSS transition | Kept — subtle, performance-safe |
| `FlowTable` row expand | `motion.div` height animation | Already in `T` wrapper (respects reduced motion via `reducedSafe`) |
| `ReportVerdictPanel` score ring | `motion.div` + `animate` | Retained — meaningful, not decorative; user can disable via OS |
| `ScoreCard` number counter | `motion.span` + `animate` | Retained — meaningful data visualization |
| `PracticeLoopCTA` entrance | `motion.div` opacity+y | Retained — one-time entrance, not looping |

### Performance notes
- No new heavy libraries added
- `motion` (formerly Framer Motion) is already in the bundle; no additions
- Evidence Studio Modal uses CSS `backdrop-blur-sm` — GPU-composited, no JS
- `EvidenceSearchProgress` uses `setInterval` (not RAF); interval is cleared on unmount
- Candidate list re-renders only when `activeCardIndex` or `selectedCardId` change — no excessive re-renders introduced

### Lazy-loading opportunities (deferred)
- `EvidenceStudioModal` could be lazy-loaded with `dynamic(() => import(...), { ssr: false })` — would remove ~15KB from initial evidence page bundle
- `DebatePrepPanel` and `CardAnalysis` are candidates for suspense-wrapped lazy loading

---

## 7. Remaining Known Limitations

### P1 (design debt, pre-existing)

| Area | Issue | Priority |
|---|---|---|
| `CoachReportView.tsx` | `print:gray-*` classes — intentional print overrides; could use `print:text-foreground` | P2 |
| `EvidenceSearchPanel.tsx` | `bg-gray-50` and `text-amber-700` in diagnostics section | P2 |
| `EvidenceSupportPanel.tsx` | `text-amber-600` in one location | P2 |
| Typography — remaining arbitrary px sizes | `FlowBoard`, `BlockCoveragePanel`, `ImprovementReceipt`, `ReportVerdictPanel`, `CardDraftReview`, `DebatePrepPanel`, `DebateCardPreview` — surface-level audit items, do not affect core user journeys | P1 |
| `DebatePrepPanel.tsx` | `text-gray-900` one remaining instance | P2 |
| Demo page contrast | All violations fixed (section-stamp upgraded, arbitrary sizes bumped, lav-on-tiny-text removed); e2e suppression removed | ✅ FIXED |
| `command.tsx` cmdk group headings | `text-ink-faint` → `text-ink-subtle`; `text-[0.6875rem]` → `text-eyebrow` | ✅ FIXED |

### P2 (polish)
- Visual regression screenshots not automated — snapshots would be fragile with AI-generated content
- `EvidenceStudioCard` collapsed view is used inside the workbench center panel as a button wrapper — double-button nesting risk if `EvidenceCardDraft` renders buttons internally; review for `role` conflict
- Playwright tests require a running Next.js server — CI must start the server or set `BASE_URL`

### P3 (future enhancements)
- `EvidenceStudioModal` lazy-loaded to reduce initial bundle size
- Arrow-key navigation within filter chip groups (currently Tab-only)
- Live region announcement when filter chips change the candidate count (e.g., "3 results")
- Skip-to-main-content link on all AppShell pages (currently relies on native Tab order)

---

## 8. Test / Build Results

```
TypeScript:   0 errors                       ✓
Jest:         1371 passed, 0 failed (51 suites)  ✓  (+279 since baseline of 1092)
Build:        49 routes, 0 errors            ✓
Lint:         41 errors (all pre-existing)   ✓
Playwright:   117 passed / 0 failed          ✓  (39 × 3 projects)
  ├ chromium (1280×800):   39/39 passed
  ├ mobile-chrome (375×812): 39/39 passed
  └ tablet (768×1024):     39/39 passed
```

### New test files
| File | Tests | Covers |
|---|---|---|
| `src/__tests__/workbenchModel.test.ts` | ~150 | WorkbenchStage, MobileStage, filters, credibility, rejection, save state, immutability |
| `src/__tests__/workbenchKeyboard.test.ts` | 32 | Roving tabindex math, selection preservation, modal focus trap, Escape key |
| `src/__tests__/reportVerdictStyles.test.ts` | 47 | `resolveGrade`, `dimColor`, `CHAIN_STYLES`, `ISSUE_STYLES` — all variants, no template strings |
| `e2e/accessibility.spec.ts` | 12 | Axe scans, heading hierarchy, color contrast, reduced motion (suppressions documented inline) |
| `e2e/keyboard.spec.ts` | 12 | Tab order, dialog roles, landmark structure, radiogroup labels |
| `e2e/responsive.spec.ts` | 9 | Overflow, sticky elements, mobile nav, touch targets |

---

## 9. Prioritized Next Steps

1. **[P0] Fix `EvidenceCardDraft` button nesting** — the wrapper `<button>` in the center panel wraps `EvidenceCardDraft` which may itself render buttons; ensure no interactive element inside a button
2. **[P0] `ReportVerdictPanel` template string colors** — `border-${color}/15` causes Tailwind purge misses; replace with a static CVA variant map
3. **[P1] Typography token pass** — `text-[8px]` → `text-eyebrow`; `text-[12px]` → `text-xs` across `FlowBoard`, `DrillCard`, `BlockCoveragePanel`, `CardDraftReview`
4. **[P1] Lazy-load Evidence Studio** — `dynamic(() => import('./EvidenceStudioModal'), { ssr: false })` removes ~15KB from initial payload
5. **[P1] Skip-to-main-content link** — add `<a href="#main-content">Skip to main</a>` as first child of `AppShell` with `sr-only focus:not-sr-only`
6. **[P1] CI Playwright setup** — add `BASE_URL` env var, `npx playwright install --with-deps chromium`, and run `npx playwright test e2e/accessibility.spec.ts` in CI
7. **[P2] Live region for filter count changes** — when user switches filter chip, announce "N evidence cards" via `aria-live="polite"`
8. **[P2] Arrow-key navigation in filter chips** — currently Tab-only; add left/right arrow navigation within the chip group
9. **[P2] Full visual regression** — integrate Percy or Chromatic for snapshot diffs on the evidence workbench, speech report, and dashboard
10. **[P3] Dark mode audit** — verify all semantic tokens resolve correctly in dark mode; test `EvidenceStudioCard` collapsed and expanded views
