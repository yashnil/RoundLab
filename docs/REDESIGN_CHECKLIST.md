# RoundLab Redesign Checklist

> **Foundation pass complete** (see `DESIGN_SYSTEM.md`).  
> This checklist tracks per-file migration work. Complete P0 before shipping; P1 before beta.

Priority key: **P0** blocks shipping · **P1** design debt · **P2** polish · **P3** enhancement

---

## P0 — Accessibility Blockers

These missing focus styles make the product unusable for keyboard users.

- [x] `PracticeLoopCTA.tsx` — Already has `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50` on all interactive elements (stale audit item — verified 2026-06-19)
- [x] `AnalysisProgressCard.tsx` — Already uses `<Button variant="destructive">` (stale audit item — verified 2026-06-19)
- [x] `CardDraftReview.tsx` — All buttons have `focus-visible:ring-2 focus-visible:ring-lav/50`; card uses `bg-surface-1 border-hairline` (stale audit item — verified 2026-06-19)
- [x] `TranscriptPanel.tsx` — All buttons have `focus-visible:ring-2 focus-visible:ring-lav/50` (stale audit item — verified 2026-06-19)
- [x] `FlowBoard.tsx` — Interactive cells have `focus-visible:ring-2 focus-visible:ring-lav/50`; scroll container has `tabindex="0" role="region"` (stale audit + scrollable-region fix 2026-06-19)
- [x] `FlowCanvas.tsx` — All interactive nodes have `focus-visible:ring-2 focus-visible:ring-lav/50` (stale audit item — verified 2026-06-19)

---

## P1 — Design Token Violations

Fix all hardcoded Tailwind colors and arbitrary text sizes.

### Color violations

- [ ] `AnalysisProgressCard.tsx`:
  - `border-red-500/30 bg-red-950/20` → `border-danger/30 bg-danger/5`
  - `text-red-400`, `text-red-300`, `text-red-400/80` → `text-danger`
  - `text-blue-400`, `bg-blue-500` → `text-lav`, `bg-lav`
  - `border border-white/10 bg-white/5` → `border-hairline bg-surface-1`
- [ ] `CardDraftReview.tsx`:
  - `bg-white border-gray-200` → `bg-surface-1 border-hairline`
  - `text-gray-900`, `text-gray-500`, `text-gray-400` → `text-ink`, `text-ink-subtle`, `text-ink-faint`
  - `hover:bg-rose-50 hover:text-rose-500` → `hover:bg-danger/10 hover:text-danger`
- [ ] `evidence/DebatePrepPanel.tsx`:
  - `text-gray-900` → `text-ink`
- [ ] `EvidenceSearchPanel.tsx`:
  - `bg-gray-50 border border-border/50` → `bg-surface-1 border-hairline`
- [ ] `CoachReportView.tsx`:
  - Audit print: styles; replace `gray-*` with semantic equivalents or `print:text-foreground`
- [x] `ReportVerdictPanel.tsx`:
  - `border-${color}/15` and `ring.replace("border-","bg-")` template strings → extracted to `lib/reportVerdictStyles.ts` static maps (`CHAIN_STYLES`, `ISSUE_STYLES`, `resolveGrade`, `dimColor`); 47 unit tests added

### Typography violations

- [x] `globals.css` `.section-stamp` — 0.625rem/ink-faint → 0.6875rem/ink-subtle (visual craft pass 2026-06-19)
- [x] `ui/command.tsx` cmdk group-heading — `text-ink-faint` → `text-ink-subtle`; `text-[0.6875rem]` → `text-eyebrow` (visual craft pass 2026-06-19)
- [x] `shell/MobileNav.tsx` tab labels — `text-[0.625rem]` → `text-eyebrow`; nav group label ink-faint → ink-subtle
- [x] `shell/AppSidebar.tsx` nav group label — ink-faint → ink-subtle
- [x] `dashboard/PracticeRecipes.tsx` — `text-[0.625rem] text-ink-faint` → `text-eyebrow text-ink-subtle`
- [x] `dashboard/NextActionPanel.tsx` — `text-[0.6875rem]` → `text-eyebrow`
- [x] `dashboard/CoachingFocusCard.tsx` — `text-[0.6875rem] text-ink-faint` → `text-eyebrow text-ink-subtle`
- [x] `dashboard/QuickStartRow.tsx` — `text-[0.6875rem] text-ink-faint` → `text-eyebrow text-ink-subtle`
- [x] `dashboard/LoopStageCard.tsx` — `text-[9px] text-ink-faint` → `text-xs text-ink-subtle`; `text-[10px]` → `text-xs`; `text-[11px]` → `text-xs`; ink-faint → ink-subtle throughout
- [x] `DrillCard.tsx` — `text-[11px]` → `text-xs`; ink-faint → ink-subtle
- [x] `FlowBoard.tsx` — column card `rounded-[3px]` → `rounded-sm`
- [x] `app/demo/page.tsx` — all arbitrary sizes (8–11px) bumped to text-eyebrow/text-xs; all ink-faint → ink-subtle; lav-on-small removed; suppression in e2e tests removed
- [x] `app/evidence/page.tsx` — eyebrow labels ink-faint → ink-subtle; form label sizes text-[11px] → text-xs; 8/9px lead card labels → text-eyebrow; lav on tiny text → ink-subtle; filter chip text-[11px] → text-xs; all other 9/10/11px occurrences bumped
- [ ] `DashboardCockpitBand.tsx` — `text-[8px]` → `text-eyebrow` or omit (file not found — may have been renamed)
- [ ] `ReportVerdictPanel.tsx` — `text-[9px]` → `text-eyebrow`; `<h1>` level → use `text-headline`
- [ ] `reportPrimitives.tsx` — `text-[9px]` → `text-eyebrow`
- [ ] `FlowTable.tsx` — `text-[10px]` → `text-eyebrow`
- [ ] `ImprovementReceipt.tsx` — `text-[10px]`, `text-[11px]` → `text-eyebrow`
- [ ] `BlockCoveragePanel.tsx` — `text-[10px]`, `text-[11px]` → `text-eyebrow`
- [ ] `CardDraftReview.tsx` — `text-[12px]` → `text-xs`; `text-[15px]` → `text-heading`
- [ ] `evidence/DebatePrepPanel.tsx` — `text-[13px] font-semibold text-gray-900` → `text-heading text-ink`
- [ ] `evidence/DebateCardPreview.tsx` — `text-[16px]` → `text-base`

### Radius violations

- [x] `FlowBoard.tsx` — column card `rounded-[3px]` → `rounded-sm` (visual craft pass 2026-06-19)
- [x] `DrillCard.tsx` — order-number badge `rounded-[3px]` → `rounded-sm` (visual craft pass 2026-06-19)
- [ ] `DashboardCockpitBand.tsx` — `rounded-[2px]` → `rounded-sm` (file not found — may have been renamed)
- [ ] `DocumentCard.tsx` — `rounded-[3px]` → `rounded-sm`

---

## P2 — Semantic & Polish

Improve hierarchy, consolidate components, fix light mode rendering.

### Heading hierarchy

- [ ] `ReportVerdictPanel.tsx` — `<h1 className="text-2xl font-bold">` → `<h1 className="text-headline">`
- [ ] `EmptyStateCard.tsx` — `<h3 className="text-lg font-semibold">` → `<h3 className="text-heading">`
- [ ] `TournamentWorkoutPanel.tsx` — `<h3 className="text-sm font-semibold">` → `<h3 className="text-heading">`
- [ ] `evidence/DebatePrepPanel.tsx` — fix triple violation (heading level + size + color)

### Component migration

- [ ] Migrate `EmptyState.tsx` usages → `import { EmptyState } from "@/components/ui/empty-state"`
  - `/evidence/page.tsx` (library empty)
  - `SpeechReportWorkspace.tsx`
- [ ] Migrate `EmptyStateCard.tsx` usages → `ui/empty-state`
  - `/dashboard/page.tsx` (empty speech list)
  - `/progress/page.tsx`
  - `/learn/page.tsx`
- [ ] Inline empty states in `/team/page.tsx`, `/team/review/page.tsx` → `<EmptyState>`
- [ ] Inline status badges in `reportPrimitives.tsx` → `<StatusChip>`
- [ ] Inline status badges in `SpeechProcessingTimeline.tsx` → `<StatusChip>`

### Light mode fixes

- [ ] Audit scrollbar rendering in light mode (fix already applied in globals.css)
- [ ] `AnalysisProgressCard.tsx` normal state `border-white/10 bg-white/5` — invisible in light mode
- [ ] `EvidenceStudioModal.tsx` minimum margin on narrow tablets (add `min-[calc(100vw-32px)]` clamp)

### Motion

- [ ] `/` landing page `fadeUpInView` stagger chains — wrap with `reducedSafe()`
- [ ] `/dashboard` stagger panel animations — wrap with `reducedSafe()`
- [ ] `EmptyStateCard.tsx` entrance animation — wrap with `reducedSafe()`

---

## P3 — Enhancement

Nice to have. Do not block earlier priorities.

### Design token linting

- [ ] Add ESLint rule to flag `text-gray-*`, `bg-white`, `bg-black`, `border-gray-*` (use `eslint-plugin-tailwindcss` or custom regex rule)
- [ ] Add Tailwind v4 safelist for any intentionally dynamic class patterns

### Storybook

- [ ] Set up Storybook 8 with Tailwind v4 support
- [ ] Stories for: Button (all variants), Card, EmptyState, StatusChip, SectionHeader, Skeleton, Badge
- [ ] Visual regression baseline for dark/light themes

### Accessibility audit

- [ ] Run axe-core on all routes
- [ ] NVDA/VoiceOver test on: login, session setup, speech report, evidence library
- [ ] Verify all images and icons have `aria-label` or `aria-hidden`

### Responsive edge cases

- [ ] `/evidence` EvidenceStudioModal narrow tablet margin fix
- [ ] `/team` coach roster table — add horizontal scroll wrapper on mobile
- [ ] `DashboardCockpitBand` stat row — fix 2-column wrap at sm breakpoint

---

## Foundation Work Completed

These are done in the current pass and can be crossed off:

- [x] Shadow token scale (`--shadow-xs/sm/md/lg`) added to `@theme inline`
- [x] Scrollbar colors fixed for light mode (theme-aware CSS vars)
- [x] `.focus-ring` utility added to `@layer utilities`
- [x] `ui/status-chip.tsx` — new unified status indicator component
- [x] `ui/empty-state.tsx` — new unified empty state component
- [x] `SectionHeader.tsx` — `eyebrow` + `level` props added
- [x] `motion.ts` — `reducedSafe()` + `MOTION_NOOP` added
- [x] `docs/UI_UX_AUDIT.md` — comprehensive audit documented
- [x] `docs/DESIGN_SYSTEM.md` — design system reference created
- [x] `docs/REDESIGN_CHECKLIST.md` — this file

## Verification Pass Completed (2026-06-19)

- [x] All 6 P0 focus-ring items confirmed present via code inspection — checklist was stale
- [x] `ReportVerdictPanel.tsx` — template-string Tailwind classes extracted to `lib/reportVerdictStyles.ts` static maps; `glowBg` field added; 47 unit tests in `reportVerdictStyles.test.ts`
- [x] `app/login/page.tsx` — toggle buttons changed to `text-ink` with decorative lav underline (was `text-lav` with 3.6:1 contrast, below AA); divider span `text-ink-faint` → `text-ink-subtle`
- [x] `app/demo/page.tsx` — evidence library `Link` gets persistent `underline underline-offset-2` (fixed `link-in-text-block` violation)
- [x] `app/not-found.tsx` — eyebrow `text-ink-faint` → `text-ink-subtle` (fixed contrast on 404 page)
- [x] `components/FlowBoard.tsx` — scroll container gets `tabindex="0" role="region"` (fixed `scrollable-region-focusable`)
- [x] Playwright: all 39 tests pass on Chromium · mobile-chrome · tablet (768px Chromium)
- [x] `playwright.config.ts` — tablet project switched from iPad/WebKit to Chromium-at-768px (WebKit requires separate `playwright install webkit`)

## Production-Readiness Pass Completed (2026-06-19)

- [x] `evidence/EvidenceSearchProgress.tsx` — all hardcoded colors → tokens; `animate-pulse` → `motion-safe:`; `role="progressbar"` on outer wrapper with `aria-label`
- [x] `evidence/CardAnalysis.tsx` — all hardcoded colors → tokens (`text-ok`, `text-danger`, `text-ink-subtle`, etc.)
- [x] `evidence/CoachNotesPanel.tsx` — all 7 category color strings → semantic tokens; `aria-expanded` on expand button; decorative icons `aria-hidden`
- [x] `evidence/EvidenceStudioCard.tsx` — 30+ violations fixed: gray/amber/orange/emerald/rose → tokens; Cut controls get `role="radiogroup"`/`role="radio"`/`aria-checked`; focus rings → `ring-lav/50`; readiness dot gets `aria-hidden`
- [x] `evidence/EvidenceStudioModal.tsx` — focus trap (Tab/Shift+Tab cycles within modal); focus restoration to trigger on close; `bg-white` → `bg-surface-1`
- [x] `app/evidence/page.tsx` — roving tabindex candidate keyboard navigation; `role="listbox"` + `role="option"` + `aria-selected`; `handleCandidateKeyDown` for ArrowUp/Down/Home/End
- [x] `lib/workbenchModel.ts` — `isCutTextSubstringOfBody` bug fixed (split before remove)
- [x] `lib/researchHelpers.ts` — all badge styles use semantic tokens
- [x] `@playwright/test` + `@axe-core/playwright` installed
- [x] `playwright.config.ts` created (3 projects: Chromium, mobile Chrome, tablet)
- [x] `e2e/accessibility.spec.ts` — Axe scans, heading hierarchy, color contrast, reduced motion
- [x] `e2e/keyboard.spec.ts` — Tab order, focus indicators, dialog roles, landmark structure
- [x] `e2e/responsive.spec.ts` — Overflow, sticky elements, touch targets, broken images
- [x] `src/__tests__/workbenchKeyboard.test.ts` — 32 unit tests for roving tabindex, modal focus trap, Escape key
- [x] `docs/UI_UX_OVERHAUL_REPORT.md` — created

## Visual Craft Pass Completed (2026-06-19)

- [x] `globals.css` `.section-stamp` — font-size 0.625rem→0.6875rem (10px→11px); color ink-faint→ink-subtle
- [x] `ui/command.tsx` — cmdk group-heading `text-[0.6875rem]`→`text-eyebrow`; `text-ink-faint`→`text-ink-subtle` (fixes Axe violation)
- [x] `shell/MobileNav.tsx` — nav tab labels `text-[0.625rem]`→`text-eyebrow`; sheet group labels ink-faint→ink-subtle
- [x] `shell/AppSidebar.tsx` — nav group labels ink-faint→ink-subtle
- [x] `dashboard/PracticeRecipes.tsx` — `text-[0.625rem] text-ink-faint`→`text-eyebrow text-ink-subtle` for sub-group labels and duration
- [x] `dashboard/NextActionPanel.tsx` — `text-[0.6875rem]`→`text-eyebrow` for action eyebrow
- [x] `dashboard/CoachingFocusCard.tsx` — `text-[0.6875rem] text-ink-faint`→`text-eyebrow text-ink-subtle`
- [x] `dashboard/QuickStartRow.tsx` — `text-[0.6875rem] text-ink-faint`→`text-eyebrow text-ink-subtle`
- [x] `dashboard/LoopStageCard.tsx` — `text-[9px]`→`text-xs`, `text-[10px]`→`text-xs`, `text-[11px]`→`text-xs`; all ink-faint→ink-subtle; "Training loop" label contrast fixed
- [x] `DrillCard.tsx` — order badge `rounded-[3px]`→`rounded-sm`; `text-[11px]`→`text-xs`; ink-faint→ink-subtle
- [x] `FlowBoard.tsx` — column card `rounded-[3px]`→`rounded-sm`
- [x] `app/demo/page.tsx` — comprehensive contrast fix: all 8–11px labels bumped to text-eyebrow/text-xs; all ink-faint→ink-subtle; lav removed from tiny text; Evidence Library link uses ink default color with lav decoration; HelpNote "?" badge bg-lav/15 text-lav-hi
- [x] `e2e/accessibility.spec.ts` — removed `disableRules: ["color-contrast"]` suppression from demo page tests (violations are now fixed, not suppressed)
- [x] `app/evidence/page.tsx` — section eyebrow labels ink-faint→ink-subtle; 8/9/10/11px arbitrary sizes→text-eyebrow or text-xs; lav-on-small→ink-subtle; filter chip buttons text-[11px]→text-xs; "Best match" badge text-[9px]→text-eyebrow; weak lead card labels bumped to scale

**Test results:** TypeScript clean · Jest 1371/1371 · build 49 routes · lint 41 errors (baseline, unchanged)
