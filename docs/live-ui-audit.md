# RoundLab Live UI Audit

_Last updated: 2026-06-17 — audit scope for the anti–vibe-coded product transformation._

## How this audit was produced

This audit is **code-grounded**. No browser-automation tooling (Playwright/Puppeteer
or a browser MCP) is available in this environment, and the deployed app at
`https://round-lab.vercel.app/` is client-rendered, so `WebFetch` cannot capture
meaningful rendered screenshots. Findings below are derived from reading the actual
route components in `frontend/src/app/**` and shared components in
`frontend/src/components/**`, cross-referenced against the live product behavior they
produce.

**Known limitation:** `artifacts/ui-before/` and `artifacts/ui-after/` screenshot sets
could not be captured automatically. If/when a browser tool is available, this audit
should be re-run with screenshots attached. Section findings are written to be verifiable
by opening each route.

## Routes inspected (from `frontend/src/app`)

| Route | File | Primary user task |
| --- | --- | --- |
| `/` | `app/page.tsx` | Understand the product, start practicing |
| `/login` | `app/login/page.tsx` | Authenticate |
| `/dashboard` | `app/dashboard/page.tsx` | Decide what to practice next |
| `/session` | `app/session/page.tsx` | Set up + capture a speech |
| `/speech/[id]` | `app/speech/[id]/page.tsx` | Read the report (6 modes) |
| `/drills/[id]` | `app/drills/[id]/page.tsx` | Run a drill |
| `/team` | `app/team/page.tsx` | Coach/team workflows |
| `/evidence` | `app/evidence/page.tsx` | Research + cut cards |
| `/learn` | `app/learn/page.tsx` | Drills + skill guides |
| `/demo` | `app/demo/page.tsx` | Explore a sample report |
| `/pilot` | `app/pilot/page.tsx` | Pilot checklist + feedback |
| `/share/[token]` | `app/share/[token]/page.tsx` | View a shared report |
| `/evals` | `app/evals/page.tsx` | Internal eval results |

This pass (Phase 2) transforms `/` (public homepage + marketing nav/footer). The
remaining routes are audited here to seed later phases.

---

## `/` — Public homepage (PRIMARY FOCUS OF THIS PASS)

**Current structure** (`app/page.tsx`, 827 lines, single client component):
`MarketingNav → Hero (HeroDebateConsole) → Metrics strip → "Watch a speech become a flow"
(PipelineShowcase) → "Built like a coach" (ArgumentHealthMatrix + JudgeLensComparison) →
"How it works" (4 step cards) → "Features" (bento) → "Drills" (3 cards) → "Roadmap" → CTA → Footer`.

### Findings

- **Repeated sample experience (spec §2.1).** One canonical sample —
  _"1AC · State Championship R4", score 78/100, Clash 14/20, Weighing 9/20, Coverage 16/20,
  "No weighing detected — C1", "Weighing Sprint" drill_ — is re-rendered in the hero console,
  the "How it works" step cards (weak-evidence-on-C1 chain, weighing/clash bars, Weighing
  Comparison Sprint), and the Features bento (identical 78/100 ballot bars + claim/warrant
  chain). The page is long but reveals the same artifact 3–4 times.
- **Stale roadmap (spec §2.3, completion gate).** The `#roadmap` section lists
  _"Drill attempt recording, Progress tracking over time, Team dashboard, Evidence upload & RAG"_
  as **Next / coming**, but all four already ship (delivery metrics, progress, `/team`,
  Evidence Studio). This misrepresents the product as less capable than it is.
- **No mobile navigation for logged-out users.** `MarketingNav`'s link cluster is
  `hidden … sm:flex`, with no hamburger/sheet fallback. On phones the only actions are theme
  toggle + "Get started". Section anchors are unreachable.
- **Equal visual weight (spec §2.2).** Most sections are the same `max-w-4xl/6xl` padded
  card grid on alternating `surface-1` backgrounds. Rhythm comes only from background flips,
  not from density/scale/layout changes.
- **Thin product proof (spec §2.4).** The page asserts capabilities ("judge-style", "PF-native")
  but never shows the improvement loop, evidence provenance, or a coach workflow — the three
  things that distinguish RoundLab from a generic LLM.
- **Anti-vibe signals present:** decorative mini-waveform built from a hardcoded bar array
  (fake telemetry), an XP chip ("Start drill → 50 XP") in the hero console, and a feature
  bento with interchangeable mini-visuals.
- **Footer is a dead end.** Logo + one tagline; no navigation, no students/coaches split,
  no help/pilot links.

### Action (this pass)

Rebuild into progressive disclosure where **every section reveals a different capability**:
Hero (full promise) → Proof strip (real facts) → Practice (capture+analysis) → Flow
(diagnostic board) → Judge lens (interactive) → Improvement (before/after re-record) →
Evidence (provenance trail) → Team (coach workflow) → Trust → **Supported today** (replaces
roadmap, truthful) → Convert → real Footer. Add an accessible mobile nav sheet. Eliminate the
duplicate 78/100 sample outside the hero; give each new section a distinct topic.

---

## `/login`

- Clean but generic. Primary task (auth) is clear. Carries less of the new visual language —
  candidate for a later auth pass (split-pane with a product-proof panel).

## `/dashboard`

- Recently upgraded (NextActionPanel, CoachingFocusCard, RecentActivity, QuickStartRow). Strong
  direction; Phase 3 target for the intelligent priority-action + readiness view.

## `/session`

- `SpeechCaptureWorkspace` with debate-native setup + honest save-state already landed. Phase 3
  focus-mode practice room + full recorder state matrix remain.

## `/speech/[id]`

- Six-section report nav already exists (`SpeechReportNav`). Phase 3: flow canvas depth, ballot
  decision/coach split, transcript-first review.

## `/evidence`

- Most mature surface (Evidence Studio modal, provenance panels). Phase 5: three-state research
  cockpit + claim-decomposition map + provenance graph.

## `/team`, `/drills/[id]`, `/learn`, `/demo`, `/pilot`

- Functional; consistent with AppShell. Later-phase polish (coach review queue, drill room +
  ghost comparison, contextual help).

---

## Cross-cutting findings

- **Authorship distinction is inconsistent on marketing.** Source-authored vs AI-generated text
  is well separated inside Evidence Studio but not surfaced on the homepage as a trust story.
- **Responsive:** the app shell handles authed routes well; the **public** homepage is the main
  responsive gap (no mobile nav).
- **Accessibility:** decorative visuals are mostly `aria-hidden`; section headings exist. The new
  homepage keeps semantic `<section>` + `<h2>` landmarks, labels the nav, and routes all motion
  through the global `prefers-reduced-motion` kill-switch in `globals.css`.

## Before-screenshot index

Not captured — see "How this audit was produced". Re-run with a browser tool to populate
`artifacts/ui-before/`.
