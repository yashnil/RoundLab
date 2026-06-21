# RoundLab Design Direction

> **Date:** 2026-06-20  
> **Branch:** main (working, not yet committed)  
> **Author:** audit + direction pass before implementation  
> **Status:** Stage 1 complete — no production code changed yet

---

## 1. RoundLab Visual Identity

RoundLab's identity comes from **debate structure**, not from AI-product aesthetics.

The visual language must read like a serious judge's decision, not a chatbot or a homework helper.

### Core identity elements

| Element | Description |
|---------|-------------|
| **Color** | Near-black canvas (`oklch(0.065)`) with restrained lavender accent (`oklch(0.510 0.156 278)` = `#5e6ad2`). One semantic accent family, not a rainbow. |
| **Typography** | Space Grotesk (sans) + JetBrains Mono. Display type is tight and confident; code/labels are mono. |
| **Borders** | Hairline everywhere. Surfaces are defined by stacked thin borders, not drop shadows or glow effects. |
| **Iconography** | Lucide — consistent, thin-stroke, never filled or rounded outside shadcn components. |
| **Debate semantics** | `ok/warn/danger` map to `live/contested/dropped` arguments. `authored-user/authored-ai/authored-coach` provenance colors. Never use debate-semantic colors for decoration. |
| **Surface stack** | `canvas → surface-1 → surface-2 → surface-3`. Each step is slightly lighter. No arbitrary opacity layering. |
| **Motion** | Entrance, state change, and workflow transition only. Never perpetual. `motion/react` throughout. |

---

## 2. What Must Be Preserved

The following elements are working well and must not be changed or removed:

### Homepage

| Element | Why it works |
|---------|--------------|
| **HeroDebateConsole** | Completely unique — no other product shows this. The 2.5D product graphic at landing is the signature visual. |
| **Split hero composition** | Headline left + console right. The tension between the claim and the proof is deliberate. |
| `Speak. / Get flowed. / Drill what matters.` headline | Three-verb rhythm. Immediate clarity. Aggressive tracking. |
| **Dark canvas direction** | Premium, technical, distinct from SaaS templates. |
| **Judge type pills** in hero | "Lay judge / Flow judge / Tech judge / Coach" — product-specific proof, not a generic testimonials strip. |
| **`ArgumentHealthMatrix`** | Debate-native grid that no generic AI product could use. Strong visual. |
| **`JudgeLensComparison`** | One speech, multiple paradigms — core product differentiator. |
| **`ImprovementLanes`** | "Same speech, second attempt" — shows coaching not cheating in one glance. |
| **`EvidenceProvenanceStrip`** | The visual source/AI distinction. Exactly what the product promises. |
| **`TeamWorkflowStrip`** | Coach-loop flow — distinct from the student view. |
| **`WorkflowRail`** | The five-step loop. Can be refined but the concept is correct. |
| **`marketing.ts` model** | No roadmap language, all defensible claims. Do not introduce invented metrics. |
| **`section-stamp` utility** | Mono uppercase eyebrow label — debate-native texture. |
| **`beam-top` animation** | Subtle top-edge sweep. Use sparingly on hero panels only. |
| **`glow-lav`** | One primary CTA glow. No secondary glows. |
| **Font pairing** | Space Grotesk + JetBrains Mono. Do not add a third font. |
| **Design token system** | `canvas/surface-1/ink/hairline` hierarchy. All components must use tokens. |

### Application

| Element | Why it works |
|---------|--------------|
| **AppSidebar** collapse | Functional, keyboard-accessible. |
| **`section-stamp`** in sidebar loop strip | "Practice › Analyze › Drill › Improve" — product vocabulary visible at all times. |
| **Active nav state** | `bg-lav/8` + left indicator bar. Quiet but clear. |
| **`beam-top` on PipelineShowcase/HeroDebateConsole** | Only on those two surfaces. |
| **`surface-flow`, `surface-ballot`, `surface-evidence`** utilities | Debate context surfaces distinct from generic cards. |

---

## 3. Design Principles

These are extracted from studying Linear, Vercel/Geist, Resend, Raycast, and RoundLab-specific needs. They are translated — not copied.

### P1 · Product interface IS the marketing

Linear shows the actual issue list. Vercel shows the actual deployment log. Raycast shows the actual command palette.

RoundLab's HeroDebateConsole is the right instinct. **Every marketing section must show a real RoundLab UI state, not an abstract illustration.**

The argumentHealthMatrix, judgeLensComparison, improvementLanes, evidenceProvenanceStrip, and teamWorkflowStrip already do this. The PipelineShowcase does too, but it duplicates the hero.

**Implication:** Remove the PipelineShowcase "Capture" section. The hero already shows the pipeline.

### P2 · One section, one idea

The current homepage has 9 sections below the hero. Many have the same rhythm: `stamp / headline / blurb / motion-wrapped card`. The page becomes fatiguing.

**Target:** 6 sections below the hero (see §8). Each proves a *different* capability that could not be demonstrated by any other product.

### P3 · Motion explains state; it does not decorate space

Good motion: state transitions, workflow progression, hover/press micro-feedback.  
Bad motion: perpetually pulsing elements, waveforms that animate forever, text that slides in on scroll at every section.

The `PipelineShowcase` `useInViewOnce` trigger is the right pattern. The `HeroDebateConsole` should add a *short*, *one-shot* animation sequence.

**Rule:** Any animation that has no end state is a regression.

### P4 · Color earns meaning; it does not decorate

`lav` = brand/action (CTAs, active states, AI provenance).  
`ok` = live argument, success, improvement.  
`warn` = contested, weak, issue detected.  
`danger` = dropped, error, missing.  
`cyan` = coach-authored content.  

These colors must never be used purely for decoration, section differentiation, or visual interest.

### P5 · Typography has six levels; use all six

```
.text-display   → hero headline only
.text-headline  → section openers
.text-title     → page/card title
.text-heading   → sub-section / card header
.text-eyebrow   → labels, stamps, badges (always mono + uppercase)
text-sm, text-xs → body copy, detail
```

No `text-[9px]`, `text-[10px]`, `text-[11px]` in production code. Audit found these widely.

### P6 · Surface hierarchy before shadows

Four surface levels: `canvas → surface-1 → surface-2 → surface-3`.  
Prefer adding a `surface-1` card over adding a `box-shadow`.  
Use `shadow-sm` only when an element genuinely floats above page content (dropdowns, tooltips, modals).  
`beam-top` and `glow-lav` are reserved for the primary CTA and hero panel only.

### P7 · Debate-native language everywhere

Every section head, every badge, every label must speak in debate vocabulary.  
No "Analyze" when you mean "Flow". No "Insights" when you mean "Ballot feedback". No "Progress" when you mean "Skill trajectory".

### P8 · Errors are part of the UI, not exceptions

An error state is a first-class UI state. It must:
- Tell the user what happened
- Explain what to do next
- Offer one recovery action (Retry or navigate away)
- Never be just a sentence in a Card

---

## 4. Typography and Spacing Scale

### Type scale

```
.text-display   → 3rem / 700 / -0.035em  — hero h1 only
.text-headline  → 1.75rem / 600 / -0.025em — section h2
.text-title     → 1.25rem / 600 / -0.02em  — page/card h1
.text-heading   → 0.9375rem / 600 / -0.01em — card h2
.text-eyebrow   → 0.6875rem / 600 / 0.06em / uppercase — ALL labels/stamps
text-base       → 1rem / leading-relaxed — body copy
text-sm         → 0.875rem — supporting copy, list items
text-xs         → 0.75rem — meta, timestamps, captions
```

**Violations found in audit:** `text-[8px]`, `text-[9px]`, `text-[10px]`, `text-[11px]` throughout evidence components, `DashboardCockpitBand`, `FlowBoard`, `BlockCoveragePanel`. These are **deferred to Stage 4 evidence/component pass** and must not be introduced in Stages 2–3.

### Spacing scale

Use Tailwind's default 4px base: `gap-1 gap-2 gap-3 gap-4 gap-6 gap-8 gap-12 gap-16 gap-20 gap-24`.

Section vertical padding: `py-20` (desktop), `py-12` (mobile).  
Section max-width: `max-w-6xl` (content), `max-w-5xl` (focused), `max-w-lg` (CTA).  
Page horizontal padding: `px-6` (standard).

**Hero specifics:** `pt-16 pb-20 lg:pt-24 lg:pb-28` (current) — keep these values.

---

## 5. Surface and Border Hierarchy

```
canvas          → page background (darkest in dark mode)
surface-1       → cards, panels (step +1 from canvas)
surface-2       → raised elements, sub-cards (step +2)
surface-3       → dropdowns, popovers (step +3)
hairline        → standard borders
hairline-strong → emphasis borders (active states, heavy dividers)
```

**Rules:**
- Cards use `bg-surface-1 border border-hairline`
- Active nav uses `bg-lav/8` (not `bg-surface-2`)
- Proof strip uses `bg-surface-1` solid, not `/70 backdrop-blur` (which causes floating artifact)
- Inner panels in HeroDebateConsole use `bg-surface-1` solid for Axe contrast accuracy

**Current issue:** The proof strip uses `bg-surface-1/70 backdrop-blur-sm` which causes a detached floating look against the canvas. Fix: use `bg-surface-1` solid with `border-t border-b border-hairline`.

---

## 6. Motion Principles

### Use motion for:
- Entrance animations: `fadeUp(delay)`, `fadeUpInView(delay)` — 300–500ms, ease-out
- State transitions: tab content changes, workflow stage reveals — 200–300ms
- HeroDebateConsole one-shot sequence — see Stage 2 spec
- Hover/press micro-interactions — 100–150ms
- Loading → result transitions

### Never use motion for:
- Perpetually animating waveforms (unless actively recording)
- Parallax scroll effects
- Text that appears letter-by-letter or word-by-word
- Cards that animate on every scroll-into-view
- Multiple competing entrance animations in the same viewport

### Reduced motion:
Always use `reducedSafe()` from `lib/motion.ts` for entrance animations.  
Static `initial={{ opacity: 0 }}` in inner elements causes Axe color-contrast false positives — use plain divs inside `aria-hidden` containers.

### Duration reference:
```
fast:   150ms (hover, focus)
base:   300ms (entrance, transitions)
slow:   500ms (page sections)
spring: stiffness 360 / damping 30 (interactive feel)
EASE:   [0.25, 0.1, 0.25, 1] (defined in lib/motion.ts)
```

---

## 7. Color Reference

### Dark mode (default)
```
canvas        oklch(0.065 0.002 264)  ≈ #010102
surface-1     oklch(0.115 0.003 264)  ≈ #0f1011
surface-2     oklch(0.140 0.003 264)  ≈ #141516
hairline      oklch(0.210 0.005 264)  ≈ #23252a
ink           oklch(0.975 0.001 264)  ≈ #f7f8f8
ink-muted     oklch(0.860 0.008 264)  ≈ #d0d6e0
ink-subtle    oklch(0.630 0.007 264)  ≈ #8a8f98
ink-faint     oklch(0.490 0.006 264)  ≈ #62666d
lav           oklch(0.510 0.156 278)  = #5e6ad2
lav-hi        oklch(0.660 0.130 278)  = #828fff
ok            oklch(0.620 0.170 145)  = #27a644
warn          oklch(0.750 0.155 74)   = amber
danger        oklch(0.640 0.215 25)   = red
```

### Contrast AA minimums (dark mode)
- `ink` on `surface-1`: ≈ 17:1 ✓
- `ink-subtle` on `surface-1`: ≈ 5.9:1 ✓
- `ink-faint` on `surface-1`: ≈ 3.4:1 ✗ — use only for purely decorative text (never on labels)
- `lav` on `surface-1`: ≈ 3.5:1 ✗ — use only on interactive elements with ≥3px/bold font
- `ok` on `surface-1`: ≈ 5.1:1 ✓ (borderline — use bold at ≤14px)
- `warn` on `surface-1`: ≈ 9.2:1 ✓

**Rule:** All label text (badges, stamps, pills) must use `ink-subtle` or `ink-muted` minimum. `ink-faint` is for timestamps, meta, decorative elements only. Never use `lav` for text at `text-eyebrow` size unless it is an interactive element.

---

## 8. Page-Specific Improvement Plan

### 8.1 Homepage (Stage 2 + 3)

**Current: 10 sections** (Hero, Proof strip, Workflow, Capture/PipelineShowcase, Flow, Judge, Improve, Evidence, Team, Trust, SupportedToday, CTA)  
**Target: 8 sections** (Hero, Proof rail, Workflow, Debate proof, Judge lens, Evidence, Coaches, CTA)

#### Section removals / consolidations:
- **Remove:** "Capture" section with `PipelineShowcase` — duplicates the hero. The hero already demonstrates the pipeline.
- **Remove:** Standalone "Flow" section — the `ArgumentHealthMatrix` moves into the "Debate proof" section.
- **Remove:** Standalone "Improve" section — `ImprovementLanes` moves into the "Debate proof" section.
- **Remove:** "Trust" section (`TrustGrid`) — absorb key trust facts into hero trust marks and CTA.
- **Remove:** "Supported today" grid (`SupportedTodayGrid`) — move to footer or fold into CTA area as a compact 3-column capability list.

#### New/refined sections:

**§A. Hero** (Stage 2)
- Keep composition. Refine headline spacing and tracking.
- Add very subtle radial glow behind console (violet, 12% opacity maximum).
- Replace `bg-dots` (20px dot grid) with a `bg-grid` coordinate texture at even lower opacity — more structural, less generic.
- Fix `text-ink/70` in third headline line → `text-ink-muted` (uses token, not alpha).
- Fix trust marks: `text-ink-faint` → `text-ink-subtle`.
- Fix judge type pills: `text-[10px]` → `text-eyebrow`.
- Improve responsive behavior: on mobile, console stacks below hero text at `max-w-sm` centered.
- Add one-shot animation sequence to `HeroDebateConsole` (see §8.2).

**§B. Proof rail** (Stage 2)
- Replace `bg-surface-1/70 backdrop-blur-sm` with `bg-surface-1 border-t border-b border-hairline` — solid, grounded.
- Reduce divider to `sm:grid-cols-3` (3 metrics, not 4) for more breathing room.
- Better metric: replace `4 PF speech types covered` with `3 targeted drills` — more concrete outcome.
- New 3-metric structure:
  - `<60s` — Speech to structured report
  - `5 dimensions` — Judge-style scoring
  - `3 drills` — Targeted from your actual weakness

**§C. How it works / Workflow** (Stage 3)
- Replace the `WorkflowRail` (numbered list) with an interactive tabbed section.
- Four steps: **Speak → Flow → Ballot → Drill**
- Left column: step selector (vertical tab list on desktop, segmented control on mobile).
- Right column: actual RoundLab UI state for the selected step.
  - Speak: audio upload UI excerpt (from session page visual)
  - Flow: ArgumentHealthMatrix (reuse)
  - Ballot: judge verdict panel (ballot score + top three feedback lines)
  - Drill: drill card with specific exercise
- Keyboard: arrow keys navigate steps; no scroll-jacking.
- Mobile: stacked, one step expanded at a time.
- Static fallback: all four steps visible without JavaScript (accordion with first open).
- Section anchor: `#how-it-works`

**§D. Debate-specific proof** (Stage 3)
- The "See what the judge heard" concept.
- One coherent example: a 2-sentence speech excerpt → extracted flow → identified issue → ballot note → recommended drill.
- This can reuse `ImprovementLanes` in the bottom half (before/after re-record).
- Top half: argument chain excerpt → missing warrant → ballot note.
- No generic AI product could build this section.
- Section anchor: `#product-proof`

**§E. Judge lens** (Stage 3)
- Keep `JudgeLensComparison` as-is. It's strong.
- Wrap it in a section with a concise heading.
- Section anchor: `#judge-lens`

**§F. Evidence** (Stage 3)
- Keep `EvidenceProvenanceStrip`. Condense section heading.
- Section anchor: `#evidence`

**§G. For coaches** (Stage 3)
- Keep `TeamWorkflowStrip`. Condense section heading.
- Section anchor: `#for-coaches`

**§H. CTA** (Stage 3)
- Remove the glow icon box (too decorative).
- Two lines: headline + one sentence.
- One primary CTA (lav button). One quiet secondary (link to demo).
- Below the fold: 3-column capability reference (replaces SupportedTodayGrid).
- No "No credit card required" in a different element — fold it into the secondary CTA label.

**§I. Footer** (existing)
- Keep. Update anchor links to match new section IDs.

---

### 8.2 HeroDebateConsole animation sequence (Stage 2)

The console currently renders static. Add a short, restrained, one-shot sequence:

```
t=0ms    Console entrance: outer wrapper fades up (already in place via motion.div)
t=300ms  Waveform bars animate in: bars grow from bottom (stagger left→right)
t=700ms  Stage strip lights up: "Audio ✓" → "Flow ✓" → "Ballot ✓" → "Drill 🔓"
          (each stage label transitions color from ink-subtle → ink, with checkmark appearing)
t=1000ms Flow chain nodes appear: Claim, Warrant, Evidence, Impact (stagger left→right, fade up)
t=1300ms Issue row slides in from below (the "No weighing detected" warning)
t=1600ms Ballot score ring fills to 78: counter animates 0→78
t=1900ms "Drill unlocked" panel fades in with a subtle lav glow flash
```

**Reduced-motion fallback:** All elements visible in `initial` state; no animation. Use `reducedSafe()` for all inner animations.  
**Constraint:** Content must be readable at t=0 without waiting. `initial` state must show all text — only add reveal ON TOP of readable initial state.  
**Implementation:** Use `useReducedMotion` from motion/react. If reduced, render plain divs. If not, wrap in motion elements with the sequence timings.  
**No perpetual animations after the sequence ends.** The waveform does NOT continue pulsing.

---

### 8.3 Application shell (Stage 4)

**ProductHeader:**
- Keep current structure. Verify mobile brand shows correctly.
- The left slot (breadcrumb) renders on md+; on mobile the brand replaces it.

**AppSidebar:**
- Keep current active state (`bg-lav/8` + left bar).
- Group labels (`text-eyebrow px-2 pb-1.5 text-ink-subtle`): already correct.
- Collapse toggle: add `aria-label` improvements if needed.
- No user profile chip needed in this pass.

**Specific fix:** The sidebar `border-r border-sidebar-border` may need a `bg-sidebar` value review in light mode. Check that `--theme-sidebar: oklch(0.975 0.001 264)` renders distinctly from `canvas` in light mode.

---

### 8.4 Dashboard (Stage 4)

**Current hierarchy:** NextActionPanel → CoachingFocusCard → LoopStageCard → MidFunnelGuide → SkillTrajectory → DrillQueue → SpeechHistory

**Problem:** For new users, 3–4 empty-looking panels compete for attention.

**Target state for new users:**
1. One confident onboarding banner (the app knows you have no speeches yet)
2. One primary action: "Record your first speech" (large, lav button)
3. One secondary: "See a sample report" (link to /demo)
4. No redundant panels beneath

**Target state for returning users:**
1. Latest speech status or "Your last ballot" summary
2. Coaching focus (from progress data)
3. Next drill
4. Speech history (compact)

**Improvement approach (Stage 4):** Refine `dashboardModel.ts` `deriveDashboardState` to collapse redundant panels. Keep existing components, improve their conditional rendering.

---

### 8.5 Progress page (Stage 4)

**Current issues:**
- Error state is just a `<Card>` with a sentence in `text-danger`. Visually sparse.
- Empty state ("Start with one speech") is correct concept but the component needs refinement.
- No retry action for API errors.

**Target:**
- Loading: `DashboardSkeleton`-style content skeleton (not just `Skeleton` rectangles)
- Empty: `EmptyState` component with icon, title, description, one action
- API error: Error card with `AlertTriangle`, message, and a "Retry" button that triggers `window.location.reload()`
- Data: Current layout preserved

---

### 8.6 Learn page (Stage 4)

Fixed in this session: API errors now show an error banner. No further changes needed unless visual refinement pass identifies issues.

---

### 8.7 Evidence Studio (Stage 4 — minimal scope)

Do not change functional behavior. Only visual improvements:
- Fix `text-[8px]`/`text-[9px]`/`text-[10px]`/`text-[11px]` occurrences → `text-eyebrow`
- Fix `text-ink-faint` on non-decorative label text
- No structural changes to the card-cutting workflow

---

## 9. Prohibited Regressions

The following changes must never occur:

| Prohibited | Reason |
|------------|--------|
| Remove or replace `HeroDebateConsole` | It is the product's signature visual |
| Replace split hero with centered hero | The tension of claim vs. proof is structural |
| Add persistent "Skip to content" visible control | User requirement, creates visual noise |
| Add perpetual animations (waveforms, floating particles, pulsing) | Regresses to generic AI-product clichés |
| Change `canvas` background to white or light gray | Loses dark immersive direction |
| Add a second accent color family (e.g., orange, teal, pink) | Fragments the restrained palette |
| Use `text-[N]px` arbitrary sizes | Breaks the typography system |
| Use `text-ink-faint` for label text | Fails WCAG AA at `text-eyebrow` size |
| Add Aceternity UI, Magic UI, Chakra, Material, Mantine | Competing design systems |
| Add a large animation package | `motion/react` already handles all animation needs |
| Fabricate proof metrics or roadmap claims | `marketing.ts` enforces this — tests will catch it |
| Change API contracts or backend behavior | Out of scope |
| Remove `section-stamp`, `beam-top`, `glow-lav`, `surface-*` utilities | Debate-native texture layer |
| Add a Skip-to-content link anywhere | Removed per user requirement |
| Merge `authored-user`, `authored-ai`, `authored-coach` provenance colors | Core trust signal |
| Remove `ImprovementLanes`, `EvidenceProvenanceStrip`, `TeamWorkflowStrip` | Product-specific illustrations |

---

## 10. Visual Acceptance Checklist

This checklist must be completed manually before any stage is approved.

### Viewport sizes to review

- [ ] 1440 × 900 — full desktop
- [ ] 1280 × 800 — typical laptop
- [ ] 1024 × 768 — iPad landscape
- [ ] 768 × 1024 — iPad portrait
- [ ] 390 × 844 — iPhone 14

### Per-page review

**Homepage:**
- [ ] First impression: feels premium, debate-specific, not generic SaaS
- [ ] Hero visible without scrolling at 1280 × 800
- [ ] Console does not clip or overflow at 768px wide
- [ ] Animation sequence completes in < 2 seconds
- [ ] Animation does not play under `prefers-reduced-motion`
- [ ] Proof rail is grounded (not floating/blurry)
- [ ] Section count feels focused, not exhausting
- [ ] CTA is the most visually dominant element in the last viewport
- [ ] No horizontal overflow at 375px
- [ ] All text passes WCAG AA contrast
- [ ] Axe: zero critical or serious violations

**Dashboard:**
- [ ] New-user state: one clear primary action
- [ ] Returning-user state: latest speech is first thing visible
- [ ] Error state: visible, has retry
- [ ] Loading state: skeleton fills the expected layout
- [ ] No competing panels at any state

**Progress:**
- [ ] Loading: skeleton matches expected layout
- [ ] Empty: explains how to create progress (no blank void)
- [ ] Error: has retry, no raw error sentence
- [ ] Data state: coaching focus is first, skill trend second

**Application shell:**
- [ ] Sidebar active state is subtle but clear
- [ ] Collapsed sidebar shows tooltips on hover
- [ ] Mobile bottom nav tabs are usable at 390px

### Comparison rule

For every page-level change, document the **before** and **after** in plain language:  
*"Before: proof strip floated on blurry surface. After: solid `surface-1` with hairline borders."*

Playwright screenshots at the above viewports should be captured for `/` (homepage) at minimum.

---

## 11. Proposed File Scope by Stage

### Stage 2 — Homepage hero only

| File | Change |
|------|--------|
| `src/app/page.tsx` | Fix trust marks, judge pills, `text-ink/70` → `text-ink-muted`; hero grid `xl:` breakpoint review |
| `src/components/HeroDebateConsole.tsx` | Add one-shot animation sequence (waveform reveal, stage lights, node appear, score fill, drill unlock) |
| `src/app/globals.css` | Add `bg-grid` at lower opacity; no other changes |

No sections added or removed in Stage 2.

### Stage 3 — Homepage storytelling

| File | Change |
|------|--------|
| `src/app/page.tsx` | Remove PipelineShowcase/Capture section; remove standalone Flow, Improve sections; remove TrustGrid section; remove SupportedTodayGrid section; add interactive workflow section; add debate-proof section; update anchors |
| `src/components/marketing/WorkflowRail.tsx` | Replace numbered list with interactive tabbed workflow (four steps, product UI previews) |
| `src/components/marketing/MarketingFooter.tsx` | Update anchor links to match new section IDs |
| `src/lib/marketing.ts` | Update `HOME_ANCHORS` and `MARKETING_NAV_LINKS` to match new sections |
| `src/components/marketing/DebateProofSection.tsx` | **NEW** — "See what the judge heard" one coherent example |
| `src/__tests__/marketing.test.ts` | Update anchor expectations |

No files removed — only `PipelineShowcase` will stop being used on the homepage (the component stays for the demo page).

### Stage 4 — Application polish

| File | Change |
|------|--------|
| `src/app/dashboard/page.tsx` | Refine new-user / returning-user state rendering |
| `src/app/progress/page.tsx` | Improve loading/empty/error state components |
| `src/app/learn/page.tsx` | Already improved (API error handling); visual refinement if needed |
| Typography fixes across evidence components | `text-[N]px` → `text-eyebrow` / `text-xs` / `text-sm` |

---

## 12. Dependencies

No new packages are planned for Stages 1–3.

`motion/react` already handles all animation requirements for the HeroDebateConsole sequence.  
`TabsRoot/TabsList/TabsTrigger/TabsContent` from `src/components/ui/tabs.tsx` handles the workflow section interaction.  
No new icon sets, no new animation libraries, no new design systems.

If Stage 4 evidence typography fixes reveal a pattern that needs a utility, add to `globals.css` only.

---

## 13. Stage 3 Research: Product Storytelling Reference Pass

> **Date:** 2026-06-20  
> **Purpose:** Before implementing the Stage 3 interactive speech-to-flow section, five crafted product sites were studied to extract principles — and to explicitly record what was rejected so the result remains uniquely RoundLab.

### References reviewed

| Site | Observed pattern |
|------|-----------------|
| **Linear** (linear.app) | Shows actual product UI (issue lists, Gantt timelines, code diffs) as the marketing material. Each scroll section reveals a different product state in a progression: Intake → Plan → Build → Monitor. No abstract illustrations. |
| **Stripe** (stripe.com) | Outcome-focused metrics rather than raw UI. Progressive disclosure: broad value proposition → specific capabilities. Testimonials interrupt technical sections to humanize. Modular card-based layouts for capabilities. |
| **Vercel** (vercel.com) | Three-act structure targeting different user personas — technical specificity for developers, social proof and outcome language for stakeholders. Copy deliberately bifurcates within the same scroll. |
| **Raycast** (raycast.com) | Embeds the actual product keyboard UI as the hero. Real extension cards, real product states. Keyboard motif (⌘K, shortcuts) runs as a consistent visual grammar throughout the entire page. |
| **Resend** (resend.com) | Developer-first: documentation and code snippets as marketing. No interactive demos. Transparency about the stack. Vocabulary is unapologetically technical. |

### Principles adopted

**P1 — Real UI, not illustrations (from Linear + Raycast)**  
Every section must show actual debate artifacts: a real argument chain, a real ballot excerpt, a real flow annotation. No generic graphs, no abstract category illustrations. The product is the intelligence itself.

**P2 — One continuous example (from Linear)**  
Linear progresses Intake → Plan → Build → Monitor using the same project. RoundLab's Stage 3 homepage uses the same C1 speech example across every demonstration section: transcript → extracted flow → judge reading → drill. Seeing the same argument transform across multiple analyses is the product story.

**P3 — Technical vocabulary as signal, not barrier (from Resend + Raycast)**  
Resend doesn't simplify "DKIM" or "SPF" for non-developers. Raycast doesn't explain what ⌘K is. RoundLab should not apologize for "warrant," "weighing," "dropped argument." These terms are features. Debaters will recognize them; coaches will trust them; parents will learn them by seeing them used confidently.

**P4 — Complexity revealed by interaction, not hidden from it (from Linear + Raycast)**  
Static state must be complete and fully readable. Interaction reveals additional depth — a phrase lights up its corresponding flow node, not replaces it. Nothing is locked behind a click.

**P5 — Consistent visual grammar (from Raycast)**  
Raycast's keyboard motif appears in every section. RoundLab's visual grammar is the argument chain: [CLAIM] → [WARRANT] → [EVIDENCE] → [IMPACT] with status indicators (strong/weak/missing). This exact chip pattern anchors the hero console, the flow section, and the diagnostic board — never redesigned, only zoomed in.

### Ideas explicitly rejected

**Outcome abstraction without UI (Stripe model)**  
Stripe hides the API response behind a metric card. RoundLab must not do this — the flow chart, the ballot text, the argument chain ARE the value. Hiding them behind "78/100" alone would lose the entire product claim.

**Scroll-jacking or reveal-on-scroll animations**  
Several sites use aggressive scroll capture. Rejected: violates the "no scroll hijacking" constraint, breaks screen readers, and obscures content from users who need it immediately.

**Multiple accent colors for visual differentiation**  
Stripe uses purple/green/blue across sections to create visual rhythm. Rejected: RoundLab's color system maps colors to MEANING (ok/warn/danger = live/contested/dropped). Using color for decoration would break that semantic contract.

**Generic carousel / "how it works" slide deck**  
Common pattern across SaaS marketing. Rejected: it flattens an interesting problem (structured debate analysis) into a flat list. RoundLab's product is about the relationships between parts of an argument — the UI must show those relationships.

**Product tour overlay with guided steps**  
Linear avoids this; Raycast avoids this. Their UIs speak for themselves. A walkthrough overlay would signal that the product needs explanation rather than demonstrating self-evident value.

### How the result remains uniquely RoundLab

The Phase A interactive transcript section is built around something no general productivity tool could replicate: **the internal structure of a Public Forum argument**. The claim/warrant/evidence/impact chain is not a generic workflow step — it's the specific analytical grammar of competitive debate. The issue detection (missing weighing, weak warrant) uses actual flow judge notation. The opponent response branch shows cross-case analysis, not just a single argument in isolation.

Visually: the connecting lines between flow nodes follow PF flow sheet geometry (vertical chain, opponent response as indented secondary block), not a generic graph or tree diagram. The chip style ([CLAIM badge] · [status dot] · excerpt) is the same pattern used in HeroDebateConsole, providing internal brand coherence.

The section can only exist for a debate coaching product. That is the test.

---

---

## 14. Phase B Design Decisions — Judge-Lens Simulator

**Research note:** Inspected Vercel's persona-bifurcated content (developer vs. stakeholder view), Linear's workflow-step tabs (each tab shows a genuinely different product state), and Raycast's keyboard-shortcut segmented selector. Key takeaway: differentiation must be in content and information architecture, not color or label swaps.

**Placement:** `JudgeLensSection` replaces `JudgeLensComparison` and is inserted directly after `SpeechFlowSection` in page.tsx — not at its former `#judge` position — so the C1 narrative flows continuously (structured → evaluated). The old static 4-card grid is retired; the interactive 3-judge simulator takes the `id="judge"` anchor.

**ARIA pattern:** Manual roving tabindex (not Radix) for full control over simultaneous left-panel and ballot-panel fade transitions. All three tabpanels are in the DOM (correct ARIA) but only active one holds content (performance). Ballot panel (right) updates by React state; `role="status"` outside the animated `motion.div` announces the judge change to screen readers.

**Transition:** `key={activeJudge}` on inner `motion.div` wrappers with `initial={{ opacity: 0 }}` when animated. Reduced-motion: same `key` change triggers instant remount at full opacity (no `initial` injected).

**Score semantics:** 62/51/44 for Flow/Lay/Parent. Colors: `warn` ≥50, `danger` <50. These are ILLUSTRATIVE scores demonstrating the same technical gap lands differently depending on judge type — not absolute quality ratings.

**Content constraint:** All three judges share one decisive weakness (missing weighing). The differences are in WHAT THEY NOTICE about it and HOW THEY EXPRESS the gap. Flow judges see a technical drop; lay judges see an unexplained comparison; parent judges see a confidence deficit. Each correction is judge-mode-specific.

---

## 15. Phase C Design Decisions — Debate Proof Section

**Scope:** Single new section `DebateProofSection` at anchor `#product-proof`, placed after `JudgeLensSection`. Continues the C1 Economic Burden Shift narrative from Phases A and B. The section tells the full coaching story: gap detected → drill prescribed → speech improved.

**Three sub-sections:**
1. **Decisive Moment** (01) — Mini flow-sheet showing C1 chain status (Claim/Evidence/Warrant/Impact all present, Weighing = missing). Ballot excerpt confirms the technical drop. This is NOT decorative; it mirrors the actual flow judge notation the app produces.
2. **Drill Bridge** (02) — The specific drill generated from the gap. Exact prompt text, drill type badge, expected outcome. Shows that the app prescribes specific practice, not generic tips.
3. **Before/After Transformation** (03) — Two speech excerpts: original (no weighing) vs re-record (explicit timeframe comparison). Added behavior chips: Weighing, Timeframe comparison, Causal link.

**Layout:** `grid-cols-1 lg:grid-cols-3` — three equal columns at desktop, stacked on mobile. Columns connected by step numbers (01/02/03) rather than arrows, which are fragile at narrow widths. Each column is a self-contained card.

**Narrative continuity:** The flow node data echoes the exact same status values as SpeechFlowSection (Warrant = weak, Weighing = missing). The drill prompt names the same "$8K vs $21K" figures the judge lens ballots reference. This gives the visitor the sense that the same argument has been tracked across three consecutive analytical lenses.

**Data exports:** `DECISIVE_MOMENT_NODES`, `DRILL_CARD_DATA`, `BEFORE_SPEECH`, `AFTER_SPEECH` — all exported for unit testing (no DOM required).

**Reduced-motion:** Entrance animations gated by `isMounted && prefersReducedMotion === false`. Static render includes all content at full opacity.

**No new dependencies.** No interaction state (fully static — this is a coaching story display, not a simulator like Phases A/B).

---

## 16. Phase C Refinement — DebateProofSection Polish

**Scope:** Refinements to `DebateProofSection.tsx` only. Five targeted improvements:

1. **Causal connectors at xl+:** Grid changed from `lg:grid-cols-3` to `xl:grid-cols-[1fr_60px_1fr_60px_1fr]`. Two inline connector elements sit in the 60px columns — connector 01→02 shows "✗ WEIGHING / detected" in warn color + ChevronRight; connector 02→03 shows "drill / complete" + ChevronRight. Connectors are `hidden xl:flex` — invisible at and below 1024px, avoiding the cramped three-column state.

2. **Card 01 density reduction:** "Strong" nodes (CLAIM, EVIDENCE, IMPACT) now render as compact rows showing only `role · strong` — no excerpt paragraph. "Weak" (WARRANT) and "missing" (WEIGHING) nodes retain annotated notes. The WEIGHING missing state is now the dominant visual focus in card 01.

3. **Gap-trigger bridge in card 02:** A warn-colored callout (`WEIGHING · missing · prescribed from C1`) with `data-testid="gap-trigger"` sits above the drill prompt, explicitly connecting the diagnosis in card 01 to the prescription in card 02.

4. **Before/after contrast in card 03:** Before lane changed to recessive (bg-surface-2/60, text-ink-faint italic, no border). After lane gains `border-l-2 border-lav` left accent. Labels changed from "ORIGINAL/RE-RECORD" to "BEFORE DRILL/AFTER DRILL". `BEFORE_SPEECH.label` data constant updated accordingly.

5. **Section subtext reduced:** One line: "Same speech. One diagnosed gap. One drill. A stronger next round."

**Playwright test updated:** "before lane shows 'ORIGINAL' label" → "before lane shows 'BEFORE DRILL' eyebrow" (label data and display changed together).

---

## 17. Phase D Design Decisions — Homepage Finalization

**Scope:** Audit, consolidation, and completion of the full homepage.

### Redundancy removals

| Removed section | Anchor | Reason |
|----------------|--------|--------|
| "The practice loop" (WorkflowRail) | (unanchored) | Static 5-step description now fully demonstrated interactively by A/B/C sections combined |
| Capture / PipelineShowcase | `#practice` | Replaced by IntelligenceLayerSection which explains the underlying system rather than re-animating the user experience already shown in A/B/C |
| Flow diagnostic board (ArgumentHealthMatrix) | `#flow` | C1 chain health is shown deeply and interactively in SpeechFlowSection; macro grid adds marginally more at significant redundancy cost |
| Improvement lanes (ImprovementLanes) | `#improve` | Direct duplicate of DebateProofSection card 03 (TransformationCard). Phase C version is superior because it shows causation (gap → drill → outcome), not just a side-by-side |

### IntelligenceLayerSection (`#how-it-works`)

Six-stage pipeline walkthrough using a vertical timeline layout (number badge + thin connecting line + label + one-sentence body).

Stages: Speech capture → Argument segmentation → Argument graph → Judge-conditioned evaluation → Targeted drill generation → Progress model.

Design decisions:
- Two-column at `lg+`: heading block (sticky) left, pipeline stages right. Single column on mobile.
- Each stage: number badge (01–06 in lav), section-stamp label, one sentence body.
- Connecting line: thin `w-px bg-hairline` between stages within the right column.
- Heading cross-references: "The same C1 Economic Burden Shift argument seen throughout this page runs through every stage below."
- NO fake architecture diagrams, NO generic AI terminology ("neural network", "embedding", "model weights").
- `PIPELINE_STAGES` data array exported for unit testing.
- Reduced-motion: fully static at all times; no perpetual animation.

### Final CTA redesign

Old CTA: Mic icon in lav gradient circle, "Start your first practice rep" headline, body copy, "No credit card required" note.

New CTA: Restrained `<section>` with `max-w-2xl` centered text. Headline: "Your next speech should know what the last one missed." Two CTAs: primary "Start practicing" → `/login`, secondary "See a sample report" → `/demo`. One-line footer: "Free to start · No coach required". No icon, no gradient box, no repeated product summary.

### Section heading approach

Sections in page.tsx now use inline `motion.div` blocks with `section-stamp` + `h2` + `p` instead of the `<SectionHead>` reusable component. This eliminates the intermediate abstraction (one-off component that added no meaningful API) and allows per-section customization without prop sprawl.

### nav + footer link updates

- `MARKETING_NAV_LINKS`: "Practice" → `#speech-to-flow`, "Flow & ballot" → "How it works" at `#how-it-works`. Anchors `#flow`, `#improve`, `#practice` removed.
- `MARKETING_FOOTER`: Product group updated to reflect new anchors (`#speech-to-flow`, `#judge`, `#how-it-works`, `#evidence`, `#team`).
- `HOME_ANCHORS` in `marketing.ts`: removed `#practice`, `#flow`, `#improve`; added `#how-it-works`.

### Final homepage narrative sequence

1. Hero — what RoundLab is
2. Proof rail — grounding proof points
3. SpeechFlowSection — how it understands a speech
4. JudgeLensSection — how judges interpret it
5. DebateProofSection — where the ballot was lost and how the student improves
6. IntelligenceLayerSection — how the system works under the hood
7. Evidence — evidence workflow capability
8. Team — coach workflow capability
9. Trust — why to trust it
10. Supported today — what's live
11. Final CTA — what to do next

*Phase D implementation complete. 1452 Jest · 354 Playwright (118 unique) · TypeScript clean · Build green.*

---

## §18 — Surgical Cleanup Pass (post Phase D)

**Date:** 2026-06-21 · **Branch:** `ui/homepage-transformation`

### Changes

**PipelineShowcase restored** (`#practice`): The animated `Audio → Transcript → Flow → Ballot → Drill` section was removed in Phase D in favor of IntelligenceLayerSection. This was reversed because PipelineShowcase is the stronger product moment — it's interactive, user-visible, and visually distinctive. IntelligenceLayerSection covered the same pipeline at a slightly different level of abstraction but added page weight without adding clarity.

**IntelligenceLayerSection removed** (`#how-it-works`): Superseded by PipelineShowcase. The overlap was high enough (both walked through the same 5–6 analysis stages) that keeping both would dilute both. PipelineShowcase shows the UX; the deep-dive sections (A/B/C) demonstrate individual capabilities. Technical-depth readers are served by the architecture docs.

**SupportedToday removed** (`#supported`): The live capability grid was informative but arrived too late in the scroll to change a visitor's decision. The trust section and CTA reach visitors at lower attention-cost.

**Trust section expanded to 6**: Added "Every judgment is inspectable" — explains that RoundLab shows its inference provenance and uncertainty, making feedback reviewable. Implemented with `Eye` icon from existing lucide-react import.

**SpeechFlowSection balance**: Removed `items-start` from the two-panel grid (panels now stretch to equal height), widened the right column (`352px → 388px` at `lg`, `368px → 408px` at `xl`), gave the nodes list `flex-1` to fill the panel, tightened transcript line-height (`leading-[1.9] → leading-[1.75]`), equalized padding in the flow panel (`px-4 py-3 → px-5 py-4`).

**DebateProofSection composition**: Card 01 — added `mt-auto border-t border-hairline/50 pt-3` wrapper on the ballot note so the separator is explicit rather than just dead space. Card 02 — added `border-t border-lav/20 pt-3` wrapper grouping drill type + prompt + outcome under a lav separator, cleanly separating the diagnosis trigger from the drill content. Card 03 — added `border border-hairline` to the Before lane for a contained artifact feel.

### Final homepage sequence (post-cleanup)

1. Hero
2. Proof rail
3. PipelineShowcase (`#practice`) — fast animated overview of the full loop
4. SpeechFlowSection (`#speech-to-flow`) — interactive transcript ↔ flow annotation
5. JudgeLensSection (`#judge`) — three-judge ARIA tab simulator
6. DebateProofSection (`#product-proof`) — decisive moment → drill → transformation
7. Evidence (`#evidence`) — provenance strip
8. Team (`#team`) — coach workflow strip
9. Trust (`#trust`) — 6-point trust grid
10. Final CTA

### Test counts

- Jest: **1442** (−16 IntelligenceLayer unit tests, +8 marketing invariants, net −8 from Phase D's 1452; IntelligenceLayer component/e2e deleted as unused)
- Playwright: **351** executions (15 new homepage tests ×3 projects, −20 intelligenceLayer tests ×3 projects)
- TypeScript: clean · Build: green
