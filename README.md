# RoundLab

AI flow coach for novice and JV Public Forum debaters.

Record or upload a speech → transcribe → extract claims/warrants/evidence/impacts → generate a flow table → get ballot-style feedback → receive three personalized drills.

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16 · TypeScript · Tailwind v4 · shadcn/ui |
| Backend | FastAPI · Python 3.12 · Pydantic |
| Auth / DB | Supabase (Sprint 2) |
| Transcription | OpenAI Whisper (Sprint 2) |
| AI Pipeline | LangGraph (Sprint 2) |

---

## Getting Started

### Prerequisites

- Node.js 22+
- Python 3.12+

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:3000`.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`.  
Health check: `GET http://localhost:8000/health`

---

## Environment Variables

Copy `.env.example` to `.env` in the repo root and fill in values:

```bash
cp .env.example .env
```

The backend reads `.env` from `backend/`. Copy or symlink as needed:

```bash
cp .env backend/.env
```

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

---

## Project Structure

```
RoundLab/
├── frontend/          # Next.js app
│   └── src/
│       ├── app/       # Pages (App Router)
│       ├── components/# UI components (shadcn)
│       ├── lib/       # api.ts, utils.ts
│       └── types/     # Shared TypeScript types
├── backend/           # FastAPI app
│   └── app/
│       ├── main.py    # App entry, CORS
│       ├── config.py  # Pydantic Settings
│       ├── api/       # Route handlers
│       ├── models/    # Pydantic schemas
│       ├── services/  # Business logic (Sprint 2)
│       └── pipeline/  # LangGraph graph (Sprint 2)
└── docs/              # Product and design docs
```
