# Crossfire Simulation

## Overview

During crossfire phases, the AI generates a targeted question against a live flow argument and the student responds in text. The system analyzes responses for concessions, contradictions, and evasions.

## Question Generation

`generate_crossfire_question(round_id, phase, config, live_args)`:
1. Selects target argument: prefers opponent's live/extended arguments
2. Calls LLM with a concise JSON prompt requesting one question (max 30 words)
3. Falls back to `_fallback_question()` if LLM fails or returns empty string
4. Stores as `CrossfireExchange` with `status="pending_student_answer"`

## Student Answer Processing

`process_crossfire_response(exchange_id, student_answer)`:
- **Concession detection**: checks for patterns like "I'll admit", "you're right", "that's fair", "I grant"
- **Contradiction detection**: checks for direct negation ("not true", "wrong", "actually")
- **Evasion detection**: checks for dodge patterns ("that's not what this is about", "irrelevant", "moving on")

Results are stored on the `CrossfireExchange` record. Concessions can later be cited in the decision engine as "decisive_concessions".

## No New Evidence Rule

Neither the AI nor the student can introduce new evidence in crossfire. The system:
- Does not search for sources during crossfire question generation
- `check_crossfire()` in `speech_legality_checker.py` flags any new citation language in student answers
- AI questions reference only already-introduced arguments, never new cards

## Exchange Types

```
targeted_question    Challenges a specific argument
clarification        Asks for clarification on evidence or claim
concession_trap      Tries to extract a concession
follow_up            Follows up on a previous answer
```

## Evasion Patterns

The system detects these evasion signals in student answers:
- "that's not what [this/the argument] is about"
- "you're mischaracterizing"
- "irrelevant"
- "moving on" / "next"
- "I'll get back to that"
- "not applicable here"
