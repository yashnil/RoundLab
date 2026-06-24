# Round Decision Engine

## Design Principle

The winner is never a single opaque LLM judgment. The engine runs 8 deterministic steps and builds a structured trace. The LLM is only used to write a natural-language RFD *constrained to the facts already in the trace*. If LLM generation fails, `_deterministic_rfd()` writes the RFD from trace facts without any LLM call.

## 8-Step Decision Process

1. **Gather arguments** — load all `RoundArgument` records for the round
2. **Compute surviving offense** — pro and con sides separately; excludes `dropped`, `conceded`, `turned`, `outweighed`; excludes `is_framework=True` and `is_offense=False`
3. **Compute dropped arguments** — any with status `dropped` or `conceded`
4. **Check weighing** — scan summary + final focus speeches for weighing language; count phrases per side
5. **Check evidence** — load `RoundEvidenceUse` records; count flagged uses per side; penalize flagged side
6. **Apply judge profile** — `_apply_judge_profile_weights()` adjusts pro/con scores for evidence_detail_preference, weighing_expectation, jargon_tolerance
7. **Determine winner** — compare final scores; tie goes to pro (debate convention)
8. **Generate RFD** — LLM writes narrative from trace; `_deterministic_rfd()` as fallback

## Surviving Offense Statuses

```python
_SURVIVING_STATUSES = {"live", "extended", "introduced", "unresolved"}
```

## Losing Statuses

```python
_LOSING_STATUSES = {"dropped", "conceded", "turned", "outweighed"}
```

## Speaker Points

`_estimate_speaker_points()` gives a base of 27.5 and adjusts:
- `-0.2` per legality violation
- `+0.1` for clean evidence (citation_given, warrant_explained)
- Floor 25.0, ceiling 30.0

## Rejudging

`rejudge_round(round_id, judge_type, ...)` creates a **new** `RoundDecision` with a new UUID. The original decision and the flow history are unmodified. A student can rejudge the same round under multiple judge profiles to compare outcomes.

## Decision Confidence

| Condition | Confidence |
|---|---|
| Winner has ≥ 2 more surviving voters | decisive |
| Winner has 1 more surviving voter | split |
| Scores equal, weighing difference | weighing |
| All other cases | contested |
