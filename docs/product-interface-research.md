# RoundLab Product Interface Research

_Patterns studied during the homepage transformation (Phase 2). Each entry records the
source, its original use, the RoundLab adaptation, why it helps the debate workflow, and
what was intentionally **not** copied._

> Method note: this round focused on patterns directly applicable to a public product
> homepage and marketing navigation. Deeper application/workspace patterns (command menu,
> split-pane research, transcript editing) are tracked for later phases.

## 1. Progressive disclosure over feature lists (Stripe, Linear marketing)

- **Source / original use:** Stripe and Linear marketing pages reveal one capability per
  scroll "act," each with a distinct layout and a concrete artifact, instead of a uniform
  feature grid.
- **RoundLab adaptation:** Homepage is re-sequenced into acts that each expose a *different*
  product surface — capture, flow diagnostic, judge lens, improvement loop, evidence
  provenance, coach workflow. No artifact repeats across acts.
- **Why it helps:** A debater scanning the page learns the full practice loop without seeing
  the same ballot four times; each act answers "what else can this do?"
- **Not copied:** Stripe's gradient-heavy hero treatment and dense logo walls. We keep one
  restrained accent and use real facts, not borrowed brand logos we don't have.

## 2. Provenance / source-card traceability (Perplexity, Zotero)

- **Source / original use:** Perplexity shows answer → numbered source cards; Zotero preserves
  exact source metadata separate from user notes.
- **RoundLab adaptation:** The Evidence section renders a left-to-right **provenance trail**
  — `Claim → Source (publisher/date) → Exact quote → AI tag → Citation → Saved card` — with
  the exact quote visually marked as untouched source text and the tag marked as AI-proposed.
- **Why it helps:** RoundLab's core trust claim is "we never rewrite the source." Making the
  provenance chain literal on the homepage proves it before signup.
- **Not copied:** Perplexity's chat framing. Evidence here is a research artifact, not a
  conversation.

## 3. Before/after deliberate-practice framing (Strava, TrainingPeaks, Duolingo)

- **Source / original use:** Athletic/learning tools show a baseline, an intervention, and a
  measurable change rather than a single vanity number.
- **RoundLab adaptation:** The Improvement section uses **two parallel lanes** (Original vs
  Re-record) and annotates exactly what was *added* (warrant, weighing, extension) — not just
  a higher score.
- **Why it helps:** Reinforces "coaching, not cheating": improvement is shown as new debate
  behavior, matching the product principle in `CLAUDE.md`.
- **Not copied:** Streak pressure and XP economies. We avoid game-y rewards (also removed the
  hero's "+50 XP" chip).

## 4. Coaching dashboards / review queues (Khan Academy coach view)

- **Source / original use:** Teacher dashboards summarize "who needs attention" and route to a
  per-student action.
- **RoundLab adaptation:** The Team section shows a compact coach workflow strip
  (`Assign → Students complete → Review queue → Skill gap → Assign drill`) so schools can see
  the value before creating a team.
- **Why it helps:** The buyer (coach/program) is different from the daily user (student); the
  homepage must speak to both.
- **Not copied:** Heavyweight LMS gradebooks. We show the loop, not a spreadsheet.

## 5. Accessible mobile navigation (Radix Dialog / shadcn sheet)

- **Source / original use:** Radix Dialog primitive (focus trap, ESC, `aria` wiring) behind a
  shadcn-style sheet.
- **RoundLab adaptation:** Reused the repo's existing `components/ui/sheet.tsx` (Radix Dialog)
  for a mobile marketing menu, preserving the primary CTA and exposing section anchors.
- **Why it helps:** Fixes the real bug that logged-out phone users had no navigation.
- **Not copied:** A second nav library — we reused the in-repo primitive (no new dependency).

## 6. Truthful "what's supported today" over roadmap (changelog-driven marketing)

- **Source / original use:** Linear/Vercel changelog-style honesty — show what shipped, link to
  it, keep "next" small and credible.
- **RoundLab adaptation:** Replaced the stale `#roadmap` ("coming soon" for already-shipped
  features) with a **Supported today** grid listing live capabilities, plus a small honest
  "in progress" line. Enforced by a unit test that fails on roadmap/"coming soon" language.
- **Why it helps:** Trust. Claiming shipped features are "coming" undersells the product and
  reads as a template.
- **Not copied:** Invented metrics / fake social proof. The proof strip uses only defensible
  product facts (scoring dimensions, speech types, drills/session, analysis time).

## Carry-forward for later phases

- Linear command menu + contextual actions → Phase 3/6 (the repo already has `CommandMenu`).
- Descript transcript-first editing → Phase 3 report transcript mode.
- Figma anchored comments / version history → Phase 4 coach comments.
- Perplexity/Readwise/split-pane document triage → Phase 5 Evidence research cockpit.
