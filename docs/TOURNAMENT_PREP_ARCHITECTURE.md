# Tournament Prep Architecture (Pass 14)

## Overview

Tournament Prep is a workspace-level feature that synthesizes a debater's evidence library, blockfiles, and frontlines into an actionable readiness report. It exposes:

1. **Readiness Report** — 7-dimension analysis with a composite score, gap list, freshness assessments, and next actions.
2. **Prep Plan** — Prioritized task list derived deterministically from gaps. Never destroys manually created or completed tasks.
3. **Gap-Driven Workouts** — 7 workout types, each derived from actual saved evidence cards. Card body is snapshot at creation time (immutable).

No LLM scores the report. No evidence is automatically replaced.

---

## Database Tables (Pass 14 migration)

| Table | Purpose |
|---|---|
| `prep_workspaces` | Tracks resolution + side + tournament date per user. Unique on (user_id, resolution_id, side). |
| `prep_readiness_reports` | Persisted report JSON + summary columns (gap_count, stale_card_count, composite_score). |
| `prep_gaps` | Individual gap records linked to arguments/blockfiles/cards/frontlines. |
| `prep_tasks` | Ordered task list. `is_auto_generated` distinguishes generated vs manual tasks. |
| `prep_workouts` | Workout rows with `source_card_body` snapshot (first 1000 chars of card at generation time). |

All tables use RLS (owner = user_id) and `updated_at` triggers via `p14_set_updated_at()`.

---

## Service Layer

```
backend/app/services/
├── evidence_freshness.py          # Claim-type-aware freshness assessment
├── blockfile_coverage_analyzer.py # Argument-type-aware coverage matrix
├── frontline_readiness_analyzer.py# 4-level readiness classifier
├── readiness_scorer.py            # 7-dimension deterministic scorer
├── prep_plan_service.py           # Gap → task mapping, task CRUD
├── gap_workout_generator.py       # 7 workout builders
└── tournament_prep_service.py     # Orchestrator: loads library data + generates report
```

Each service is independently unit-testable. The orchestrator (`tournament_prep_service.py`) is the only file that calls the others and reads the Supabase client.

---

## API

All endpoints under `/prep` prefix.

| Method | Path | Description |
|---|---|---|
| `POST` | `/prep/workspaces` | Create/upsert workspace |
| `GET` | `/prep/workspaces` | List user's workspaces |
| `GET` | `/prep/workspaces/{id}` | Get single workspace |
| `PATCH` | `/prep/workspaces/{id}` | Update workspace (side, date, emphasis) |
| `POST` | `/prep/readiness-report` | Generate (or return cached) readiness report |
| `POST` | `/prep/prep-plan` | Generate task list + workouts from a report |
| `GET` | `/prep/workspaces/{id}/tasks` | List workspace tasks |
| `POST` | `/prep/tasks` | Create a manual task |
| `PATCH` | `/prep/tasks/{id}` | Update task status |
| `GET` | `/prep/workspaces/{id}/workouts` | List workspace workouts |
| `PATCH` | `/prep/workouts/{id}/complete` | Mark workout complete |
| `GET` | `/prep/freshness/{card_id}` | Assess a single card's freshness |
| `GET` | `/prep/workspaces/{id}/overview` | Workspace + latest report + pending tasks + active workouts |
| `POST` | `/prep/newer-evidence` | Return suggested queries for finding newer evidence |

---

## Frontend

```
frontend/src/
├── types/prep.ts                           # All TS interfaces mirroring Pydantic models
├── app/prep/page.tsx                       # Tournament Prep workspace page
└── components/prep/
    ├── ReadinessOverview.tsx               # Composite score + 7 dimension bars
    ├── GapsPanel.tsx                       # Severity-grouped gap list
    ├── FreshnessPanel.tsx                  # Freshness state summary + card list
    ├── PrepPlanPanel.tsx                   # Task list with inline complete buttons
    └── PrepWorkoutPanel.tsx                # Workout cards with expand-and-complete flow
```

The page is tab-based: Overview / Gaps / Freshness / Prep Plan / Workouts.

Tournament Prep is reachable from `/prep?workspace=<id>` or `/prep?resolution=<id>&side=<side>` (auto-creates workspace).

---

## Data Flow

```
User opens /prep
  → ensureWorkspace()         creates or reuses prep_workspace
  → POST /prep/readiness-report
      → tournament_prep_service.generate_readiness_report()
          → loads all library data for (user, resolution, side)
          → runs all 4 gap detectors
          → runs all 4 dimension assessors (freshness / coverage / frontline / quality)
          → readiness_scorer.score_dimensions() → ReadinessDimensions
          → returns PrepReadinessReport (fully serializable, no DB writes)
      → API persists report JSON to prep_readiness_reports
  → POST /prep/prep-plan
      → prep_plan_service.generate_tasks_from_report()
      → gap_workout_generator.generate_workouts_for_report()
      → save tasks + workouts to DB
      → returns PrepPlan
```

---

## Observability Events

| Event Name | When |
|---|---|
| `readiness_reports_generated` | After successful report generation |
| `prep_tasks_created` | After plan generation |
| `prep_tasks_completed` | After user marks a task done |
| `workouts_completed` | After user marks a workout done |
| `newer_evidence_searches` | After newer-evidence query requested |

---

## Design Constraints (from Pass 14 spec)

- Analysis is deterministic; no LLM scoring pipeline.
- No evidence is auto-replaced; `newer_evidence` endpoint returns search suggestions only.
- Historical/legal evidence is never flagged stale solely based on age.
- Completed tasks and manually created tasks are never deleted on plan refresh.
- Source card body is snapshot at workout creation time (immutable evidence for drills).
- Coach assignments (`team_id`) supported via workspace, but no private evidence exposed.
