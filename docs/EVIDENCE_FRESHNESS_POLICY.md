# Evidence Freshness Policy (Pass 14)

## Principle

**Age alone does not make evidence wrong.** A 2018 study on nuclear deterrence strategy is not stale. A 2022 GDP statistic may be. The freshness system classifies evidence by claim type and applies per-type windows — not a single universal threshold.

---

## Claim Type Classification

The system classifies each card's claim type using the card's `tag` (debate tag line) and first 300 characters of `body_text`. Classification is deterministic via regex patterns.

| Claim Type | Pattern keywords (simplified) |
|---|---|
| `statistics` | GDP, percent, rate, million, billion, number, count |
| `policy` | law, legislation, policy, regulation, bill, treaty, passed, enacted |
| `law` | court, ruled, decision, statute, legal, jurisdiction, held, SCOTUS |
| `science` | study, research, trial, found, evidence shows, peer-reviewed |
| `historical` | historically, during the X century, in 19XX, during the war |
| `tech` | AI, technology, software, algorithm, chip, model, deployment |
| `general` | (fallback if no pattern matches) |

---

## Freshness Windows

| Claim Type | Current (days) | Aging (days) | Stale (days) |
|---|---|---|---|
| `statistics` | ≤ 548 (1.5y) | ≤ 1095 (3y) | > 1095 |
| `policy` | ≤ 730 (2y) | ≤ 1460 (4y) | > 1460 |
| `law` | ≤ 1095 (3y) | ≤ 2190 (6y) | > 2190 |
| `science` | ≤ 730 (2y) | ≤ 1825 (5y) | > 1825 |
| `historical` | **never stale** (999,999d window) | — | — |
| `tech` | ≤ 365 (1y) | ≤ 730 (2y) | > 730 |
| `general` | ≤ 730 (2y) | ≤ 1460 (4y) | > 1460 |

---

## Freshness States (7)

| State | Meaning |
|---|---|
| `current` | Within the `current` window for claim type |
| `aging` | Past current window but not yet stale |
| `stale` | Past stale threshold for claim type |
| `superseded` | Card is stale AND `has_newer_corroboration=True` |
| `older_but_still_relevant` | Stale by time, but claim type is `historical` or `law` (per-type exception) |
| `freshness_unknown` | No `published_date` or `accessed_date` found on the card |
| `not_time_sensitive` | Classified as `historical` — time threshold not applicable |

---

## Date Parsing

The system reads `card["published_date"]` first, then `card["accessed_date"]` as fallback.

Supported formats:
- `YYYY-MM-DD` (ISO date string)
- `YYYY` (year only — treated as Jan 1 of that year)

If neither field is present or parseable, state is `freshness_unknown`.

---

## What "freshness_unknown" means for scoring

A card with `freshness_unknown` **reduces** the evidence_freshness dimension score (treated as `needs_attention`) but is **never labeled stale**. The feedback text explains the missing date and prompts the debater to verify the publication year.

---

## `has_newer_corroboration`

When assessing a batch, the caller passes a set of `newer_card_ids` (typically the set of card IDs that have a `relationship_type = "updates"` or `"stronger_source"` relationship pointing at the card being assessed). If the target card is stale and has a newer corroborating card, its state upgrades to `superseded` (not stale), which generates a more specific UI label and a different recommended action.

---

## Clock Injection

All freshness functions accept `today: date | None = None`. When `today` is None, `date.today()` is used. Tests always pass an explicit `today` to keep results deterministic regardless of when the test suite runs.

---

## Constraints

- `assess_freshness()` never raises. If the card dict is missing expected fields it returns `freshness_unknown`.
- Historical evidence is never labeled stale. "Do not treat old evidence as false solely because of age." (Pass 14 spec)
- The batch function (`assess_freshness_batch`) processes each card independently.
- Freshness state is advisory only. The UI surfaces it; the debater decides whether to act.
