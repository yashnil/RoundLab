# Judge Adaptation Architecture (Pass 15)

## Overview

The Judge Adaptation system translates prepared debate material for five built-in judge types (lay, parent, flow, technical, coach) without altering evidence text, verdicts, or citation metadata.

## Service Layers

```
judge_profiles.py          — 5 built-in profiles, 13 preference dimensions
adaptation_rules.py        — Deterministic changes per judge type
adaptation_risk_checker.py — 14 risk categories, severity-sorted output
frontline_adapter.py       — Response ordering and condensation rules
speech_plan_adapter.py     — Stage-specific speech plans
judge_comparison.py        — Cross-profile constants and differences
judge_workout_generator.py — 7 workout types from prepared material
judge_readiness_scorer.py  — 8 judge-readiness dimensions (SEPARATE from evidence quality)
judge_adaptation_service.py — Orchestrator
```

## Data Flow

```
Request (user_id, judge_type, source_type, source_id)
  → Load source material (card / frontline / argument)
  → run adaptation_rules → list[AdaptationChange]
  → run risk_checker → list[AdaptationRisk]
  → build EvidencePresentationGuide (no body text)
  → build FrontlineAdaptation / SpeechStageAdaptation
  → compute JudgeReadinessReport (separate scoring)
  → persist to judge_adaptations table
  → return JudgeAdaptationResult
```

## Immutability Contract

The following are NEVER modified or stored in adaptation output:
- Evidence body text
- Support verdict (from Pass 11)
- Citation metadata (author, date, URL, MLA string)
- Factual magnitude, causal strength, population scope

The system never strengthens a claim for a persuasive judge.

## Judge Profiles

Five built-in profiles with 13 preference dimensions (1-5 scale):

| Profile   | Jargon | Speed | Line-by-Line | Narrative | Real-World |
|-----------|--------|-------|--------------|-----------|------------|
| Lay       | 1      | 1     | 1            | 5         | 5          |
| Parent    | 2      | 1     | 2            | 5         | 5          |
| Flow      | 4      | 4     | 5            | 2         | 2          |
| Technical | 5      | 5     | 5            | 1         | 1          |
| Coach     | 4      | 3     | 4            | 3         | 3          |

## API Endpoints

All under `/judge-adaptation`:

| Method | Path | Description |
|--------|------|-------------|
| GET | /profiles | List judge profiles |
| GET | /profiles/{judge_type} | Get one profile |
| POST | /profiles/custom | Create custom profile |
| POST | /adapt | Generate adaptation |
| POST | /compare | Compare two judge types |
| POST | /risks | Detect risks for a card |
| POST | /workouts/generate | Generate a workout |
| POST | /workouts/assign | Coach assigns workout |
| PATCH | /workouts/{id}/complete | Mark complete |
| GET | /workouts | List student workouts |
| POST | /notes | Save adaptation note |
| GET | /notes/{adaptation_id} | List notes |
| GET | /history | Adaptation history |
| POST | /readiness-score | Compute judge readiness |

## Database Tables

- `judge_profiles` — User-created custom profiles
- `judge_adaptations` — Persisted adaptation results
- `judge_adaptation_notes` — Notes on adaptations
- `judge_workout_assignments` — Coach→student workout assignments

See `backend/migrations/20260622_pass15_judge_adaptation.sql`.
