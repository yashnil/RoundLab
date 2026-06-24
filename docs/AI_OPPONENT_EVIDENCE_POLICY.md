# AI Opponent Evidence Policy

## Core Constraint

The AI opponent never fabricates evidence. Every card reference in an opponent speech must come from the user's own pre-approved card set and must have passed the source verification pipeline.

## Approved Cards

Cards are pre-loaded via `POST /round-simulations/{id}/load-preparation`:
- `approved_card_ids`: list of card UUIDs the user has saved and wants to allow
- `approved_blockfile_ids`: blockfile UUIDs (frontlines included)
- `approved_frontline_ids`: frontline entry UUIDs

`_fetch_approved_cards()` verifies user_id ownership for every card before returning it. A foreign user's card is silently excluded even if its UUID is passed.

## Unusable Verdicts

Cards with these support verdicts are excluded from opponent use:

```python
_UNUSABLE_VERDICTS = {"not_supported", "contradicts", "abstract_only"}
```

`_score_card_for_opponent()` returns `-1.0` for unusable cards. They never appear in the opponent plan regardless of topicality.

## Limited Verdicts

```python
_LIMITED_VERDICTS = {"partially_supported", "abstract_only"}
```

Cards with `partially_supported` can be used but are prefixed with `[Limited]` in the opponent's claim to signal to the coach that limited use is being modeled.

## Speech Validation

After LLM generation, `_validate_speech()` checks every evidence reference in the generated speech:
- Each card ID mentioned must appear in `approved_card_ids`
- No unauthorized IDs are allowed

If validation fails, the generator retries once with an explicit constraint in the prompt. If the second attempt also fails, `_deterministic_fallback()` generates a safe speech using only analytical arguments (no evidence references at all).

## Analytical Arguments

When no approved evidence is available for a given argument, the opponent uses an analytical argument labeled `[Analytical]`. These arguments are:
- Clearly marked so debaters know they're not card-backed
- Based on standard PF debate logic without citations
- Not a source of invented statistics, studies, or authors

## What the Opponent Never Does

- Cites an author or year it didn't get from an approved card
- Uses a card the student hasn't approved
- References a study by name without a real source
- Introduces new cards in summary or final focus (same rules as the student)
