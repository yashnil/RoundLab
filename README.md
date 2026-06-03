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

### Gamification
- ✅ XP system: +5 XP/speech, +10 XP/feedback, +25 XP/drill generated, +50 XP/first drill attempt, +20 XP/repeat attempt
- ✅ Level progression (Level 1: 0-99 XP, Level 2: 100-249, Level 3: 250-499, Level 4: 500-899, Level 5: 900-1399, Level 6+: 1400+)
- ✅ Badges: First Speech, Flow Builder, Judge Ready, Drill Starter, Consistent Speaker, Practice Streak, Team Player
- ✅ Skill averages dashboard (averaged across all feedback reports)

### Team Features
- ✅ Create team (generates 6-character invite code)
- ✅ Join team (enter invite code)
- ✅ Coach dashboard (view student progress, speeches, drills, attempts, last practice date)
- ✅ Privacy: coaches see progress metadata, not audio or transcripts

### UI/UX
- ✅ Dark mode (default) and light mode toggle with localStorage persistence
- ✅ Responsive design (mobile-first, tested on phone/tablet/desktop)
- ✅ Motion animations (stagger, fade-up, card hover)
- ✅ Coaching report format (summary card, priority cards, judge ballot, coach diagnosis, action checklist)
- ✅ Flow visualization with argument cards (color-coded by type: offense, defense, weighing, response, unclear)
- ✅ Improvement examples with disclaimers
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

Run Supabase migrations (see `backend/supabase/` for schema):

```sql
-- Tables: speeches, transcripts, argument_maps, feedback_reports, drills, drill_attempts, teams, team_members
-- Storage bucket: audio (for speech recordings)
```

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

## Running Tests

Backend tests (pytest):

```bash
cd backend
source .venv/bin/activate
pytest
```

Frontend build check:

```bash
cd frontend
npm run build
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

## Contributing

Pull requests welcome. For major changes, open an issue first.

---

## License

MIT

---

## Contact

Built by [@yashnilmohanty](https://github.com/yashnilmohanty)  
For questions or feedback: yashnilmohanty@gmail.com
