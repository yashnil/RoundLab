# Round Flow Rules

## Append-Only Event Log

`round_flow_events` is an insert-only table. Argument statuses are never stored directly — they are derived by replaying the event log through `reconstruct_flow_status()`.

## Argument Status Transitions

`apply_event(current_status, event_type)` is a pure function with no DB access:

| Event | From status | To status |
|---|---|---|
| introduce | (any) | introduced |
| answer | introduced, extended, live | answered |
| extend | introduced, answered, live | extended |
| drop | introduced, live, answered | dropped |
| turn | introduced, live | turned |
| concede | live, answered, extended | conceded |
| indict | extended | mitigated |
| mitigate | answered, live | mitigated |
| weigh_against | live | outweighed |
| late_intro | (any) | new_in_late_speech |
| unresolved_marker | (any) | unresolved |

Unknown event types or unknown statuses return the current status unchanged.

## Valid Argument Statuses

```
introduced → answered → extended → dropped → turned → conceded
underextended → mitigated → outweighed → new_in_late_speech → unresolved → live
```

## Label Extraction

`_extract_argument_labels(transcript)` uses regex to find:
- `AC1`, `AC2`, `AC3` (pro constructive arguments)
- `NC1`, `NC2`, `NC3` (con constructive arguments)
- `Contention 1`, `Contention 2`

## Extension Detection

`_extract_extensions(transcript, known_labels)` matches:
- `"extend [label]"` / `"extend our [label]"`
- `"[label] still stands"` / `"[label] stands uncontested"`
- `"[label] goes unanswered"` / `"[label] goes uncontested"`
- `"across the flow on [label]"`

## Drop Detection

`_detect_drops()` flags opponent arguments as dropped when:
- The argument is `live` or `extended` in the previous phase
- The student's speech does not mention the argument label

## Reconstruction

`reconstruct_flow_status(events)` replays events in chronological order. It returns a `Dict[str, ArgumentFlowStatus]` keyed by argument label.

## Late-Phase New Arguments

`is_new_argument_legal(phase, practice_override)` returns `False` for any phase in `LATE_PHASES_NO_NEW_ARGS`. A violation is stored as a `SpeechLegalityViolation` with `severity="illegal"` (not a block — it's surfaced in coaching feedback).
