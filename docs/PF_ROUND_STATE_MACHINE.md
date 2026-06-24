# PF Round State Machine

## Full Phase Order (13 phases)

```
first_constructive → second_constructive → first_crossfire
→ first_rebuttal → second_rebuttal → grand_crossfire
→ first_summary → second_summary → final_crossfire
→ first_final_focus → second_final_focus → judge_deliberation → completed
```

## Format Variants

| Format | Description |
|---|---|
| `full` | All 13 phases (standard PF round) |
| `shortened` | Removes grand_crossfire and final_crossfire |
| `speech_stage_drill` | Constructives + first crossfire only |
| `evidence_testing` | Constructives + rebuttals only |

## Phase Classification

**Crossfire phases** (no speeches, AI questions): `first_crossfire`, `grand_crossfire`, `final_crossfire`

**Late phases** (no new arguments legal): `first_summary`, `second_summary`, `final_crossfire`, `first_final_focus`, `second_final_focus`, `judge_deliberation`, `completed`

## Transition Rules

- Phase transitions must be sequential (no skipping) unless `practice_override=True`
- Backward transitions are always rejected
- Transitions from `completed` are always rejected
- A phase must exist in the format's phase order

## Speaking Assignment

`phase_speaker(phase, config)` returns the side that speaks in a given phase:
- Based on `speaking_order` (first/second) and `student_side` (pro/con)
- Returns `None` for crossfire phases and `completed`/`judge_deliberation`

`student_speaks_in_phase()` returns `True` when the student is the speaker, or `True` for all crossfire phases (both sides participate).

## Time Limits (default)

| Phase type | Duration |
|---|---|
| Constructive | 240 s (4 min) |
| Rebuttal | 240 s |
| Summary | 180 s (3 min) |
| Final Focus | 120 s (2 min) |
| Crossfire | 180 s |

## Difficulty Parameters

| Level | Max words | Use evidence | Use analytics |
|---|---|---|---|
| novice | 300 | True | True |
| jv | 450 | True | True |
| varsity | 600 | True | True |

Difficulty controls how much the AI opponent uses — not what the student is allowed to do.
