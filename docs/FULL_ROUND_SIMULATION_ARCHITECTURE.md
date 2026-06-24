# Full Round Simulation Architecture

## Overview

Pass 16 adds a complete Public Forum practice simulator. A student configures a round, runs through all 13 speech phases against an AI opponent using only pre-approved evidence cards, receives an explainable ballot from a deterministic decision engine, and gets targeted post-round drills linked to actual round failures.

## Component Map

```
round_state_machine.py     Phase ordering, time limits, transition rules
opponent_strategy.py       Build opponent plan from approved cards (no fabrication)
opponent_speech_generator.py  Bounded LLM speech with deterministic fallback
round_flow_tracker.py      Append-only event log + deterministic status replay
evidence_use_tracker.py    Per-card tracking, violation detection
speech_legality_checker.py  Deterministic per-phase rule enforcement
crossfire_simulator.py     AI question generation, student answer processing
round_decision_engine.py   8-step deterministic winner derivation
round_drill_generator.py   10 drill templates linked to round failures
round_prep_connector.py    Reads/writes Tournament Prep tables
```

## Request Flow

1. `POST /round-simulations` → create round, store config
2. `GET /round-simulations/{id}/prep-warnings` → pre-round readiness check (non-blocking)
3. `POST /{id}/start` → advance to first_constructive
4. Per phase:
   - **Student speech**: `POST /{id}/speeches/student` → legality check → flow update → evidence tracking
   - **Opponent speech**: `POST /{id}/speeches/opponent` → load plan → generate bounded speech → validate → flow update
   - **Crossfire**: `GET /{id}/crossfire/question` + `POST /{id}/crossfire/answer`
5. `POST /{id}/advance-phase` → state machine transition
6. `POST /{id}/decision` → run 8-step engine, store RoundDecision
7. `POST /{id}/rejudge` → new Decision with different judge profile
8. `POST /{id}/drills` → generate drills linked to failures

## Data Flow Invariants

- `round_flow_events` is insert-only; statuses are derived by replaying the event log
- Saved cards are never mutated; the evidence use record stores usage metadata separately
- Decision engine derives winner from structured trace facts; LLM only writes the RFD narrative using those facts
- All opponent speech card references are validated against approved_card_ids before being inserted

## Database Tables (9 new)

| Table | Purpose |
|---|---|
| round_simulations | Root record + config |
| round_participants | Per-side metadata |
| round_speeches | All submitted speeches with legality results |
| round_crossfire_exchanges | AI questions + student answers |
| round_arguments | Flow arguments with current status |
| round_flow_events | Append-only event log |
| round_evidence_uses | Per-card use tracking |
| round_decisions | Deterministic ballot records |
| round_drills | Post-round targeted drills |
| opponent_round_plans | Cached opponent strategy per round |
| round_adaptation_reviews | Judge-style balance assessment |

## Security Model

Every endpoint calls `_verify_owner()` which checks that the requesting user_id matches the round's user_id. All 9 tables have RLS with user ownership policies. Service-role has bypass for background operations.
