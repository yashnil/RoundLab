# Round Quality Evaluation — Pass 17

## Overview

`test_round_quality_p17.py` contains 62 tests covering the quality improvements from Pass 17. These test deterministic behavior only — no LLM calls required.

## Test Coverage

| Category | Tests | What's Tested |
|----------|-------|---------------|
| Opponent Round Memory | 11 | Build from speeches/args, commitments, evidence, prompt context |
| Concession Detector | 10 | Explicit/partial/evasion detection, polite-phrase guard |
| Decision Engine | 12 | Weighing comparison, adaptation feedback, tiebreak |
| Drill Generator | 6 | Phase assignment, conditional crossfire, weighing drill |
| Prep Connector | 6 | DROPPED bug fix, gap categories, missing workspace |
| Crossfire Simulator | 3 | Follow-up, AI answer |
| Coach Review | 7 | Annotation CRUD, type validation, history safety |
| Replay | 6 | Turning point detection, severity ordering, max limit |
| Opponent Strategy | 3 | Plan quality validator |

## Key Quality Metrics (Deterministic)

### Decision Engine
- Adaptation feedback now non-empty for all judge types
- Weighing comparison describes actual argument labels
- Tiebreak: drop count → weighing presence → judge-type default

### Prep Connector Gaps (Pass 17 categories)
- `missing_response` — unanswered LIVE/EXTENDED opponent args (not DROPPED)
- `extension_gap` — student offense not extended through summary
- `weighing_gap` — no comparative weighing detected
- `rebuttal_coverage` — 3+ unanswered opponent args
- `evidence_quality` — flagged evidence uses

### Drill Generator Phases
| Drill Type | Expected Phase |
|------------|---------------|
| dropped_response | first_rebuttal |
| rebuttal_coverage | first_rebuttal |
| evidence_explanation | first_constructive |
| summary_extension | first_summary |
| final_focus_consistency | first_final_focus |
| weighing | first_summary |
| crossfire_concession | grand_crossfire |

## Pre-existing Failures (Do Not Fix)

- `test_read_aloud_passes_validator[rwanda]`
- `test_enabled_scorer_changes_ranking`
