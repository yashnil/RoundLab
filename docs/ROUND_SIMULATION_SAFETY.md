# Round Simulation Safety Constraints

## Hard Constraints (Never Violated)

1. **No evidence fabrication** — opponent only uses cards from the user's approved list; analytic arguments are labeled `[Analytical]`
2. **No card mutation** — saved card records are read-only during simulation; usage metadata is stored in `round_evidence_uses`
3. **No late new arguments** — `is_new_argument_legal(phase)` returns False in summary/final focus/crossfire; violations are flagged but do not block the round (coaching, not gating)
4. **No web search during round** — opponent speech generator does not call any search provider; it uses only pre-loaded opponent plan data
5. **No free-form LLM winner** — `run_decision_engine()` derives the winner deterministically; LLM only writes the RFD narrative from already-determined trace facts
6. **No private reasoning exposed** — internal scoring variables (pro_score, con_score, penalty values) are not included in the API response; only the trace, winner, and RFD are surfaced
7. **No cross-user data access** — `_verify_owner()` + RLS on all tables; `_fetch_approved_cards()` filters by user_id

## Graceful Degradation

| Failure | Behavior |
|---|---|
| LLM speech generation fails | `_deterministic_fallback()` produces a safe speech from plan without LLM |
| LLM speech references unauthorized card | Retry once; if still bad, fall back to deterministic |
| LLM RFD generation fails | `_deterministic_rfd()` writes RFD from trace without LLM |
| LLM crossfire question fails | `_fallback_question()` generates a template question |
| DB save fails | Logged; round can continue in memory |

## What the Simulation Does Not Do

- Build a multiplayer round (live opponent is always AI)
- Run tournament pairing or tabulation
- Add video analysis
- Replace or modify existing single-speech practice (independent feature)
- Fix the two known pre-existing test failures (`test_read_aloud_passes_validator[rwanda]`, `test_enabled_scorer_changes_ranking`)

## Debate-Native Coaching Orientation

Violations detected by `speech_legality_checker.py` and `evidence_use_tracker.py` are surfaced as coaching feedback in the ballot — they are not errors that prevent round progression. The goal is skill feedback, not gate-keeping.
