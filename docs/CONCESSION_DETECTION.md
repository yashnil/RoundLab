# Concession Detection — Pass 17

## Overview

`concession_detector.py` replaces simple keyword matching with a structured multi-type detector. Not every polite phrase is a concession — confidence levels and `requires_confirmation` distinguish strong signals from noise.

## Detection Types

| Type | Example | Confidence | Requires Confirmation |
|------|---------|------------|----------------------|
| `explicit` | "I concede that point" | high | No |
| `partial` | "To some extent that's true" | medium | No |
| `qualified` | "That's fair, but..." | medium | Yes |
| `evasion` | "I'll address that later" | medium | Yes |
| `agreement_on_fact` | "Yes, 2020 data shows X" | medium | Yes |
| `non_concession_agreement` | "That's a good question" | low | Yes |

## Priority Order (checked in order)

1. Explicit concession patterns (checked FIRST — highest priority)
2. Word-count evasion (< 15 words, no direct stance)
3. Qualified concessions (polite phrase + pivot word)
4. Partial concessions
5. Fact-level agreements
6. Non-concession polite acknowledgments

## Critical Rule

`"That's fair"` alone, `"That's a good question"`, `"I see your point"` — all `non_concession_agreement`, confidence=low. These MUST NOT generate high-confidence flow events without human confirmation.

## API

```python
findings = detect_concessions(
    answer_text: str,
    speaker_side: str,
    target_argument_label: Optional[str],
    prior_positions: List[str],
) -> List[ConcessionFinding]

result = detect_contradiction(
    new_statement: str,
    prior_statements: List[str],
    argument_label: Optional[str],
) -> Optional[ConcessionFinding]
```

## ConcessionFinding Fields

- `type` — one of the types above
- `speaker_side` — "pro" or "con"
- `confidence` — "high", "medium", "low"
- `requires_confirmation` — whether a human should verify before updating the flow
- `strategic_effect` — human-readable explanation for the coach/student
- `transcript_span` — the exact text that triggered the detection
