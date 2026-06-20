# RoundLab Design System

> Single source of truth for tokens, components, and usage patterns.  
> Tailwind 4 + shadcn/ui + Space Grotesk + JetBrains Mono.

---

## 1. Color Tokens

All colors are CSS custom properties registered in `globals.css` `@theme inline`. Use as Tailwind utilities: `bg-canvas`, `text-ink`, `border-hairline`, etc.

### Surface ladder (theme-aware)

| Token | Tailwind class | Dark | Light | Use for |
|-------|---------------|------|-------|---------|
| `--color-canvas` | `bg-canvas` | `#010102` | `#f9f9fb` | Page background |
| `--color-surface-1` | `bg-surface-1` | `#0f1011` | `#ffffff` | Cards, panels |
| `--color-surface-2` | `bg-surface-2` | `#141516` | `#f4f4f6` | Raised elements, inputs |
| `--color-surface-3` | `bg-surface-3` | `#18191a` | `#eeeef0` | Dropdowns, tooltips |
| `--color-hairline` | `border-hairline` | `#23252a` | `#dddde0` | Default 1px borders |
| `--color-hairline-strong` | `border-hairline-strong` | `#34343a` | `#c0c0c4` | Heavy/accent borders |

### Ink hierarchy (theme-aware)

| Token | Tailwind class | Dark | Light | Use for |
|-------|---------------|------|-------|---------|
| `--color-ink` | `text-ink` | `#f7f8f8` | `#0e0e11` | Primary body text |
| `--color-ink-muted` | `text-ink-muted` | `#d0d6e0` | `#3c3c46` | Secondary text |
| `--color-ink-subtle` | `text-ink-subtle` | `#8a8f98` | `#6e6e78` | Tertiary/meta text |
| `--color-ink-faint` | `text-ink-faint` | `#62666d` | `#a0a0a8` | Disabled/placeholder |

### Brand accents (consistent across themes)

| Token | Tailwind | Value | Use for |
|-------|---------|-------|---------|
| `--color-lav` | `text-lav`, `bg-lav`, `border-lav` | `#5e6ad2` | Primary accent, CTAs |
| `--color-lav-hi` | `text-lav-hi`, `bg-lav-hi` | `#828fff` | Hover state of lav |
| `--color-lav-lo` | `border-lav-lo` | deep lavender | Focus rings |
| `--color-cyan` | `text-cyan`, `bg-cyan` | bright cyan | Secondary accent |
| `--color-cyan-hi` | `text-cyan-hi` | brighter cyan | Hover of cyan |

### Semantic (consistent across themes)

| Token | Tailwind | Use for |
|-------|---------|---------|
| `--color-ok` | `text-ok`, `bg-ok` | Success, passed, extended arguments |
| `--color-warn` | `text-warn`, `bg-warn` | Warning, contested arguments |
| `--color-danger` | `text-danger`, `bg-danger` | Error, dropped arguments, destructive |
| `--color-info` | `text-info`, `bg-info` | Informational callouts |

### Debate-semantic tokens

| Token | Mapped to | Use for |
|-------|----------|---------|
| `--color-flow-live` | `ok` | Extended/live argument |
| `--color-flow-contested` | `warn` | Contested/weak argument |
| `--color-flow-dropped` | `danger` | Dropped argument |
| `--color-ev-strong` | `ok` | Strong evidence |
| `--color-ev-weak` | `warn` | Weak evidence |
| `--color-pro` | teal-green | Affirmative side |
| `--color-con` | warm red | Negative side |
| `--color-authored-coach` | `cyan` | Coach-written content |
| `--color-authored-ai` | `lav` | AI-generated content |
| `--color-authored-user` | `ink` | User-written content |
| `--color-skill-up` | `ok` | Skill improving |
| `--color-skill-down` | `danger` | Skill declining |

### Argument type colors

`blue`, `violet`, `orange`, `amber`, `indigo`, `green` — each has a `-hi` variant. Used for argument type labeling in FlowCanvas and report cards.

---

## 2. Typography Scale

Six semantic levels only. **Never use `text-[Npx]` arbitrary sizes.**

```
Level       Class           Size      Weight  Tracking   Use for
──────────────────────────────────────────────────────────────────
Display     .text-display   3rem      700     -0.035em   Hero headlines (landing only)
Headline    .text-headline  1.75rem   600     -0.025em   Page openers, major sections
Title       .text-title     1.25rem   600     -0.020em   Card/panel titles
Heading     .text-heading   0.9375rem 600     -0.010em   Section headers, sub-labels
Eyebrow     .text-eyebrow   0.6875rem 600     +0.060em   Mono stamps, category labels (UPPERCASE auto)
────────── Tailwind defaults ────────────────────────────────────
Body lg     text-base       1rem (16) 400     0          Standard body text
Body        text-sm         0.875rem  400     0          Secondary body, descriptions
Caption     text-xs         0.75rem   400     0          Labels, timestamps, meta
```

**Font families:**
- `font-sans` → Space Grotesk (body default)
- `font-mono` → JetBrains Mono (use for `.section-stamp`, `.rep-badge`, code)
- `font-display` → Space Grotesk (explicit for heroes)

---

## 3. Spacing Conventions

No formal spacing scale beyond Tailwind defaults. Follow these conventions:

| Context | Pattern |
|---------|---------|
| Card interior padding | `p-5` (20px) |
| Card interior — compact | `px-4 py-3` |
| Section gap | `gap-4` (16px) between sections within a page |
| Item gap | `gap-2` (8px) between list items / rows |
| Section header → content | `mt-4` |
| Page padding | `px-4 py-6 sm:px-6 sm:py-8` (via AppShell) |
| Inline icon + label | `gap-1.5` |

---

## 4. Radius Scale

| Token | Value | Class | Use for |
|-------|-------|-------|---------|
| `--radius-sm` | 4px | `rounded-sm` | Compact chips, flow steps, `.surface-flow` |
| `--radius-md` | 8px | `rounded-md` | Inputs, small buttons, dropdowns |
| `--radius-lg` | 12px | `rounded-lg` | Medium cards, badges |
| `--radius-xl` | 16px | `rounded-xl` | Primary cards (`Card` component) |
| `--radius-2xl` | 24px | `rounded-2xl` | Large modals, hero cards |

**Never use:** `rounded-[2px]`, `rounded-[3px]`, `rounded-full` for rectangular elements.

---

## 5. Shadow Scale (New)

Added to `@theme inline`. Used only where surface layering is insufficient (modals, floating toolbars).

| Token | CSS | Use for |
|-------|-----|---------|
| `--shadow-xs` | 0 1px 2px ink/8% | Subtle card lift |
| `--shadow-sm` | 0 1px 3px ink/10% + 0 1px 2px ink/6% | Dropdowns, tooltips |
| `--shadow-md` | 0 4px 6px ink/7% + 0 2px 4px ink/6% | Floating action bars |
| `--shadow-lg` | 0 10px 15px ink/10% + 0 4px 6px ink/5% | Modals, EvidenceStudioModal |

**Note:** Ink-tinted shadows (not black) so they adapt gracefully in light mode.

---

## 6. Surface Taxonomy

Use the appropriate surface for each context. Never override with inline background colors.

| Class | Radius | Border | Background | Use for |
|-------|--------|--------|-----------|---------|
| `Card` component | xl (16px) | 1px hairline | surface-1 | Default content card |
| `.surface-flow` | sm (4px) | 1px hairline | surface-1 | Argument maps, flow tables |
| `.surface-ballot` | 0 0 sm sm | 2px top + 1px sides | surface-1 | Scoring panels, judge feedback |
| `.surface-practice` | 6px | 1px lav/18 | lav/2 | Drill workspace |
| `.surface-evidence` | 2px | 1px hairline + 2px left strong | surface-1 | Case files, evidence cards |
| `.surface-mission` | 6px | 1px lav/20 | lav/6→lav/2 gradient | Dashboard CTAs |

---

## 7. Motion Presets

Import from `@/lib/motion`. Never hardcode transition values in components.

```ts
import { fadeUp, fadeIn, fadeUpInView, staggerParent, staggerChild,
         cardHover, T, reducedSafe, MOTION_NOOP } from "@/lib/motion";

// Entrance animation
<motion.div {...reducedSafe(fadeUp(0.1))} />

// Stagger list
<motion.ul variants={staggerParent()} initial="hidden" animate="show">
  <motion.li variants={staggerChild} />
</motion.ul>

// Card hover
<motion.div {...cardHover} />

// When user prefers reduced motion
<motion.div {...reducedSafe(fadeUpInView())} />
```

**`reducedSafe(props)`** — wraps any motion prop factory and returns `MOTION_NOOP` when `prefers-reduced-motion: reduce` is set. Always use on entrance animations (fadeUp, stagger, etc.).

**Timing constants (T):**
- `T.fast` — 150ms, smooth easing
- `T.base` — 300ms, smooth easing
- `T.slow` — 500ms, smooth easing
- `T.spring` — spring(360, 30) — confident snaps
- `T.snap` — spring(500, 38) — immediate precision

---

## 8. Component Inventory

### Shell (authenticated chrome)
| Component | Path | Purpose |
|-----------|------|---------|
| `AppShell` | `shell/AppShell.tsx` | Root authenticated container (sidebar + header + mobile nav) |
| `AppSidebar` | `shell/AppSidebar.tsx` | Collapsible grouped navigation |
| `MobileNav` | `shell/MobileNav.tsx` | Fixed bottom tab bar (mobile) |
| `CommandMenu` | `shell/CommandMenu.tsx` | Cmd-K global command palette |
| `ProductHeader` | `shell/ProductHeader.tsx` | Sticky header with slot props |
| `PageSkeleton` | `shell/PageSkeleton.tsx` | Route-level loading state |
| `RouteError` | `shell/RouteError.tsx` | Route-level error boundary |

### UI Primitives (`components/ui/`)
| Component | Import | Purpose |
|-----------|--------|---------|
| `Button` | `ui/button` | All interactive buttons. Variants: default/outline/secondary/ghost/destructive/link. Sizes: xs/sm/default/lg + icon variants |
| `Card` + subs | `ui/card` | Content containers. Always use over raw divs with inline bg/border |
| `Input` | `ui/input` | Text inputs with focus-visible ring |
| `Badge` | `ui/badge` | Status/label badges |
| `Skeleton` | `ui/skeleton` | Shimmer placeholder (use via PageSkeleton) |
| `EmptyState` | `ui/empty-state` | **New unified empty state** (replaces legacy EmptyState.tsx + EmptyStateCard.tsx) |
| `StatusChip` | `ui/status-chip` | **New semantic status indicator** — ok/warn/danger/info/neutral/active/processing |
| `Dialog` | `ui/dialog` | Modal dialogs |
| `Sheet` | `ui/sheet` | Side drawers |
| `Tabs` | `ui/tabs` | Tab groups |
| `Tooltip` | `ui/tooltip` | Hover tooltips |
| `Progress` | `ui/progress` | Linear progress bar |
| `Separator` | `ui/separator` | Visual divider |
| `Sonner` | `ui/sonner` | Toast notifications (use `toast()` from sonner) |
| `Command` | `ui/command` | Command palette base (used by CommandMenu) |
| `DropdownMenu` | `ui/dropdown-menu` | Dropdown trigger + items |

### Shared components (`components/`)
| Component | Path | Purpose |
|-----------|------|---------|
| `SectionHeader` | `SectionHeader.tsx` | Section title + optional eyebrow/description/action |
| `EmptyState` (legacy) | `EmptyState.tsx` | **Deprecated** — migrate to `ui/empty-state` |
| `EmptyStateCard` (legacy) | `EmptyStateCard.tsx` | **Deprecated** — migrate to `ui/empty-state` |
| `ScoreRing` | `ScoreRing.tsx` | Circular score gauge |
| `WorkflowStepper` | `WorkflowStepper.tsx` | Ordered step indicator |
| `DeleteDialog` | `DeleteDialog.tsx` | Confirmation modal for destructive actions |

---

## 9. StatusChip Usage

```tsx
import { StatusChip } from "@/components/ui/status-chip";

// Static status
<StatusChip variant="ok" label="Extended" />
<StatusChip variant="warn" label="Contested" />
<StatusChip variant="danger" label="Dropped" />
<StatusChip variant="info" label="Informational" />
<StatusChip variant="neutral" label="Not started" />

// Active/processing with animated dot
<StatusChip variant="active" label="Recording" dot />
<StatusChip variant="processing" label="Analyzing" dot />

// Size variants
<StatusChip variant="ok" label="Pass" size="sm" />
<StatusChip variant="warn" label="Needs work" size="md" />
```

**Replaces:** ad-hoc inline badge divs in `reportPrimitives.tsx`, `SpeechProcessingTimeline.tsx`, inline status spans across pages.

---

## 10. EmptyState Usage

```tsx
import { EmptyState } from "@/components/ui/empty-state";
import { Mic } from "lucide-react";

// Basic
<EmptyState
  icon={Mic}
  title="No speeches yet"
  description="Record or upload a PF speech to start your practice loop."
/>

// With href action
<EmptyState
  icon={Mic}
  title="No speeches yet"
  description="Record or upload your first speech."
  action={{ label: "Start practice", href: "/session" }}
/>

// With onClick action
<EmptyState
  icon={BookOpen}
  title="No blocks yet"
  description="Search for evidence to build your block file."
  action={{ label: "Search evidence", onClick: () => openSearch() }}
/>

// With preview content and size
<EmptyState
  icon={Layers}
  title="No sets yet"
  description="Create an evidence set to organize your research."
  preview={<EvidenceSetPreview />}
  size="lg"
/>
```

---

## 11. SectionHeader Usage

```tsx
import SectionHeader from "@/components/SectionHeader";

// Standard
<SectionHeader title="Recent Activity" />

// With eyebrow (uses .section-stamp)
<SectionHeader
  eyebrow="Practice Loop"
  title="Recent Activity"
  description="Your last 10 practice speeches"
/>

// With action button
<SectionHeader
  title="Drills"
  badge="3"
  action={<Button size="sm" onClick={openDrills}>View all</Button>}
/>

// h3 level (inside a card, below an h2)
<SectionHeader level="h3" title="Claim Analysis" />
```

---

## 12. Focus Styles

### Built-in (Button, Input, Radix primitives)
All shadcn/ui primitives use `focus-visible:ring-2 focus-visible:ring-ring/50`. Do not override.

### Custom interactive elements
Apply the `.focus-ring` utility:
```tsx
<button className="focus-ring ... other classes">...</button>

// Or inline:
className="... focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
```

### Rule
- **Always** use `focus-visible:` not `focus:`
- **Never** use `outline-none` without replacing with a ring
- Every clickable element must have a visible keyboard focus indicator

---

## 13. Anti-Patterns

| Anti-pattern | Correct pattern |
|-------------|----------------|
| `bg-white`, `bg-black`, `bg-gray-*`, `bg-zinc-*` | `bg-canvas` / `bg-surface-1` / `bg-surface-2` |
| `text-gray-900`, `text-gray-500`, `text-gray-400` | `text-ink` / `text-ink-subtle` / `text-ink-faint` |
| `border-gray-200`, `border-white/10` | `border-hairline` / `border-hairline-strong` |
| `bg-red-600`, `text-red-400`, `bg-red-950/20` | `bg-danger` / `text-danger` / `bg-danger/10` |
| `text-[12px]`, `text-[13px]`, `text-[10px]` | `text-xs` / `text-eyebrow` / `text-sm` |
| `rounded-[2px]`, `rounded-[3px]` | `rounded-sm` (4px) |
| Inline `<button className="...">` | `<Button>` component |
| `focus:ring-*` | `focus-visible:ring-*` |
| `border-${color}/15` (template string) | CVA variant map or static class per variant |
| Direct `motion.div` without `reducedSafe()` | `motion.div {...reducedSafe(fadeUp())}` |
| `EmptyState` / `EmptyStateCard` imports | `import { EmptyState } from "@/components/ui/empty-state"` |
