# Multi-Turn Crossfire — Pass 17

## Overview

The crossfire simulator was upgraded in Pass 17 to support:
- Question diversity (no repeating targets)
- Follow-up generation when an answer is evasive
- AI opponent answers to student questions
- Evasion detection via concession_detector

## Architecture

```
crossfire_simulator.py
  ├── generate_crossfire_question()    — main entry point (unchanged signature)
  ├── generate_followup_question()     — NEW: follow-up when evasion detected
  ├── generate_ai_answer()             — NEW: AI answers student questions
  └── process_crossfire_response()     — upgraded with concession_detector
```

## Question Diversity

- Tracks which argument labels have been targeted in prior exchanges
- Rotates through live → extended → introduced → other
- Deduplicates via `_normalize_question()` (lowercase + stopword removal)

## Follow-Up Detection

`generate_followup_question(prior_exchange, questioner_side, live_args, judge_type)`:
- Called when `prior_exchange.evasion_detected == True`
- References the original question and what was not answered
- Must not introduce new evidence
- Returns a `CrossfireExchange` object

## AI Answers to Student Questions

`generate_ai_answer(question, opponent_side, live_args, prior_exchanges, config)`:
- AI opponent answers student-initiated questions
- Consistent with prior opponent speeches
- Max 2 sentences for crossfire
- Uses `detect_concessions()` to note if student question forced a partial concession

## Evasion Detection

An answer is evasive if:
- `concession_detector.detect_concessions()` returns a finding with `type == "evasion"`, OR
- Answer is < 20 words and does not contain a direct yes/no/agreement

## Constraints

- No new evidence introduced during crossfire
- Bounded turns per crossfire phase (max set by `exchange_type` limits)
- Follow-ups only generated once per exchange chain
