# Round Replay — Pass 17

## Overview

`round_replay.py` reconstructs a phase-by-phase replay timeline from append-only round records and identifies turning points — key moments where the round changed.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{round_id}/replay` | Phase-by-phase replay |
| GET | `/{round_id}/turning-points` | Key turning points only |

## ReplayPhase

Each phase in the timeline contains:
- `phase` / `phase_label` / `speaker_label`
- `transcript_preview` — first 200 chars of transcript
- `flow_events` — events that happened in this phase
- `arguments_changed` — argument status transitions in this phase
- `evidence_used` — card IDs used
- `legality_violations` — violations detected
- `turning_points` — turning points in this phase

## Turning Point Types

| Type | Description | Severity |
|------|-------------|----------|
| `major_drop` | Offense argument dropped | critical |
| `key_turn` | Argument turned against original speaker | critical |
| `final_focus_mismatch` | FF voter not in summary | critical |
| `failed_extension` | Argument not extended through summary | significant |
| `evidence_challenge_unanswered` | Challenged evidence left unanswered | significant |
| `decisive_concession` | High-confidence crossfire concession | significant |
| `strongest_weighing` | Explicit comparative weighing present | notable |

## Rules

- Maximum 8 turning points total
- Sorted: critical → significant → notable
- Never more than 8 — only the most impactful moments
- Does NOT mutate historical records

## Usage

```python
from app.services.round_replay import build_replay_timeline, identify_turning_points

# Full timeline
timeline = build_replay_timeline(round_id, all_args, speeches, crossfire, ev_uses, decision)

# Turning points only
tps = identify_turning_points(all_args, speeches, crossfire, ev_uses, decision)
```
