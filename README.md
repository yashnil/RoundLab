# RoundLab

**AI flow coach for novice and JV Public Forum debaters.**

RoundLab helps debaters practice and improve through AI-powered coaching. Record a speech, get judge-style feedback, and complete personalized drills that target your specific weaknesses.

---

## What RoundLab Does

1. **Record or Upload** — Capture a 45-90 second PF speech (constructive, rebuttal, summary, final focus, crossfire)
2. **Transcribe** — Automatic speech-to-text via OpenAI Whisper
3. **Extract Flow** — AI identifies every claim, warrant, evidence, and impact in your speech
4. **Generate Coaching Report** — Judge-style feedback with scores, priorities, strengths, weaknesses, and actionable recommendations
5. **Create Drills** — Three personalized practice exercises targeting your skill gaps (warranting, weighing, drops, clash, judge adaptation)
6. **Track Progress** — Dashboard with XP, levels, badges, skill averages, and drill completion
7. **Team Mode** — Coaches can create teams, invite students, and monitor practice progress

---

## Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 15 (App Router) · TypeScript · Tailwind CSS v4 · shadcn/ui · Motion/React |
| **Backend** | FastAPI · Python 3.12 · Pydantic v2 |
| **Auth & DB** | Supabase (Auth, PostgreSQL, Storage) |
| **AI** | OpenAI GPT-4o (reasoning) · Whisper (transcription) · LangGraph (workflow orchestration) |
| **Styling** | oklch color system · Dark/light mode · Accessible UI components |

---

## Features

### Core Workflow
- ✅ Audio recording (browser MediaRecorder) or file upload (MP3, WAV, M4A, WebM, OGG, MP4)
- ✅ Whisper transcription with word count validation
- ✅ Structured argument extraction (claim → warrant → evidence → impact)
- ✅ Judge-style feedback with 5-dimension scoring (clash, weighing, extensions, drops, judge adaptation)
- ✅ Personalized drill generation (3 drills per speech, skill-targeted)
- ✅ Drill attempts with re-recording and progress tracking

### Gamification (Practice-Focused)
- ✅ **Drill-First XP System**: Rewards practice and completion, not just recording
  - +5 XP per flow generated
  - +10 XP per feedback report
  - +15 XP per drill assigned
  - +10 XP per feedback rating
  - +50 XP per first drill attempt (biggest reward!)
  - +20 XP per repeat drill attempt
  - +25 XP bonus for completing full practice loop (feedback + drills + attempts)
  - **No XP for speech upload/transcription** — level up by completing drills and practice attempts
- ✅ Level progression (Level 1: 0-99 XP, Level 2: 100-249, Level 3: 250-499, Level 4: 500-899, Level 5: 900-1399, Level 6+: 1400+ [+300 per level])
- ✅ **Practice-Focused Badges**: First Feedback, First Drill Attempt, Practice Habit (3 attempts), Full Practice Loop, Feedback Analyst (3 reports), Team Player
- ✅ Skill averages dashboard (clash, weighing, extensions, drops, judge adaptation)

### PF Rubric Calibration (Speech-Type-Specific Scoring)
- ✅ **Expert-Grounded Rubrics**: Different scoring dimensions for each PF speech type
  - **Constructive**: Case Structure (20) · Warranting (25) · Evidence Use (20) · Impact Development (20) · Clarity (15)
  - **Rebuttal**: Clash/Refutation (30) · Coverage (20) · Response Quality (20) · Evidence Comparison (15) · Strategic Framing (15)
  - **Summary**: Extension Quality (25) · Collapse Strategy (20) · Frontlining (20) · Weighing (25) · Judge Clarity (10)
  - **Final Focus**: Ballot Story/Voters (30) · Comparative Weighing (25) · Crystallization (20) · Consistency (15) · Judge Adaptation (10)
- ✅ **Speech-Type Awareness**: Constructive speeches are not penalized for missing clash or extensions; Rebuttal emphasizes direct refutation; Summary focuses on extensions and weighing; Final Focus prioritizes voters and crystallization
- ✅ **Calibrated Scoring**: 90-100 = Tournament-Ready · 80-89 = Strong · 70-79 = Solid · 60-69 = Developing · 50-59 = Flawed but Complete · 40-49 = Major Issues · 30-39 = Severely Underdeveloped · <30 = Incomplete
- ✅ **Novice/JV Calibration**: Complete constructives with evidence and clear advocacy score 50-60 even with weak warrants (not 30); 30-39 reserved for severely underdeveloped or incoherent speeches
- ✅ **Topic-Aware Examples**: Coach Diagnosis uses the student's actual speech topic and claims in before/after improvement examples (e.g., Section 230 examples for tech policy speeches)

### Authentication
- ✅ Supabase Auth with PKCE OAuth flow
- ✅ Google sign-in
- ✅ Session persistence and automatic token refresh

### Team Features
- ✅ **Multi-Team Hub**: Users can join multiple teams (student or coach role)
- ✅ Create team (auto-generates 6-character invite code)
- ✅ Join team (enter invite code from coach)
- ✅ **Coach Dashboard**: View all students' progress in one place
  - Speech count, drills assigned, drill attempts
  - Last practice date for each student
  - Aggregate team stats (total members, speeches, drills, attempts)
- ✅ **Invite Workflow**: Copy invite code or full invite message to share with students
- ✅ **Privacy**: Coaches see progress metadata, not audio recordings or full transcripts

### UI/UX
- ✅ **Theme System**: Full dark/light mode with CSS custom properties (oklch color space)
  - Dark mode: `--color-canvas: oklch(0.065 0.002 264)`, `--color-ink: oklch(0.975 0.001 264)`
  - Light mode: `--color-canvas: oklch(0.985 0.001 264)`, `--color-ink: oklch(0.095 0.002 264)`
  - Toggle persists via localStorage, transforms entire app
- ✅ **Personalized Homepage**: Adapts based on login state (shows name, level, quick actions)
- ✅ **Team Hub**: Multi-team management, coach dashboard, student progress tracking
- ✅ **Smart Speech Workspace**: Reorders sections when session is complete (Coaching Report → Drills → Flow → Transcript)
- ✅ Responsive design (mobile-first, tested on phone/tablet/desktop)
- ✅ Motion animations (stagger, fade-up, card hover, AnimatePresence transitions)
- ✅ **Coaching Report Format**: Summary hero card, "Fix These First" priority cards, judge ballot, coach diagnosis with before/after examples, action checklist
- ✅ Flow visualization with color-coded argument cards (offense, defense, weighing, response, unclear)
- ✅ Coach diagnosis cards with targeted examples, disclaimers, and expandable before/after comparisons
- ✅ Accessible buttons (size-sm: h-8, size-default: h-9, size-lg: h-10)

---

## Getting Started

### Prerequisites

- **Node.js** 22+
- **Python** 3.12+
- **Supabase** project (or local Supabase setup)
- **OpenAI API key** (for Whisper + GPT-4o)

### 1. Clone the Repository

```bash
git clone https://github.com/yashnilmohanty/RoundLab.git
cd RoundLab
```

### 2. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` file in `backend/`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=sk-...

# Optional
ENVIRONMENT=development
LOG_LEVEL=INFO
```

Run the server:

```bash
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`  
Health check: `GET http://localhost:8000/health`

### 3. Frontend Setup

```bash
cd frontend
npm install
```

Create `.env.local` file in `frontend/`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Run the dev server:

```bash
npm run dev
```

Opens at `http://localhost:3000`

### 4. Database Setup

Apply all migrations in order via the **Supabase Dashboard → SQL Editor**, or via CLI:

```bash
# If using Supabase CLI (after supabase link)
supabase db push
```

**Manual migration order:**
```
supabase/migrations/20260524000000_initial_schema.sql      # Core tables
supabase/migrations/20260601000000_add_drill_fields.sql    # Drill metadata
supabase/migrations/20260602000000_add_teams.sql           # Team features
supabase/migrations/20260602100000_add_feedback_rating.sql # Feedback ratings
supabase/migrations/20260604000000_add_xp_ledger.sql       # XP + scoring version
supabase/migrations/20260606000000_add_drill_time_limit.sql # Drill time_limit_seconds
```

**Storage bucket:** Create a bucket named `audio` with public read access for audio files.

**New columns added in Pass 4/5 (already in migrations):**
| Table | Column | Type | Notes |
|-------|--------|------|-------|
| `speeches` | `duration_seconds` | `integer` | Set from recording timer or HTMLAudioElement |
| `drills` | `time_limit_seconds` | `integer CHECK(30–300)` | LLM-generated, NULL for older drills |
| `argument_maps` | `arguments.id` | (JSONB field) | e.g. `"arg_1"`, assigned in app layer |
| `feedback_reports` | `raw_feedback.structured_issues` | (JSONB field) | Present in v2+ reports only |

---

## API Endpoints

### Speeches
- `POST /speeches` — Create new speech session
- `GET /speeches?user_id={id}` — List user's speeches
- `GET /speeches/{speech_id}` — Get speech details
- `PATCH /speeches/{speech_id}` — Update speech
- `DELETE /speeches/{speech_id}` — Delete speech
- `POST /speeches/{speech_id}/reset-audio` — Delete audio and reset workflow

### AI Pipeline
- `POST /speeches/{speech_id}/transcribe` — Run Whisper transcription
- `POST /speeches/{speech_id}/extract-arguments` — Generate argument flow
- `POST /speeches/{speech_id}/generate-feedback` — Generate coaching report
- `POST /speeches/{speech_id}/generate-drills` — Create personalized drills

### Drills
- `GET /speeches/{speech_id}/drills` — List drills for speech
- `PATCH /drills/{drill_id}` — Update drill status
- `POST /drills/{drill_id}/attempts` — Record drill attempt

### Users
- `GET /users/{user_id}/progress` — Gamification dashboard (XP, level, badges, skill averages, incomplete drills)

### Teams
- `POST /teams` — Create team
- `POST /teams/join` — Join team with invite code
- `GET /teams/users/{user_id}` — List user's teams
- `GET /teams/{team_id}/dashboard` — Coach view (student progress)

---

## Running Tests and Checks

### Backend (pytest)
```bash
cd backend
source .venv/bin/activate
pytest                       # all tests
pytest tests/ -q             # quiet output
pytest tests/test_schema_validation.py -v    # schema tests
pytest tests/test_persistence_payloads.py -v # persistence tests
```

### Frontend (TypeScript + build)
```bash
cd frontend
npm run build                # production build + typecheck
npx tsc --noEmit             # typecheck only  (use ./node_modules/.bin/tsc if npx resolves wrong)
```

### Frontend unit tests (Jest)
```bash
cd frontend
npm test                     # runs src/__tests__/**/*.test.ts
```

### Lint
```bash
cd frontend
npm run lint
```

---

## Deployment

### Backend (Render, Railway, Fly.io, etc.)

Set environment variables:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY`
- `ENVIRONMENT=production`

Start command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Frontend (Vercel recommended)

1. Connect GitHub repo to Vercel
2. Set environment variables:
   - `NEXT_PUBLIC_API_URL` (your backend URL)
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. Deploy

---

## Project Structure

```
RoundLab/
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── dashboard/        # Progress dashboard
│   │   │   ├── session/          # Create new speech
│   │   │   ├── speech/[id]/      # Speech workspace
│   │   │   ├── team/             # Team management
│   │   │   └── login/            # Supabase Auth
│   │   ├── components/           # UI components
│   │   │   ├── ui/               # shadcn primitives
│   │   │   ├── AppNav.tsx        # Navigation with theme toggle
│   │   │   ├── ArgumentCard.tsx  # Flow visualization
│   │   │   ├── DrillCard.tsx     # Drill display
│   │   │   ├── ScoreCard.tsx     # Feedback score ring
│   │   │   └── ...
│   │   ├── lib/
│   │   │   ├── api.ts            # Backend fetch wrapper
│   │   │   ├── supabase.ts       # Supabase client (PKCE OAuth)
│   │   │   ├── motion.ts         # Animation presets
│   │   │   └── utils.ts
│   │   └── types/                # TypeScript interfaces
│   └── tailwind.config.ts        # Tailwind v4 config
├── backend/
│   └── app/
│       ├── main.py               # FastAPI app + CORS
│       ├── config.py             # Pydantic settings
│       ├── api/                  # Route handlers
│       │   ├── speeches.py
│       │   ├── drills.py
│       │   ├── teams.py
│       │   └── users.py
│       ├── models/               # Pydantic schemas
│       ├── services/
│       │   ├── supabase_client.py
│       │   ├── openai_client.py
│       │   └── ...
│       └── pipeline/             # LangGraph workflow
│           ├── graph.py
│           ├── nodes.py
│           └── prompts/
└── docs/                         # Product requirements, rubric, samples
```

---

## Testing

### Backend Tests
```bash
cd backend
source .venv/bin/activate
pytest
```

71/71 tests passing (as of 2026-06-03).

### Frontend Build Check
```bash
cd frontend
npm run build
```

All pages compile successfully.

---

## Deployment Safety

### Pre-Deployment Checklist
- [ ] Backend tests pass (`pytest`)
- [ ] Frontend builds without errors (`npm run build`)
- [ ] Environment variables configured in production
- [ ] Supabase migrations applied
- [ ] Audio storage bucket configured (`audio` bucket with public read)
- [ ] CORS origins updated for production domain

### Known Deployment Considerations
- **Audio uploads**: Ensure Supabase storage `audio` bucket has public read access for playback
- **OpenAI API**: Monitor usage and set billing alerts (Whisper + GPT-4o calls)
- **Session persistence**: Supabase Auth tokens persist via localStorage and cookies
- **Theme toggle**: Persists in localStorage, safe for SSR (checked on mount)

---

## Limitations & Known Issues

### Current Limitations
- **Audio formats**: Limited to MP3, WAV, M4A, WebM, OGG, MP4 (max 50MB)
- **Speech length**: Optimized for 45-90 second speeches (PF format)
- **AI accuracy**: Flow extraction and feedback quality depend on audio clarity and speech structure
- **Team management**: No leave team or remove member functionality yet (coaches must manually manage)
- **Drill attempts**: Currently manual status tracking (no automated verification)
- **Mobile recording**: Browser MediaRecorder support varies (upload recommended for iOS Safari)

### Roadmap Considerations
- Real-time collaboration (live team practice sessions)
- Case library and opponent research tracking
- Tournament prep mode (bracket simulation, judge adaptation profiles)
- Advanced analytics (trend analysis, peer comparison)
- Integration with Tabroom.com for tournament results
- Drill verification (AI checks if drill attempt matches prompt)
- Video upload support (for crossfire and body language feedback)

---

## Product Philosophy

**Make the app feel like coaching, not cheating.**

RoundLab is built for **practice**, not case generation. The core loop is:
1. Record a speech you're already prepared to give
2. Get judge-style feedback on delivery and argumentation
3. Complete targeted drills to fix specific weaknesses
4. Re-record to track improvement

This is **not** an AI case writer. It's a **practice partner** that gives you feedback and drills, just like a coach would.

---

## Evaluation Harness

RoundLab includes a labeled evaluation system to measure whether AI outputs are debate-correct.

### Running evals

```bash
# From the backend/ directory:

# Fast — no API cost, tests eval machinery only
python -m evals.run_evals --mock

# Fast — run only 3 fixtures
python -m evals.run_evals --mock --limit 3

# Real LLM — accurate, uses OpenAI API
python -m evals.run_evals

# Single fixture by ID
python -m evals.run_evals --fixture good_constructive
```

Results are written to `backend/evals/results/latest.json` and a timestamped archive.

### Fixtures

Labeled speech fixtures live in `backend/evals/fixtures/`. Each JSON file contains:

| Field | Description |
|-------|-------------|
| `id` | Unique fixture identifier |
| `speech_type` | constructive · rebuttal · summary · final_focus |
| `transcript` | Full speech text (used directly — no audio needed) |
| `expected_issues` | Ground-truth debate issues with severity and `required` flag |
| `expected_argument_components` | Expected claim/warrant/evidence/impact components |
| `expected_drill_types` | Expected skill targets for generated drills |
| `notes` | Explanation of what this fixture tests |

**Current fixtures (8):**

| ID | Type | Primary issue |
|----|------|---------------|
| `good_constructive` | constructive | No explicit impact weighing |
| `missing_warrant_constructive` | constructive | No logical mechanisms |
| `weak_evidence_constructive` | constructive | Vague/unnamed sources |
| `no_weighing_summary` | summary | Extensions without impact comparison |
| `dropped_argument_rebuttal` | rebuttal | Ignores opponent C2 entirely |
| `new_argument_final_focus` | final_focus | New evidence in final focus |
| `no_clash_rebuttal` | rebuttal | Only restates own case |
| `strong_delivery_weak_logic` | constructive | Circular arguments, no evidence |

### Adding a new fixture

1. Create `backend/evals/fixtures/<your_id>.json`
2. Follow the `EvalSpeechFixture` schema in `backend/evals/models.py`
3. Set `required: true` for issues that MUST be detected for the sample to pass
4. Run `python -m evals.run_evals --mock --fixture <your_id>` to verify the fixture loads

### Metrics

| Metric | Description |
|--------|-------------|
| Issue Precision | Fraction of detected issues that were expected |
| Issue Recall | Fraction of expected issues that were detected |
| Issue F1 | Harmonic mean of precision and recall |
| Argument Coverage | Fraction of expected argument components found |
| Drill Relevance | Fraction of expected skill targets in generated drills |
| Hallucinated Evidence | Arguments with vague/unnamed source attributions |

A sample passes if: issue F1 ≥ 0.5, argument coverage ≥ 0.5, and all `required` issues are detected.

### Eval dashboard

Visit `/evals` in the running app to see the eval quality dashboard (reads static fixture data).
To update with latest results, copy `backend/evals/results/latest.json` into `frontend/src/lib/eval_results_fixture.ts`.

### Demo page

Visit `/demo` to see a complete polished RoundLab example using static sample data — no login, no recording required.

---

## Contributing

Pull requests welcome. For major changes, open an issue first.

---

## License

MIT

---

## Contact

Built by [@yashnilmohanty](https://github.com/yashnilmohanty)  
For questions or feedback: yashnilmohanty@gmail.com
