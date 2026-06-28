# Dissio Design System

> Reference for Claude Code and contributors. Read this before touching any UI component.
> Source of truth for tokens: `frontend/src/app/globals.css`. Principles defined here.

---

## Visual principles

1. **Debate structure is the design** — every surface should evoke a flow sheet, a ballot, or a judge's desk. Not a generic dashboard.
2. **Product interface is the marketing** — show real UI states, not abstract illustrations.
3. **One section, one idea** — never stack identical rhythms.
4. **Color earns meaning** — `lav/ok/warn/danger` are semantic signals, never decoration.
5. **Motion explains state** — animate workflow progression and state transitions only. Never perpetual.
6. **Surface hierarchy before shadows** — stack canvas/surface-1/surface-2 rather than adding box-shadows.
7. **Errors are UI, not exceptions** — every error state includes a recovery action.

---

## Color roles

### Dark mode (default)

```
canvas          #010102  oklch(0.065)  Page background — darkest
surface-1       #0f1011  oklch(0.115)  Cards, panels
surface-2       #141516  oklch(0.140)  Sub-cards, raised elements
surface-3       #18191a  oklch(0.160)  Dropdowns, popovers
hairline        #23252a  oklch(0.210)  Standard borders
hairline-strong #34343a  oklch(0.270)  Emphasis borders
ink             #f7f8f8  oklch(0.975)  Primary text
ink-muted       #d0d6e0  oklch(0.860)  Secondary text
ink-subtle      #8a8f98  oklch(0.630)  Tertiary text — labels, stamps (AA on surface-1 ✓)
ink-faint       #62666d  oklch(0.490)  Decorative only — timestamps (NOT labels)
```

### Accent colors

```
lav             #5e6ad2  oklch(0.510 0.156 278)  Brand/action (CTAs, active states, AI provenance)
lav-hi          #828fff  oklch(0.660 0.130 278)  Hover state for lav
ok              #27a644  oklch(0.620 0.170 145)  Live argument, success, improvement
warn            amber    oklch(0.750 0.155  74)  Contested, weak, issue detected
danger          red      oklch(0.640 0.215  25)  Dropped, error, missing
cyan                     oklch(0.780 0.140 200)  Coach-authored content
```

### Semantic debate colors

```
flow-live      = ok     (live / extended argument)
flow-contested = warn   (weak / under attack)
flow-dropped   = danger (conceded / missing)
authored-user  = ink    (student-authored)
authored-ai    = lav    (AI-proposed)
authored-coach = cyan   (coach-authored)
ev-strong      = ok
ev-weak        = warn
ev-unverified  = ink-subtle
```

### Contrast rules (dark mode)

| Text | Background | Ratio | Use |
|------|-----------|-------|-----|
| ink | surface-1 | ~17:1 ✓ | Primary labels |
| ink-subtle | surface-1 | ~5.9:1 ✓ | Secondary labels, stamps |
| ink-faint | surface-1 | ~3.4:1 ✗ | Decorative only |
| lav | surface-1 | ~3.5:1 ✗ | Interactive elements only, bold ≥14px |
| ok | surface-1 | ~5.1:1 ✓ | Semantic (bold at ≤14px) |
| warn | surface-1 | ~9.2:1 ✓ | Semantic |

**Never use `ink-faint` for label or stamp text. Never use `lav` for static text at eyebrow size.**

---

## Typography hierarchy

Six semantic levels. Use only these. No `text-[Npx]` in production code.

| Class | Size | Weight | Tracking | Use |
|-------|------|--------|---------|-----|
| `.text-display` | 3rem | 700 | −0.035em | Hero h1 only |
| `.text-headline` | 1.75rem | 600 | −0.025em | Section h2 |
| `.text-title` | 1.25rem | 600 | −0.02em | Page/card h1 |
| `.text-heading` | 0.9375rem | 600 | −0.01em | Card h2, sub-sections |
| `.text-eyebrow` | 0.6875rem | 600 | +0.06em / uppercase | All labels, stamps, badges |
| `text-base` | 1rem | 400 | — | Body copy |
| `text-sm` | 0.875rem | 400 | — | Supporting copy, list items |
| `text-xs` | 0.75rem | 400 | — | Meta, timestamps, captions |

### Fonts

```
Space Grotesk    → sans (display, UI copy)
JetBrains Mono   → mono (section-stamp, rep-badge, flow-step, code)
```

No third font. Both are loaded via Next.js font optimization in `layout.tsx`.

---

## Spacing scale

Tailwind 4px base. Prefer named steps.

```
gap-1   4px    inline elements, tight pairs
gap-2   8px    default inline gap
gap-3   12px   card internal gap
gap-4   16px   card padding unit
gap-6   24px   between cards
gap-8   32px   between sections (mobile)
gap-12  48px   between major blocks
gap-16  64px   section padding (mobile)
gap-20  80px   section padding (desktop)
```

Section vertical padding: `py-20` desktop, `py-12` mobile.
Page horizontal padding: `px-6`.
Max widths: `max-w-6xl` (content), `max-w-5xl` (focused), `max-w-lg` (CTA).

---

## Border hierarchy

```
border-hairline        → standard card/panel border
border-hairline-strong → active state, emphasis
border-lav/20          → lav-tinted accent (use sparingly — semantic only)
border-ok/25           → success badge border
border-warn/25         → warning context border
border-danger/20       → error context border
```

---

## Surface hierarchy

```
bg-canvas    → page background
bg-surface-1 → cards, panels, modals
bg-surface-2 → raised sub-cards, active row highlight
bg-surface-3 → dropdowns, tooltips
```

Always use **solid** backgrounds on inner panels inside `aria-hidden` containers.
`backdrop-blur` on semi-transparent backgrounds prevents Axe from computing contrast accurately and
causes framing artifacts on the dark canvas. Use `bg-surface-1` not `bg-surface-1/80 backdrop-blur`.

### Named surface utilities

```css
.surface-flow      /* argument maps, flow tables */
.surface-ballot    /* judge scoring panels */
.surface-practice  /* drill workspace */
.surface-evidence  /* case file, card-cutting */
.surface-mission   /* dashboard next-action card */
```

---

## Radii

```
rounded-sm    4px   tight inline elements, badges
rounded-md    8px   buttons, inputs (default shadcn)
rounded-lg    12px  smaller cards, chips
rounded-xl    16px  standard cards
rounded-2xl   24px  hero panels, large cards
rounded-full        pills, avatars
```

---

## Shadow rules

Use only when element genuinely floats above content:

```
shadow-xs  → focus ring-style (prefer ring utilities)
shadow-sm  → slightly elevated (rarely needed on dark canvas)
shadow-md  → modals, dropdowns
shadow-lg  → command menu, popovers
```

`glow-lav` is only for the primary CTA (`bg-lav` button). One per page.
`beam-top` animation is only for `HeroDebateConsole` and the pipeline showcase.

---

## Interaction states

Every interactive element must define all six states:

| State | Treatment |
|-------|-----------|
| Default | `text-ink-subtle border-hairline` |
| Hover | `text-ink border-hairline-strong` or `hover:bg-surface-1` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-lav/50` (never remove outline) |
| Active/pressed | `active:scale-[0.98]` or `bg-surface-2` |
| Disabled | `opacity-50 cursor-not-allowed pointer-events-none` |
| Loading | Spinner or skeleton, never blank |

Touch targets: minimum 44 × 44px. Use padding to achieve this, not just `h-9`.

---

## Motion durations and easing

```javascript
// lib/motion.ts
fast:   150ms  // hover, focus, micro-interactions
base:   300ms  // entrance, tab transitions
slow:   500ms  // page-level entrances
EASE:   [0.25, 0.1, 0.25, 1]  // cubic-bezier
```

Always use `reducedSafe()` from `lib/motion.ts`:
```tsx
import { reducedSafe, fadeUp } from "@/lib/motion";
const anim = reducedSafe(fadeUp(0.1));
```

**Never animate inner elements inside `aria-hidden` containers** with `initial={{ opacity: 0 }}` —
this causes Axe color-contrast false positives during scan at partial opacity.

---

## Responsive rules

```
Mobile:   < 768px   (sidebar hidden, bottom nav visible)
Tablet:  ≥ 768px   (sidebar visible at 60px collapsed)
Laptop:  ≥ 1024px  (sidebar expanded at 240px)
Desktop: ≥ 1280px  (comfortable line lengths)
```

---

## Empty, loading, error, success states

Every page with async data must handle all four.

### Loading
Use section-specific skeletons that match expected content layout.
Never bare `<Skeleton className="h-32 w-full" />` alone.

### Empty
Use `EmptyState` component:
```tsx
<EmptyState
  Icon={TrendingUp}
  title="Your progress starts here."
  description="Record a speech to begin tracking your skill trajectory."
  action={{ label: "Start practicing", href: "/session" }}
/>
```

### Error
```tsx
<div role="alert" className="flex items-start gap-3 rounded-xl border border-danger/25 bg-danger/5 px-4 py-3">
  <AlertTriangle size={16} className="mt-0.5 shrink-0 text-danger" aria-hidden />
  <div className="flex flex-col gap-2">
    <p className="text-sm text-danger">{message}</p>
    <button onClick={retry} className="w-fit text-xs font-medium text-danger underline">Retry</button>
  </div>
</div>
```

Use `isBackendUnreachable(e)` from `lib/api.ts` to distinguish network errors from API errors.

### Success
Brief inline feedback via `sonner` toast or `ok`-colored badge. No full-page success states.

---

## Debate-specific motifs

```
.section-stamp   → mono eyebrow label for section headers
.rep-badge       → mono score/attempt counter (tiny, mono, 2px border-radius)
.flow-step       → rectangular ordered label for argument steps
.ballot-header   → top-weighted border on scoring areas
.beam-top        → animated top-edge sweep (hero panel only — not general purpose)
.glow-lav        → primary CTA glow (one per page, on bg-lav buttons only)
```

---

## What NOT to do

```tsx
// ✗ Arbitrary font size
<span className="text-[9px]">Label</span>

// ✗ ink-faint on a label (fails WCAG AA)
<p className="text-eyebrow text-ink-faint">Stage</p>

// ✗ lav text on decorative element (fails AA at eyebrow size)
<span className="text-eyebrow text-lav">Step 1</span>

// ✗ Semi-transparent backdrop on inner panel
<div className="bg-surface-1/80 backdrop-blur-sm">

// ✗ Perpetual animation on content element
<motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity }}>

// ✗ motion.div inside aria-hidden with initial={{ opacity: 0 }}
<div aria-hidden="true">
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

// ✗ Error swallowed silently
} catch (e) {
  console.error(e);  // no UI state update — user sees nothing
}

// ✗ Hardcoded Tailwind colors (instead of tokens)
<div className="bg-zinc-900 text-gray-400">

// ✗ Fabricated metrics or roadmap claims
<p>10,000+ students coached · Cross-ex analysis coming soon</p>

// ✗ glow-lav on non-CTA
<div className="glow-lav">Some decorative card</div>

// ✗ beam-top on non-hero panels
<div className="beam-top rounded-xl border ...">Regular card</div>
```

---

*Last updated: 2026-06-20. See `docs/DISSIO_DESIGN_DIRECTION.md` for the full improvement plan.*
