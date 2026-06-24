# Opponent Speech Rules — Pass 17

## Core Constraints

These constraints hold regardless of difficulty or judge type:

1. **No fabricated evidence** — opponent only cites approved cards with verified support verdicts.
2. **No unsupported cards** — cards with `support_verdict` in `{"not_supported", "contradicts", "abstract_only"}` are excluded.
3. **No new evidence in crossfire** — crossfire questions/answers reference existing speech content only.
4. **No chain-of-thought exposure** — opponent reasoning is never exposed to the student.

## Evidence Policy

From `_UNUSABLE_VERDICTS` in `opponent_speech_generator.py`:
```python
_UNUSABLE_VERDICTS = {"not_supported", "contradicts", "abstract_only"}
```

Cards with these verdicts cannot be read even if the difficulty is VARSITY.

## Deduplication

The opponent tracks `evidence_read` in `OpponentRoundMemory`. Cards already read in prior speeches are deprioritized (not repeated in the same round).

## Speech Goals by Phase

| Phase | Goal |
|-------|------|
| Constructive | Establish core offense: tag → warrant → impact |
| Rebuttal | Address student arguments, extend own offense |
| Summary | Collapse to best voter, extend through, weigh |
| Final Focus | Name one voter, explain why it wins, compare |

## Quality Checks

- Speech is validated for warrant presence before returning
- If LLM refiner is enabled, it validates the cut before insertion
- Fallback to deterministic speech if LLM generation fails
- New arguments in SUMMARY phase trigger a legality warning

## Judge-Type Adaptation (Speech Style Only)

| Judge Type | Style Adjustment |
|------------|-----------------|
| flow | Technical terminology, fast delivery, clear labels |
| lay | Plain language, slower pace, real-world framing |
| truth | Evidence-grounded, substance over speed |
| progressive | Framework-aware, structural weighing |

Note: Style changes affect phrasing only — never evidence content.
