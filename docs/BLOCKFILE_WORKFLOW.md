# Blockfile Workflow

## What is a blockfile?

A blockfile is a named, organized collection of evidence cards grouped into sections. It maps to the traditional debate practice of maintaining "block files" — prepared arguments organized by opponent claim or speech position.

Example blockfile: **"Neg frontlines on Economy"**
- Section: "Direct negation" (type: `neg_case`)
  - Entry: Card — "Trade deficits have no GDP impact"
  - Entry: Card — "Manufacturing decline predates the policy"
- Section: "Turns" (type: `turns`)
  - Entry: Card — "Policy increases unemployment"
- Section: "Weighing" (type: `weighing`)
  - Frontline: "Impact comparison: jobs > GDP"

## Creating a blockfile

1. Navigate to `/library` → **Blockfiles** tab
2. Click **New Blockfile**
3. Set: title, optional resolution, side (Pro / Con / Neutral)
4. Click **Create**

The blockfile is immediately available for editing.

## Section types

| Type | Intended use |
|---|---|
| `neg_case` | Negative case blocks |
| `aff_case` | Affirmative case blocks |
| `turns` | Turns against opponent arguments |
| `impact_calc` | Impact calculus evidence |
| `framework` | Framework or theory blocks |
| `extensions` | Extensions and voters |
| `weighing` | Comparative weighing blocks |
| `counterplan` | Counterplan texts and nets |
| `misc` | Uncategorized |

## Adding entries

1. In the `BlockfileEditor`, open or create a section
2. Click **Add Card** and enter the card ID, or drag from search results
3. Entries are ordered by `position`; drag handles reorder them
4. `DELETE /library/entries/{id}` removes the entry — it does **not** delete the underlying evidence card

## Section nesting

Sections support **one level of nesting only**. A section can have a `parent_section_id` pointing to another section, but that parent cannot itself have a parent. Attempting to create a grandchild section raises:
```
ValueError: Sections support only one level of nesting
```

## Duplicating a section

`POST /library/sections/{id}/duplicate` creates a deep copy:
- New section with `(copy)` suffix in the title
- All entries copied at their current positions
- The duplicate is appended after the original

## Deleting entries vs. cards

**Important:** Deleting a blockfile entry (`DELETE /library/entries/{id}`) only removes the card from the blockfile. The underlying evidence card in `evidence_cards` is **not** touched. This lets the same card appear in multiple blockfiles without duplication of source text.

## Exporting blockfiles

Three export formats are available:

| Format | Endpoint | Use case |
|---|---|---|
| JSON | `GET /library/blockfiles/{id}/export.json` | Machine-readable, for import into other tools |
| Markdown | `GET /library/blockfiles/{id}/export.md` | Plain text, paste into Google Docs |
| DOCX | `GET /library/blockfiles/{id}/export.docx` | Tournament-ready formatted document |

All exports use `_safe_card()` which strips internal IDs, offsets, and diagnostic fields. A deduplicated bibliography is appended. See `docs/EVIDENCE_LIBRARY_EXPORTS.md` for format details.

## Templates

Blockfiles can be marked `is_template = True`. Template blockfiles are read-only and can be duplicated into a new personal blockfile. (Template creation is an admin-only action; no public endpoint in MVP.)
