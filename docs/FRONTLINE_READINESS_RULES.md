# Frontline Readiness Rules (Pass 14)

## Purpose

The frontline readiness analyzer classifies each frontline as one of four readiness levels, then surfaces the most important missing element.

---

## Readiness Levels (4)

| Level | Meaning |
|---|---|
| `ready` | Frontline has adequate response coverage, at least one evidence card, and no unsafe cards. |
| `usable_with_gaps` | Frontline has a defensible response but is missing some elements (e.g., no evidence, no turn). |
| `underdeveloped` | Frontline has fewer than 2 responses, or no evidence at all, or missing a direct answer. |
| `unsafe` | Linked evidence has an `unsupported` support verdict — running this frontline in round is risky. |

---

## Analysis Dimensions (boolean flags)

Each `FrontlineReadinessResult` captures:

| Flag | How it is set |
|---|---|
| `has_direct_answer` | At least one response with `response_type` in `[direct_refutation, turn]` |
| `has_defensive_coverage` | At least one response with type in `[impact_defense, non_unique, straight_turn, no_link, block]` |
| `has_offensive_option` | At least one `turn` or `concede_and_turn` response |
| `has_evidence` | At least one evidence card linked to any response |
| `has_multiple_responses` | `len(responses) >= 2` |
| `has_summary_suitability` | At least one response notes `speech_suitability` contains "summary" |
| `has_final_focus_suitability` | At least one response notes `speech_suitability` contains "final focus" |
| `has_analytical_response` | At least one `analytical` type response |
| `has_ordering` | `frontline.response_ordering` is not None/empty |
| `missing_direct_answer` | `not has_direct_answer` |
| `missing_evidence` | `not has_evidence` |
| `all_evidence_stale` | Every linked card's ID is in the `stale_card_ids` set |
| `has_unsafe_cards` | Any linked card has `support_verdict == "unsupported"` |
| `response_count` | Total number of responses |
| `evidence_count` | Total number of unique linked cards |

---

## Classification Rules

Rules evaluated in order (first match wins):

1. **`unsafe`**: `has_unsafe_cards == True`
2. **`underdeveloped`**: `response_count < 2` OR `missing_direct_answer` OR `missing_evidence`
3. **`ready`**: `has_evidence` AND `has_direct_answer` AND `has_defensive_coverage` AND NOT `all_evidence_stale` AND NOT `has_unsafe_cards`
4. **`usable_with_gaps`**: everything else (has some responses and some evidence but gaps exist)

---

## Offensive Option Policy

`has_offensive_option` is checked and surfaced in the readiness result, but **a frontline without a turn is still valid**. A `ready` frontline does not require a turn.

The reasoning: in novice/JV PF, a clean defensive frontline with a direct refutation is fully competition-ready. Requiring a turn would unfairly penalize novice debaters with sound defense.

---

## `top_missing` Field

`_identify_top_missing()` returns the single most important missing element as a short string:

| Priority | Condition | Message |
|---|---|---|
| 1 | `has_unsafe_cards` | "Linked evidence has unsupported verdict" |
| 2 | `missing_direct_answer` | "No direct answer to this argument" |
| 3 | `missing_evidence` | "No evidence cards linked" |
| 4 | `response_count < 2` | "Only 1 response — add at least one more" |
| 5 | `not has_defensive_coverage` | "No defensive coverage" |
| 6 | `all_evidence_stale` | "All linked evidence is stale" |
| 7 | `not has_offensive_option` | "No offensive option (turn)" |

---

## Stale Card Detection

The caller passes `stale_card_ids: set[str]` — a set of card IDs that the freshness assessor flagged as `stale` or `superseded`. The analyzer checks `all_evidence_stale` only when `evidence_count > 0` and all evidence card IDs appear in `stale_card_ids`.

---

## API

```
POST /prep/frontline-readiness/{frontline_id}?user_id=<uid>
→ { readiness: FrontlineReadiness, result: FrontlineReadinessResult, top_missing: str | null }
```
