# Opponent Strategy Quality — Pass 17

## Overview

The opponent strategy system builds a structured round plan (`OpponentRoundPlan`) from approved evidence cards. Pass 17 upgrades the plan to be resolution-aware, difficulty-differentiated, and quality-validated before use.

## Key Services

- `opponent_strategy.py` — `build_opponent_round_plan()`, `validate_plan_quality()`
- `opponent_round_memory.py` — `build_memory_for_phase()`, `to_prompt_context()`

## Plan Quality Validator

`validate_plan_quality(plan, config) -> List[str]` returns a list of warnings:

| Warning | Condition |
|---------|-----------|
| No viable summary path | No argument has `"summary"` in speech_suitability |
| Impact without warrant | An argument has impact but no warrant string |
| No final focus voter | No argument has `"final_focus"` in suitability |
| Too many arguments | Count exceeds difficulty limit |
| No response options | `expected_responses` is empty |

Empty list = plan is valid.

## Difficulty Differentiation

| Difficulty | Max Args | Goals |
|------------|----------|-------|
| NOVICE | 1–2 | Simple offense, clear impact |
| JV | 2–3 | Full case + collapse path |
| VARSITY | 3–4 | Strategic turns, preemptive responses |

## Round Memory

`OpponentRoundMemory` tracks:
- `opponent_commitments` — claims the AI opponent has made
- `student_commitments` — claims the student has made
- `concessions` — concessions detected in crossfire
- `strategic_priorities` — remaining live offense the opponent must win
- `planned_collapse` — best extended argument for summary
- `judge_risk_notes` — brief judge-profile warnings
- `evidence_read` — card IDs already used (to avoid repeats)

Use `to_prompt_context(memory)` to get a ≤600-char prompt injection.

## Constraints

- Opponent never invents claims beyond its cards.
- Difficulty changes speech goals, not evidence content.
- Memory is reconstructable deterministically from DB records.
