# Dissio Visual Review Checklist

> Complete this checklist manually before approving any homepage or application redesign stage.  
> Technical tests (TypeScript, Jest, Playwright) are necessary but not sufficient.

---

## Required viewports

| Label | Dimensions | Device |
|-------|-----------|--------|
| Desktop | 1440 × 900 | Wide laptop / external monitor |
| Laptop | 1280 × 800 | 13–14" MacBook |
| Tablet landscape | 1024 × 768 | iPad 10.9" landscape |
| Tablet portrait | 768 × 1024 | iPad 10.9" portrait |
| Mobile | 390 × 844 | iPhone 14 / Pixel 7 |

---

## Homepage `/`

### First impression (5-second test)

- [ ] The page reads as a debate-training product within 5 seconds
- [ ] The headline is immediately legible
- [ ] The `HeroDebateConsole` is visible and identifiable as a product preview
- [ ] The primary CTA ("Start practicing") is visible without scrolling at 1280 × 800
- [ ] No horizontal scroll at 375px
- [ ] No oversized neon glow, floating orbs, or generic AI gradients

### Hero section

- [ ] Headline line breaks look intentional at all viewports (1440 / 1280 / 1024 / 768 / 390)
- [ ] The three-line verb structure (`Speak. / Get flowed. / Drill what matters.`) is preserved
- [ ] `HeroDebateConsole` does not clip, overflow, or compress its content at 768px
- [ ] Console is right-aligned on desktop, stacked below text on mobile
- [ ] The radial glow behind the console is subtle (not dominant)
- [ ] The dot-grid / coordinate texture is visible but not distracting
- [ ] Trust marks (`Free to start / No coach required / Coaching, not cheating`) are legible
- [ ] Judge type pills are legible at all sizes

### Animation sequence (HeroDebateConsole)

- [ ] Waveform bars animate in (stagger, not all at once)
- [ ] Stage strip lights up sequentially
- [ ] Flow chain nodes appear one by one
- [ ] Ballot score fills to 78
- [ ] "Drill unlocked" panel appears last
- [ ] Full sequence completes in under 2.5 seconds
- [ ] Under `prefers-reduced-motion`: **all elements are visible at rest, no animation**
- [ ] After sequence ends: **no perpetual animations**

### Proof rail

- [ ] Renders as a grounded section (solid background, hairline borders)
- [ ] Not floating or blurry
- [ ] Three metrics are defensible and legible
- [ ] `<60s`, `5 dimensions`, `3 drills` are the correct values

### Workflow section (`#how-it-works`)

- [ ] Four steps are visible: Speak, Flow, Ballot, Drill
- [ ] Active step is clearly indicated
- [ ] Clicking/pressing a step updates the preview panel
- [ ] Arrow key navigation works between steps (keyboard)
- [ ] At 390px, steps render as a stacked/accordion, not a horizontal row
- [ ] Product preview on the right is a real Dissio UI state, not an abstract illustration
- [ ] Section is usable without JavaScript (first step open by default)

### Debate proof section (`#product-proof`)

- [ ] Shows one coherent example (speech excerpt → flow → ballot note → drill)
- [ ] Cannot be mistaken for a generic AI product section
- [ ] The `ImprovementLanes` comparison is included
- [ ] Before/after contrast is clear

### Judge lens section (`#judge-lens`)

- [ ] `JudgeLensComparison` renders correctly at 768px
- [ ] Tab/segmented control is accessible (keyboard navigable)
- [ ] Three lenses: Lay, Flow, Tech Judge
- [ ] Feedback shown is meaningfully different per lens (not just a badge change)

### Evidence section (`#evidence`)

- [ ] `EvidenceProvenanceStrip` renders with source/AI provenance color distinction
- [ ] Source quote badge and AI tag badge are both visible and distinct

### Coaches section (`#for-coaches`)

- [ ] `TeamWorkflowStrip` renders correctly
- [ ] The coach loop stages are all visible

### CTA section

- [ ] Primary CTA is the most visually dominant element in the final viewport
- [ ] No oversized glow box or decorative icon
- [ ] Secondary action (demo link) is visually quieter than primary
- [ ] "No credit card required" or equivalent trust note is present but not competing

### Footer

- [ ] All nav links point to real routes or section anchors
- [ ] No "coming soon" or roadmap language
- [ ] Footer `nav[aria-label="Footer"]` is accessible

---

## Application shell

### Sidebar (desktop)

- [ ] Active state: `bg-lav/8` tint + left bar indicator visible
- [ ] Active state is clearly but not aggressively different from inactive
- [ ] Group labels are legible but not visually dominant
- [ ] Loop strip ("Practice › Analyze › Drill › Improve") is visible at bottom
- [ ] Collapse toggle works; collapsed shows icons + tooltips only
- [ ] Collapsed state does not overlap content

### Mobile nav

- [ ] Bottom tab bar is visible at 390px
- [ ] Touch targets are ≥ 44px
- [ ] Active tab is clearly indicated
- [ ] "More" sheet opens on tap

### Top header

- [ ] Brand link visible on mobile (sidebar hidden)
- [ ] `⌘K` search button visible on desktop
- [ ] Theme toggle works
- [ ] No extra height or layout shift on load

---

## Dashboard `/dashboard`

### New user (0 speeches)

- [ ] One clear primary action ("Start your first practice rep" or equivalent)
- [ ] Secondary action: sample report
- [ ] No competing panels all asking for the same thing
- [ ] Greeting is visible and personalized (if logged in)

### Returning user (≥ 1 speech)

- [ ] Latest speech status or recent activity is first
- [ ] Coaching focus card appears (if progress data exists)
- [ ] Next drill is visible without scrolling
- [ ] History is below the fold

### Loading state

- [ ] Content skeleton fills expected layout (not bare rectangles at random positions)
- [ ] No flash of blank white space

### Error state

- [ ] Error message is visible
- [ ] Message distinguishes backend-unreachable from API error
- [ ] At least one recovery action (Retry or Refresh)

---

## Progress page `/progress`

### Loading

- [ ] Skeleton cards match section count and shape

### Empty (0 speeches)

- [ ] `EmptyState` component with icon, title, description, CTA
- [ ] Not a plain sentence in a Card
- [ ] CTA goes to `/session`

### Error

- [ ] Error banner with `AlertTriangle`
- [ ] Retry action
- [ ] Not just a text string

### Data state

- [ ] Coaching focus is first
- [ ] Skill trend is second
- [ ] Milestones and weekly plan visible
- [ ] No blank sections for missing data (hidden gracefully)

---

## Side-by-side comparison template

When approving a changed section, document before and after here:

### Homepage hero
| Aspect | Before | After |
|--------|--------|-------|
| Proof rail background | `bg-surface-1/70 backdrop-blur-sm` (floating) | `bg-surface-1 border-y border-hairline` (grounded) |
| Judge type pills | `text-[10px]` | `text-eyebrow` |
| Trust marks | `text-ink-faint` (too faint) | `text-ink-subtle` |
| HeroDebateConsole | Static | One-shot animation sequence |

*Add rows as each change is implemented.*

---

## Playwright screenshot capture

The following pages should have Playwright screenshots captured at the required viewports:

```bash
# Capture homepage at 1280x800 and 390x844
npx playwright test --project=chromium e2e/accessibility.spec.ts --screenshot=on
```

Compare screenshots before and after each stage using:
- Stage 2 screenshots: homepage only
- Stage 3 screenshots: homepage (updated sections)
- Stage 4 screenshots: dashboard, progress

---

## Final approval gate

A stage is approved only when:

1. TypeScript: clean (`npx tsc --noEmit`)
2. Jest: all existing tests pass
3. Build: `npm run build` green
4. Playwright: all accessibility and e2e tests pass
5. This checklist: all relevant boxes checked
6. Side-by-side comparison documented
7. No item in §9 "Prohibited Regressions" triggered

Approval is **not** granted by test results alone.
