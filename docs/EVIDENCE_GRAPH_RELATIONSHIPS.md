# Evidence Graph Relationships

## Overview

Cards in the Evidence Library can be connected to each other via typed, directed relationships. Relationships help debaters understand how cards reinforce each other, which cards a judge might find contradictory, and what evidence to pair in speeches.

## Relationship types

| Type | Meaning |
|---|---|
| `supports` | Card A strengthens the claim made by Card B |
| `contradicts` | Card A conflicts with Card B's claim or finding |
| `updates` | Card A is a more recent finding that supersedes Card B |
| `same_finding` | A and B report the same result from different sources |
| `stronger_version` | A makes the same argument more forcefully than B |
| `impact_evidence` | A provides the impact magnitude for B's mechanism |
| `mechanism_evidence` | A explains the causal mechanism behind B's claim |
| `application` | A is a concrete example/application of B's general claim |
| `extends` | A adds an additional dimension or time period to B's claim |
| `answers` | A directly answers or responds to B's claim |
| `pairs_with` | A and B are commonly read together in a speech |

## Suggestion vs. confirmation

Relationship suggestions are **never auto-confirmed**. `suggest_relationships_for_card()` only uses deterministic logic (currently: two cards with the same `source_id` are flagged as `same_finding`). The result always carries `auto_confirmed: False`.

To activate a suggestion, the user must explicitly call `POST /library/cards/{id}/relationships/confirm` with the `relationship_id`. Only then does the relationship become visible in the confirmed panel.

This prevents the library from being polluted by low-confidence machine suggestions.

## Directionality

Most relationships are asymmetric (`card_id_a → card_id_b`). When displaying a card's relationships, the UI loads both directions:

```
GET /library/cards/{id}/relationships
→ { outgoing: [...], incoming: [...], suggestions: [...] }
```

`pairs_with` and `same_finding` are treated as symmetric in the UI even though the DB stores a direction.

## Data model

```python
class CardRelationshipRow(BaseModel):
    id: str
    card_id_a: str
    card_id_b: str
    relationship_type: RelationshipType
    user_id: str
    notes: str | None
    is_confirmed: bool
    auto_confirmed: bool       # always False for suggestions
    created_at: datetime
```

## Frontend: CardRelationshipPanel

`CardRelationshipPanel` (`components/library/CardRelationshipPanel.tsx`):
- Loads relationships and suggestions on mount
- Confirmed relationships are shown first
- Each suggestion has a "Confirm" button that calls the confirm endpoint — no auto-confirm
- Users can add a manual relationship via a type-select + target-card picker

## "Find related evidence"

`POST /library/cards/{id}/find-related` does **not** run a new AI pipeline. It maps the card's `action` enum to a search claim string and returns search instructions that the frontend can pass to the existing `POST /research/generate-cards` endpoint. This reuses the existing evidence retrieval pipeline without duplicating it.
