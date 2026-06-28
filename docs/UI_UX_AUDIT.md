# Dissio UI/UX Audit

> **Date:** 2026-06-19 | **Branch:** ui/homepage-transformation  
> **Scope:** Shared foundation pass — identify structural gaps before any page-specific redesigns.
>
> **Updated:** 2026-06-19 — Production-readiness pass; resolved items marked ✅ FIXED below.

---

## 1. Route Inventory

| Route | AppShell | Loading State | Empty State | Error State | Notes |
|-------|----------|---------------|-------------|-------------|-------|
| `/` | No (marketing) | — | — | — | Dual-mode: logged-in greeting vs. full pitch |
| `/login` | No | — | — | — | Single-form page, no data fetching |
| `/auth/callback` | No | Spinner | — | Redirect | OAuth handler |
| `/dashboard` | Yes (full, bare) | PageSkeleton + SpeechSkeleton × 3 | FirstRunCommandCenter | Recovery banner | 20+ panel conditionals |
| `/session` | Yes | — | — | — | 4-step wizard, no async loading |
| `/speech/[id]` | Yes | SpeechProcessingWorkspace | — | SpeechFailureState | 4 workspace states |
| `/progress` | Yes | PageSkeleton | EmptyStateCard (no data) | — | |
| `/learn` | Yes | PageSkeleton | EmptyStateCard | — | |
| `/drills/[id]` | Yes | PageSkeleton | — | — | |
| `/evidence` | Yes | PageSkeleton | EmptyState (library) | — | Library + Builder tabs |
| `/team` | Yes | PageSkeleton | Inline empty | — | Coach/student role gates |
| `/team/assign` | Yes | — | — | — | |
| `/team/review` | Yes | PageSkeleton | Inline empty | — | |
| `/team/student` | Yes | PageSkeleton | — | — | |
| `/pilot` | Yes | PageSkeleton | — | — | |
| `/demo` | No (public) | Inline skeleton | — | — | |
| `/share/[token]` | No (public) | Inline skeleton | — | — | |
| `/evals` | Yes | — | — | — | |

**Gap:** `/team`, `/team/review` have inline string empties instead of the `EmptyState` component.

---

## 2. Typography Violations

The system defines 6 semantic levels (display/headline/title/heading/eyebrow + text-xs/sm/base). Components widely bypass this.

### Arbitrary pixel sizes found

| Class | Locations | Correct replacement |
|-------|-----------|---------------------|
| `text-[8px]` | DashboardCockpitBand, FlowBoard | `text-eyebrow` or remove |
| `text-[9px]` | FlowBoard, ReportVerdictPanel, DrillCard, `reportPrimitives.tsx` | `text-eyebrow` |
| `text-[10px]` | FlowTable, ImprovementReceipt, BlockCoveragePanel (×4) | `text-eyebrow` |
| `text-[11px]` | FlowBoard, BlockCoveragePanel, ImprovementReceipt | `text-eyebrow` |
| `text-[12px]` | CardDraftReview (×6) | `text-xs` |
| `text-[13px]` | `evidence/DebatePrepPanel.tsx` | `text-xs` or `text-sm` |
| `text-[15px]` | CardDraftReview | `text-heading` |
| `text-[16px]` | `evidence/DebateCardPreview.tsx` | `text-base` |

### Semantic heading level mismatches

| File | Tag | Visual class | Issue |
|------|-----|-------------|-------|
| `ReportVerdictPanel.tsx` | `<h1>` | `text-2xl` | Should be `<h1 className="text-headline">` |
| `EmptyStateCard.tsx` | `<h3>` | `text-lg font-semibold` | Should use `text-heading` |
| `TournamentWorkoutPanel.tsx` | `<h3>` | `text-sm font-semibold` | Should use `text-heading` |
| `evidence/DebatePrepPanel.tsx` | `<h3>` | `text-[13px] font-semibold text-gray-900` | Triple violation: arbitrary size, wrong heading class, off-system color |
| `FlowEditPanel.tsx` | `<h3>` | `text-heading` | Correct |

---

## 3. Color Violations

### Hardcoded Tailwind colors (bypass design tokens)

| File | Violations | Correct token | Status |
|------|-----------|---------------|--------|
| `AnalysisProgressCard.tsx` | `border-red-500/30 bg-red-950/20`, `bg-red-600 hover:bg-red-500`, `text-red-400`, `text-blue-400 bg-blue-500` | `border-danger/30 bg-danger/10`, `Button variant="destructive"`, `text-danger`, `text-lav bg-lav` | Open |
| `CardDraftReview.tsx` | `bg-white border-gray-200`, `text-gray-900/500/400`, `hover:bg-rose-50 hover:text-rose-500`, `bg-gray-900 text-white` | `bg-surface-1 border-hairline`, `text-ink/ink-subtle/ink-faint`, `hover:bg-danger/10 hover:text-danger`, `Button variant="default"` | Open |
| `evidence/DebatePrepPanel.tsx` | `text-gray-900` | `text-ink` | Open |
| `EvidenceSearchPanel.tsx` | `bg-gray-50 border border-border/50` | `bg-surface-1 border-hairline` | Open |
| `CoachReportView.tsx` | Multiple `print:*` using `gray-*` | Use semantic tokens or `print:text-foreground` | Open |
| `FlowTable.tsx` | `bg-amber/10 text-amber` | Token `amber` exists in `@theme inline` — this one is OK | OK |
| `evidence/EvidenceSearchProgress.tsx` | All `gray-*`, `bg-white` | Semantic tokens | ✅ FIXED |
| `evidence/CardAnalysis.tsx` | `gray-*`, `emerald-*`, `rose-*` | `text-ok`, `text-danger`, `text-ink-*` | ✅ FIXED |
| `evidence/CoachNotesPanel.tsx` | All category color strings | Semantic tokens | ✅ FIXED |
| `evidence/EvidenceStudioCard.tsx` | 30+ violations across `gray/amber/orange/emerald/rose` | Semantic tokens | ✅ FIXED |
| `evidence/EvidenceStudioModal.tsx` | `bg-white` | `bg-surface-1` | ✅ FIXED |
| `lib/researchHelpers.ts` | All badge styles used raw Tailwind colors | `bg-ok/10 text-ok`, `bg-warn/10 text-warn`, etc. | ✅ FIXED |
| `ReportVerdictPanel.tsx` | `border-${color}/15`, `ring.replace("border-","bg-")` template strings | Static maps in `lib/reportVerdictStyles.ts` | ✅ FIXED |
| `app/login/page.tsx` | Toggle buttons `text-lav` (3.6:1 fails AA); divider `text-ink-faint` on white card | `text-ink` + underline; `text-ink-subtle` for divider | ✅ FIXED |
| `app/not-found.tsx` | `text-ink-faint` eyebrow label (contrast fails) | `text-ink-subtle` | ✅ FIXED |

### Dynamic template string classes (Tailwind cannot purge)

```tsx
// ReportVerdictPanel.tsx — generates classes Tailwind can't statically analyse:
className={`rounded-lg border border-${color}/15 bg-${color}/5 px-3 py-2`}
className={`flex items-start gap-2 rounded-lg border border-${color}/15 bg-surface-1`}
className={`text-${color} text-sm font-medium`}
```
**Fix:** Use a lookup map or CVA variants keyed to the color name.

---

## 4. Button Inconsistencies

The `ui/button.tsx` CVA component is the correct building block. These locations bypass it with inline Tailwind:

| File | Custom button classes | Correct approach |
|------|----------------------|-----------------|
| `PracticeLoopCTA.tsx` | `rounded-md bg-lav px-3.5 py-2 text-xs font-semibold text-white hover:bg-lav-hi` | `<Button size="sm">` |
| `AnalysisProgressCard.tsx` | `rounded-lg bg-red-600 px-4 py-2 text-sm hover:bg-red-500` | `<Button variant="destructive">` |
| `CardDraftReview.tsx` | `rounded-lg bg-gray-900 text-white hover:bg-gray-700` | `<Button>` |
| `TranscriptPanel.tsx` | `rounded-md border border-danger/25 bg-danger/10 px-2.5 py-1.5 text-xs text-danger hover:bg-danger/15` | `<Button variant="destructive" size="sm">` |

**Accessibility gap:** None of these inline buttons have `focus-visible` styles. Keyboard users get no visible focus indicator.

---

## 5. Card & Surface Inconsistencies

### Radius violations

| Class | Where | Should be |
|-------|-------|-----------|
| `rounded-[2px]` | DashboardCockpitBand inner elements | `rounded-sm` (4px) |
| `rounded-[3px]` | FlowBoard, DrillCard, DocumentCard | `rounded-sm` (4px) |
| `rounded-xl` | AnalysisProgressCard (error state) | Consistent with `Card` (already `rounded-xl`) |
| `rounded-2xl` | Icon container in EmptyStateCard | OK for large icons — intended |

### Off-system background colors on cards

| File | Class | Should be |
|------|-------|-----------|
| `AnalysisProgressCard.tsx` (error) | `border border-red-500/30 bg-red-950/20` | `border-danger/30 bg-danger/5` |
| `AnalysisProgressCard.tsx` (normal) | `border border-white/10 bg-white/5` | `border-hairline bg-surface-1` |
| `CardDraftReview.tsx` | `bg-white border-gray-200` | `bg-surface-1 border-hairline` |

### Competing empty-state component APIs

| Component | Icon prop | Action type | Motion |
|-----------|-----------|-------------|--------|
| `EmptyState.tsx` | `Icon: LucideIcon` (capital) | `href` only | None |
| `EmptyStateCard.tsx` | `icon: LucideIcon` (lowercase) | `href` or `onAction` | motion.div wrapper |

**Fix:** Unified `ui/empty-state.tsx` (new primitive, see Design System).

---

## 6. Focus Style Audit

### `focus:` vs `focus-visible:` (accessibility critical)

`focus:` triggers on mouse click too, creating unexpected outlines. `focus-visible:` is the correct pattern.

| File | Issue | Status |
|------|-------|--------|
| `ui/input.tsx` | Uses `focus-visible:` ✅ | OK |
| `ui/button.tsx` | Uses `focus-visible:` ✅ | OK |
| `PracticeLoopCTA.tsx` | `focus-visible:ring-2 focus-visible:ring-lav/50` on all CTAs | ✅ CONFIRMED |
| `AnalysisProgressCard.tsx` | Uses `<Button variant="destructive">` (focus handled) | ✅ CONFIRMED |
| `CardDraftReview.tsx` | All buttons have `focus-visible:ring-2 focus-visible:ring-lav/50` | ✅ CONFIRMED |
| `TranscriptPanel.tsx` | All buttons have `focus-visible:ring-2 focus-visible:ring-lav/50` | ✅ CONFIRMED |
| `FlowBoard.tsx` | Cells have `focus-visible:ring-2`; scroll container has `tabindex="0"` | ✅ CONFIRMED + FIXED |
| `FlowCanvas.tsx` | All interactive nodes have `focus-visible:ring-2 focus-visible:ring-lav/50` | ✅ CONFIRMED |
| Radix-based (Dialog, Sheet, Tabs, etc.) | `focus-visible:` from shadcn defaults ✅ | OK |
| `evidence/EvidenceStudioCard.tsx` | All interactive elements now use `ring-lav/50` | ✅ FIXED |
| `evidence/EvidenceStudioModal.tsx` | Focus trap + focus restoration added | ✅ FIXED |
| `evidence/CoachNotesPanel.tsx` expand button | `focus-visible:ring-2 focus-visible:ring-inset` added | ✅ FIXED |
| `app/evidence/page.tsx` candidate list | Roving tabindex; ArrowUp/Down/Home/End navigation | ✅ FIXED |
| `app/login/page.tsx` toggle buttons | Added `focus-visible:ring-2 focus-visible:ring-lav/50` | ✅ FIXED |

---

## 7. Reduced Motion

### CSS animations (all covered)
`globals.css` has a comprehensive `@media (prefers-reduced-motion: reduce)` block that disables `.shimmer`, `.beam-top::after`, `.step-pulse`, `.rec-pulse`, `.analysis-step-active`, and sets all transitions/animations to 0.01ms.

### JavaScript animations (gap)
`motion/react` (framer-motion v12) components do **not** automatically check `prefers-reduced-motion`. Components using `motion.div` with `fadeUp()`, `staggerParent()`, etc. will still animate even when the user requests reduced motion.

**Current exposure:**
- `/` landing page — heavy `fadeUpInView` stagger chains
- `/dashboard` — stagger animations on panels
- `EmptyStateCard.tsx` — `initial={{ opacity:0, scale:0.95 }}` entrance

**Fix added:** `reducedSafe()` utility in `motion.ts` (see Design System).

---

## 8. Light Mode Scrollbar (Bug)

```css
/* Current — hardcoded to dark values: */
::-webkit-scrollbar-thumb { background: oklch(0.270 0.006 264); }
::-webkit-scrollbar-thumb:hover { background: oklch(0.370 0.006 264); }
```

In light mode, these dark scrollbar thumbs contrast badly against the light canvas. Fix uses `var(--theme-hairline-strong)` and `var(--theme-ink-faint)`.

---

## 9. Missing Shadow Tokens

The design avoids heavy drop shadows (elevation expressed through surface layering). However, there is no formal shadow scale, which means:
- Components that do need subtle shadows (modals, dropdowns, floating toolbars) reach for ad-hoc values or nothing
- `CardDraftReview.tsx` uses `hover:shadow-sm` (Tailwind default black shadow — breaks light mode aesthetic)

**Fix:** Add `--shadow-xs/sm/md/lg` tokens to `@theme inline` using ink-tinted shadows.

---

## 10. Responsive Behavior

### Known gaps
- `/evidence` Evidence Studio modal (`min(1400px,96vw) × min(900px,92vh)`) — on narrow tablets (768px) this leaves only 4vw margin. Should have a min-margin of 16px.
- `/team` coach roster table has no horizontal scroll on mobile — clips on <375px.
- FlowCanvas horizontal scroll works but has no visible scroll indicator on mobile.
- `DashboardCockpitBand` stat row wraps awkwardly at sm breakpoint — stats go to 2 columns but card does not reflow cleanly.

### What works well
- AppShell: mobile-first, bottom tab nav, sidebar hidden on mobile ✅
- FlowBoard: snap carousel on mobile ✅  
- Evidence Studio card rows: stack vertically on mobile ✅
- PWA manifest + safe-area insets ✅

---

## 11. Navigation Consistency

- All authenticated routes use AppShell with consistent sidebar/mobile nav ✅
- Breadcrumbs via `headerLeft` are used on some routes but not others (session, evidence lack breadcrumbs)
- `aria-current="page"` set on active nav items ✅
- Cmd-K command menu accessible globally ✅
- Skip-to-content link present ✅

---

## 12. Loading / Empty / Error State Coverage

| State type | Covered by | Gaps |
|------------|-----------|------|
| Route loading | `PageSkeleton` | Some routes show blank flash before client hydration |
| Inline data loading | `Skeleton` + `LoadingCard` | Inconsistent: some use custom shimmer divs |
| Empty states | `EmptyState` + `EmptyStateCard` | Two APIs, inline strings in team pages |
| Error states | `SpeechFailureState`, `RouteError`, recovery banner | Other routes lack error boundaries |
| Not found | `SpeechNotFoundState` | Only for speech routes; other 404s fall back to Next.js default |
| Analysis progress | `AnalysisProgressCard`, `EvidenceSearchProgress` | Custom implementations, should use `StatusChip` |
