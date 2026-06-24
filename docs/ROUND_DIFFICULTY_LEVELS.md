# Round Difficulty Levels — Pass 17

## Overview

Difficulty affects the opponent's strategy, speech goals, and collapse plan — not the factual content of evidence. A harder opponent does more with the same cards, not different cards.

## Levels

| Level | Description | Max Args | Strategy |
|-------|-------------|----------|----------|
| NOVICE | Simple, beginner-friendly | 1–2 | One main argument, clear impact, no turns |
| JV | Moderate, covers basics | 2–3 | 2 arguments, frontline responses, collapse path |
| VARSITY | Advanced, competitive | 3–4 | Turns, preemptive responses, specific weighing |

## What Changes by Difficulty

| Feature | NOVICE | JV | VARSITY |
|---------|--------|-----|---------|
| Argument count | 1–2 | 2–3 | 3–4 |
| Speech goals | Simple offense | Full case | Strategic turns |
| Weighing strategy | Simple impact comparison | Comparative | Specific dimensions (magnitude/timeframe) |
| Planned collapse | First arg | Extended arg | Best-weighted arg |
| Follow-up questions | Rarely | Sometimes | Aggressively |

## What Does NOT Change by Difficulty

- Evidence content (never fabricated or altered)
- Card citation format
- Whether evidence is used (only approved cards)
- Judge profile adaptation (separate from difficulty)

## Implementation

`get_difficulty_params(difficulty)` in `opponent_strategy.py` returns:
```python
{
    "max_arguments": int,
    "speech_goals": List[str],
    "weighing_detail": str,  # "simple" | "comparative" | "specific"
}
```

## Constraints (from Pass 17 spec)

- "Do not change factual evidence for difficulty or judge type."
- Difficulty only affects *what arguments the opponent develops* and *how it speaks*, not *what the cards say*.
