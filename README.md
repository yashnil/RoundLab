# RoundLab

**AI-powered speech and debate training for Public Forum debaters.**

RoundLab is a full-stack practice platform that turns recorded speeches into argument flows, judge-style ballots, targeted drills, and longitudinal skill improvement. It closes the coaching gap for students who practice without consistent access to a coach.

**Status:** Active development · Pilot-ready core features · Pre-public launch

**Primary users:** Novice and JV Public Forum debaters; debate coaches and program coordinators

---

## Table of Contents

1. [Product Overview](#product-overview)
2. [Core Features](#core-features)
3. [Homepage Product Story](#homepage-product-story)
4. [Architecture](#architecture)
5. [Repository Structure](#repository-structure)
6. [Local Development Setup](#local-development-setup)
7. [Environment Variables](#environment-variables)
8. [Database and Migrations](#database-and-migrations)
9. [Testing](#testing)
10. [Accessibility and Responsive Design](#accessibility-and-responsive-design)
11. [Design System](#design-system)
12. [Deployment](#deployment)
13. [Development Workflow](#development-workflow)
14. [Current Status](#current-status)
15. [Roadmap](#roadmap)
16. [Contributing](#contributing)
17. [Security and Privacy](#security-and-privacy)
18. [License](#license)

---

## Product Overview

### The problem

Most Public Forum debaters practice without a coach in the room. They record rounds, re-watch them without structured feedback, and improve slowly — or not at all. Generic AI writing tools produce case text but do not diagnose what went wrong in a live speech.

### RoundLab's coaching loop

```
Record or upload a speech
  → Transcribe
  → Segment into argument moves (claim · warrant · evidence · impact · response)
  → Reconstruct argument graph (what's contested, extended, dropped, conceded)
  → Evaluate through judge-specific lenses (flow / lay / parent priorities)
  → Identify the decisive weakness
  → Prescribe targeted drill
  → Student re-records
  → Track improvement across sessions
```

### Why it's different

- **Debate-native, not generic.** The system understands Public Forum structure: contentions, crossfire, weighing, extensions, drops. Feedback is expressed in debate language, not SAT-prep language.
- **Coaching, not cheating.** RoundLab grades and drills your own speeches. It does not write your case or cut your cards. Evidence is never rewritten.
- **Judge-conditioned evaluation.** The same speech is scored through multiple judge priority frameworks simultaneously — not just a single algorithmic score.
- **Causal improvement tracking.** Progress is shown as a change in specific debate behavior (warrant named, weighing added, extension strengthened), not just a higher number.

---

## Core Features

### Implemented

| Feature | Description |
|---------|-------------|
| Speech recording and upload | Record via browser mic, upload audio file, or paste a transcript |
| Transcription | Whisper-based transcription with speaker-turn segmentation |
| Argument flow extraction | Claim · warrant · evidence · impact structure per contention |
| Argument graph | Which arguments are contested, extended, dropped, or conceded |
| Judge-style ballot | Five scoring dimensions with contention-level feedback |
| Multiple judge lenses | Evaluate the same speech through flow, lay, and parent judge priorities |
| Targeted drills | Three drills per speech, each targeting the specific diagnosed weakness |
| Speech reports | Full report: flow, ballot, skills breakdown, transcript, drills |
| Re-record comparison | Side-by-side before/after showing added debate behaviors |
| Progress tracking | Skill trends across sessions; per-dimension improvement charts |
| Delivery analysis | WPM, pacing timeline, filler word detection, delivery score |
| Tournament workout mode | Pre-round targeted practice sequences |
| Blockfile/frontline trainer | Coverage check against stored block entries |
| Evidence Studio | Research sources, cut read-aloud cards, preserve exact source quotes |
| Source credibility | Extraction, citation metadata, MLA formatting |
| Team and coach tools | Assignments, submission review queue, team overview |
| Async analysis jobs | Background pipeline with polling and recovery UI |
| Google authentication | Via Supabase Auth |
| Interactive demo page | Full sample speech report at `/demo` |
| Pilot program tools | Pilot checklist, confusion reports, drill ratings |
| Shareable coach reports | Coach-annotated reports with share link |

### Experimental

| Feature | Status |
|---------|--------|
| LLM evidence refiner | Optional; disabled in tests; controlled by `research_enable_llm_refiner` config |
| Semantic reranking | CrossEncoder seam wired but guarded; uses BM25 by default |
| Axe-core accessibility audit | Playwright-integrated; catching violations as they surface |

### Planned (not yet implemented)

- Full-round mode (1AC through Final Focus in sequence)
- Expanded judge adaptation depth (more judge profiles)
- Evidence-link ingestion from user-provided URLs at research time
- Scheduling and practice reminders
- Public speaking support beyond PF

---

## Homepage Product Story

The public homepage (`/`) demonstrates RoundLab's coaching loop through a single continuous debate example: **C1 Economic Burden Shift** (refugee resettlement, fiscal burden, weighing gap). Each section uses this same argument so visitors experience the full causal chain.

### Interactive sections (in order)

| Section | Anchor | What it demonstrates |
|---------|--------|---------------------|
| Hero | — | Three-line headline with interactive HeroDebateConsole showing live analysis output |
| Pipeline showcase | `#practice` | Animated `Audio → Transcript → Flow → Ballot → Drill` fast-loop overview; starts on in-view |
| Speech-to-flow | `#speech-to-flow` | Bidirectional transcript ↔ flow-node highlighting; coaching gap callout; interactive phrase annotation |
| Judge lens | `#judge` | Three-judge ARIA tab simulator (Flow / Lay / Parent); roving tabIndex keyboard nav; ballot artifact with decisive issue, ballot note, and correction |
| Coaching story | `#product-proof` | Decisive moment card (C1 chain status) → drill bridge (gap-trigger, drill prompt) → transformation card (before/after re-record with causal connectors) |
| Evidence | `#evidence` | Evidence Studio provenance strip |
| For coaches | `#team` | Team workflow strip |
| Trust | `#trust` | Six trust principles (incl. inspectability) |

The homepage does not scroll-hijack, uses no perpetual animations, and remains fully navigable without JavaScript completing.

---

## Architecture

```text
Browser
  ↓
Next.js frontend (Vercel)
  ↓
FastAPI backend (Render / Railway)
  ├── Supabase Auth (Google OAuth, JWT verification)
  ├── Supabase Postgres (user data, speeches, reports, teams)
  ├── Supabase Storage (audio files)
  ├── Whisper API (transcription)
  ├── OpenAI API (argument analysis, judge evaluation, drill generation)
  ├── Evidence pipeline
  │     ├── Trafilatura / BeautifulSoup (web extraction)
  │     ├── BM25 + optional CrossEncoder (candidate ranking)
  │     └── pysbd (sentence segmentation)
  └── LangGraph (pipeline orchestration — AI analysis flow)
```

### Frontend

- **Framework:** Next.js 15+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS with custom design tokens (see `frontend/src/app/globals.css`)
- **Components:** shadcn/ui primitives + hand-authored components
- **Animation:** motion/react (framer-motion v11+) with `reducedSafe()` wrapper
- **Auth client:** `@supabase/supabase-js`
- **State:** React state + `useSyncExternalStore` for theme; no global state library

### Backend

- **Framework:** FastAPI 0.136+
- **Language:** Python 3.11+
- **AI orchestration:** LangGraph (argument analysis pipeline)
- **LLM provider:** OpenAI (GPT-4 class models; structured outputs via Pydantic)
- **Transcription:** Whisper API
- **Text extraction:** trafilatura, beautifulsoup4, pysbd, rank-bm25
- **Database client:** Supabase Python client (service-role for RLS bypass in server context)

### Infrastructure

- **Auth/DB/Storage:** Supabase (Postgres with Row Level Security)
- **Frontend hosting:** Vercel (root directory: `frontend/`)
- **Backend hosting:** Render or Railway (root directory: `backend/`, start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`)

---

## Repository Structure

```text
RoundLab/
├── frontend/                   Next.js frontend
│   ├── src/
│   │   ├── app/                App Router pages and layouts
│   │   │   ├── page.tsx        Public homepage
│   │   │   ├── dashboard/      Student dashboard
│   │   │   ├── session/        Speech recording/upload
│   │   │   ├── speech/         Speech report view
│   │   │   ├── evidence/       Evidence Studio
│   │   │   ├── team/           Coach and team pages
│   │   │   └── demo/           Interactive demo report
│   │   ├── components/
│   │   │   ├── marketing/      Homepage section components
│   │   │   ├── shell/          AppShell, sidebar, mobile nav
│   │   │   ├── ui/             Primitives (button, dialog, tabs, etc.)
│   │   │   ├── evidence/       Evidence Studio sub-components
│   │   │   └── speech/         Speech report sub-components
│   │   ├── lib/                Utilities, supabase client, motion helpers
│   │   └── hooks/              Custom React hooks
│   ├── src/__tests__/          Jest unit tests
│   ├── e2e/                    Playwright end-to-end tests
│   └── public/                 Static assets, PWA manifest
│
├── backend/                    FastAPI backend
│   ├── app/
│   │   ├── main.py             FastAPI app entry point, router registration
│   │   ├── config.py           Pydantic settings (env var loading)
│   │   ├── api/                Route handlers (one file per resource)
│   │   ├── models/             Pydantic request/response models
│   │   ├── pipeline/           AI analysis pipeline modules
│   │   └── services/           Business logic (delivery analysis, drill gen, etc.)
│   └── tests/                  pytest backend tests
│
├── supabase/
│   └── migrations/             SQL migration files (timestamped, applied in order)
│
├── docs/                       Design docs, rubrics, planning docs
│   ├── ROUNDLAB_DESIGN_DIRECTION.md
│   ├── VISUAL_REVIEW_CHECKLIST.md
│   ├── ai-pipeline.md
│   ├── debate-rubric.md
│   ├── product-requirements.md
│   └── project-plan.md
│
├── DESIGN.md                   Design system reference for contributors
├── DEPLOYMENT.md               Full deployment checklist and env var reference
└── README.md                   This file
```

---

## Local Development Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- A Supabase project (free tier is sufficient for development)
- OpenAI API key

### 1. Clone the repository

```bash
git clone <repository-url>
cd RoundLab
```

### 2. Frontend setup

```bash
cd frontend
npm install
```

Copy and fill in the frontend environment file:

```bash
cp .env.example .env.local
# Edit .env.local with your values
```

Start the development server:

```bash
npm run dev
# Opens at http://localhost:3000
```

### 3. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy and fill in the backend environment file:

```bash
cp .env.example .env
# Edit .env with your values
```

Start the backend:

```bash
uvicorn app.main:app --reload
# Runs at http://localhost:8000
```

### 4. Supabase migrations

Apply all migration files in the `supabase/migrations/` directory in timestamp order via the Supabase SQL editor or CLI. See `DEPLOYMENT.md` for the full Supabase setup checklist.

### 5. Verify the setup

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend health: [http://localhost:8000/health](http://localhost:8000/health)
- Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`

---

## Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Purpose | Browser-safe |
|----------|---------|--------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | Yes (`NEXT_PUBLIC_`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key (public) | Yes (`NEXT_PUBLIC_`) |
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Yes (`NEXT_PUBLIC_`) |

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`backend/.env`)

| Variable | Purpose | Notes |
|----------|---------|-------|
| `SUPABASE_URL` | Supabase project URL | Server-only |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key (bypasses RLS) | **Never expose to browser** |
| `OPENAI_API_KEY` | OpenAI API key for analysis and transcription | Server-only |
| `CORS_ORIGINS` | Comma-separated allowed origins | e.g. `http://localhost:3000` |
| `ENVIRONMENT` | `development`, `staging`, or `production` | Enables dev-only endpoints when `development` |

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
OPENAI_API_KEY=your-openai-api-key
CORS_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

### Optional integrations

| Variable | Purpose | Where set |
|----------|---------|-----------|
| `TAVILY_API_KEY` | Research search provider (Evidence Studio) | Backend |
| `EXA_API_KEY` | Alternative search provider | Backend |
| `FIRECRAWL_API_KEY` | Page extraction fallback | Backend |
| `COHERE_API_KEY` | Optional semantic reranking | Backend |

---

## Database and Migrations

RoundLab uses Supabase Postgres with Row Level Security (RLS). Every user-owned table is scoped by `user_id` with RLS policies that enforce ownership.

The service-role key used in the backend bypasses RLS for server-side operations. It must never enter the browser.

### Migration files

Located at `supabase/migrations/`. Apply in timestamp order:

```
20260524000000_initial_schema.sql        Core tables: speeches, transcripts, argument_maps, feedback_reports, drills
20260601000000_add_drill_fields.sql
20260602000000_add_teams.sql             Team/coach tables and RLS
20260602100000_add_feedback_rating.sql
20260604000000_add_xp_ledger.sql
20260606000000_add_drill_time_limit.sql
20260607000000_add_rerecord_fields.sql
20260608100000_add_evidence_tables.sql   Evidence Studio tables
20260608110000_fix_document_storage_policies.sql
20260609000000_add_pilot_tables.sql
...                                      (21 migrations total as of Phase D)
20260618000000_add_assignments.sql       Coach assignment system
```

Apply via the Supabase Dashboard SQL editor or Supabase CLI:

```bash
supabase db push   # if using Supabase CLI with linked project
```

See `DEPLOYMENT.md` for the complete Supabase setup walkthrough including the required `audio` storage bucket.

---

## Testing

All commands must be run from the `frontend/` directory unless otherwise noted.

### Frontend (Jest)

```bash
cd frontend
npx jest --no-coverage       # full suite
npx jest --watchAll          # watch mode
npx jest --testPathPatterns="marketing"   # single suite
```

### TypeScript

```bash
cd frontend
npx tsc --noEmit
```

### Production build

```bash
cd frontend
npm run build
```

### Playwright (end-to-end)

Playwright runs the frontend dev server automatically during tests.

```bash
cd frontend
npx playwright test                          # all projects
npx playwright test e2e/speechFlow.spec.ts   # single spec
npx playwright test --list                   # see all test names
```

**Projects:** `chromium`, `mobile-chrome`, `tablet`

### Backend (pytest)

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/                      # full suite
python -m pytest tests/test_auth.py          # single file
```

### Current test baseline (Phase D — point in time)

| Suite | Count |
|-------|-------|
| Frontend Jest — passing | 1,452 |
| Playwright — unique test definitions | 118 |
| Playwright — spec files | 7 |
| Playwright — projects | 3 |
| Playwright — total project-expanded executions | 354 |
| Backend pytest — collected | ~1,330 |
| TypeScript | clean |
| Frontend build | green |

The Playwright count of 354 reflects 118 unique tests × 3 browser projects. When reporting test results, distinguish unique tests from total executions to avoid confusion.

---

## Accessibility and Responsive Design

### Keyboard interaction

- All interactive elements are keyboard-reachable via Tab
- ARIA tab patterns use manual roving tabIndex with ArrowLeft/Right/Home/End navigation
- Custom `focus-visible` rings use `ring-lav/50` to distinguish from decorative borders
- Focus is trapped in dialogs and restored on close

### ARIA patterns

- Tablist/tab/tabpanel pattern in JudgeLensSection (Phase B) with `aria-selected` and `aria-controls`
- Live regions (`role="status" aria-live="polite"`) for dynamic content changes
- Landmark roles on all major page sections
- Buttons never used for navigation; links never used for actions

### Reduced-motion

All animations are wrapped in `reducedSafe()` from `src/lib/motion.ts`. When `prefers-reduced-motion: reduce` is active:
- Entrance animations are suppressed entirely (no `initial` prop)
- State transitions are instant
- No content depends on animation completing to be readable
- The `isMounted` pattern prevents hydration mismatch for animation state

### Responsive targets

| Viewport | Context |
|----------|---------|
| 390×844 | Mobile (iPhone 14) |
| 768×1024 | Tablet portrait |
| 1024×768 | Laptop small |
| 1280×800 | Laptop standard |
| 1440×900 | Desktop |

Playwright responsive tests run at 390×844 (mobile-chrome project). Overflow checks use `scrollWidth ≤ viewport + 2px`.

### Accessibility testing

Playwright tests use `@axe-core/playwright` for automated WCAG 2.1 AA checks. Suppressions are documented inline in `e2e/accessibility.spec.ts`.

No full WCAG certification has been conducted.

---

## Design System

See [`DESIGN.md`](DESIGN.md) for the complete token reference and design principles.

See [`docs/ROUNDLAB_DESIGN_DIRECTION.md`](docs/ROUNDLAB_DESIGN_DIRECTION.md) for phase-by-phase design decisions and visual review records.

See [`docs/VISUAL_REVIEW_CHECKLIST.md`](docs/VISUAL_REVIEW_CHECKLIST.md) for the pre-PR visual review protocol.

### Core principles (summary)

1. **Debate structure is the design.** Every surface should evoke a flow sheet, a ballot, or a judge's desk.
2. **Product interface is the marketing.** Show real UI states, not abstract illustrations.
3. **One section, one idea.** Never stack identical rhythms.
4. **Color carries meaning.** `lav` = brand/AI provenance. `ok/warn/danger` = argument health. Never decorative.
5. **Restrained motion.** Animate workflow progression and state transitions only. No perpetual animation.
6. **Preserve successful visual ideas.** A comprehensive UI improvement should refine strong existing interactions rather than replace them by default.

### Design tokens (in `frontend/src/app/globals.css`)

Key tokens: `canvas`, `surface-1/2/3`, `hairline/hairline-strong`, `ink/ink-muted/ink-subtle/ink-faint`, `lav/lav-hi`, `ok/warn/danger`.

Key CSS utilities: `section-stamp` (11px mono uppercase for eyebrows), `text-headline` (section headings), `text-title` (metric displays), `beam-top` (top lav gradient accent on cards).

---

## Deployment

### Frontend (Vercel)

| Setting | Value |
|---------|-------|
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output directory | `.next` (automatic) |
| Production branch | `main` |

Required environment variables in Vercel project settings:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` (must point to the deployed backend URL)

### Backend (Render or Railway)

| Setting | Value |
|---------|-------|
| Root directory | `backend` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Python version | 3.11+ |

Required environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `CORS_ORIGINS`.

`CORS_ORIGINS` must include the full Vercel frontend URL (including `https://`).

### Common deployment pitfalls

- Vercel project root must be set to `frontend/`, not the repo root — otherwise the build fails
- Local `.env.local` and `.env` files are never committed; they must be set in the hosting provider's dashboard
- A local commit does not update production until pushed to `main` and the Vercel deployment completes
- `SUPABASE_SERVICE_ROLE_KEY` must remain server-side only; `NEXT_PUBLIC_SUPABASE_ANON_KEY` is safe in the browser

See `DEPLOYMENT.md` for the complete first-time setup walkthrough.

---

## Development Workflow

```
feature branch
  → local changes
  → npx tsc --noEmit            (TypeScript)
  → npx jest --no-coverage      (unit tests)
  → npm run build               (build check)
  → npx playwright test         (e2e)
  → visual review at 5 viewports
  → commit
  → PR to main
  → Vercel preview deployment (automatic)
  → merge to main
  → production deployment (automatic via Vercel)
```

### Visual comparison using Git worktrees

To compare two branches side by side in the browser:

```bash
git worktree add /tmp/roundlab-compare <other-branch>
cd /tmp/roundlab-compare/frontend && npm install && npm run dev -- --port 3001
# Main branch runs on :3000, comparison branch on :3001
```

Worktrees are in `.claude/worktrees/` locally; do not commit them.

### What not to commit

- `.env.local` (frontend secrets)
- `.env` (backend secrets)
- Playwright test-result artifacts (`test-results/`)
- Claude worktrees (`.claude/worktrees/`)
- Python `__pycache__` and `.venv`
- Any speech recordings or user data

---

## Current Status

### Operational

- Speech recording, upload, and paste → transcription → argument analysis → ballot → drills
- Speech report with flow, ballot, skills, transcript, drills, and delivery analysis
- Evidence Studio: research, card cutting, markup, save, export
- Team and coach workflows: assignments, review queue, team overview
- Google authentication via Supabase
- Interactive homepage with continuous C1 debate example across Phase A–D sections
- Demo report at `/demo` (full sample without login)
- Pilot tools at `/pilot`

### Pilot-ready but not yet at scale

- Delivery analysis (deterministic; no ML model)
- Blockfile/frontline trainer (semantic coverage check)
- Tournament workout mode
- Shared coach reports

### Known limitations

- No mobile audio recording optimization (browser-level mic; quality varies)
- Delivery analysis requires audio; transcript-only input returns structural feedback only
- Evidence search quality depends on external provider availability (Tavily/Exa)
- No email notifications or scheduling features
- No full-round mode (sequential 1AC → 2NC → … flow)
- Judge adaptation covers three profiles (flow / lay / parent); not further calibrated by individual judge

---

## Roadmap

Items below are planned but not implemented:

- **Full-round mode:** Sequential speech input through the full PF round structure
- **Expanded judge profiles:** Additional named judge types beyond flow/lay/parent
- **Evidence-link ingestion:** User provides URLs at research time; system fetches and queues
- **Scheduling and reminders:** Practice reminder notifications and tournament prep schedules
- **Richer coach analytics:** Team-wide skill trend dashboards, per-student history
- **Assignments v2:** Announcements, rubric templates, and assignment comments
- **Broader public speaking support:** Extension beyond PF to LD, Congress, or extemporaneous

---

## Contributing

### Branch convention

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/short-description
# or
git checkout -b ui/section-name
```

### Before opening a PR

1. Run `npx tsc --noEmit` — must be clean
2. Run `npx jest --no-coverage` — all tests must pass
3. Run `npm run build` — must complete without error
4. Run `npx playwright test` — all projects must pass
5. If you added or changed UI: visual review at all five standard viewports
6. If you changed a marketing section: review `docs/ROUNDLAB_DESIGN_DIRECTION.md` for prior decisions

### Design expectations for UI work

- Every new interactive state needs an accessible non-animated fallback
- Use design tokens — no `text-[Npx]` or `bg-[#hex]` in component files
- Reduced-motion: wrap entrance animations in `reducedSafe()`
- No `role="alert"` on static marketing content
- Follow the ARIA patterns established in existing components (roving tabIndex for tablists, `role="status"` for live regions)

### Preservation rule

> A comprehensive UI improvement should refine strong existing interactions rather than remove them by default.

Before removing a homepage section or component, document: what it does, what replaced it, and why the replacement is stronger.

### Accessibility expectations

- All interactive elements keyboard-reachable
- Color is never the only indicator of state (always paired with icon or text)
- Screen-reader-only text (`sr-only`) for visual-only indicators
- No content hidden behind JavaScript completion

---

## Security and Privacy

- **Service-role key is server-only.** The `SUPABASE_SERVICE_ROLE_KEY` bypasses Row Level Security and must never appear in frontend code or browser network requests.
- **User data is scoped.** RLS policies on all user-owned tables enforce that users can only access their own speeches, reports, and drills. Coaches see student data only for teams they manage.
- **Audio recordings may be sensitive.** Uploaded speech files are stored in Supabase Storage under the user's account. Contributors must not commit any real user recordings.
- **Credentials are never committed.** `.env`, `.env.local`, and any file containing real keys must remain in `.gitignore`.
- **No compliance certification** (FERPA, COPPA, GDPR) has been formally conducted. RoundLab is currently in pilot with consenting participants.

---

## License

No license file is present in this repository. All rights reserved unless otherwise stated by the project owner. Contact the repository owner before using, modifying, or distributing this code.

---

*Built for competitive Public Forum. Coaching, not case generation.*
