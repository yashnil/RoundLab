# Evidence Library Architecture

## Overview

The Evidence Library turns saved evidence cards into an organized, reusable research system. Cards are tagged by resolution, argument, and side; grouped into blockfiles; and connected via a typed relationship graph. All data is user-scoped with team-read support.

## Entity hierarchy

```
Resolution
└── Argument (belongs to a resolution + side)
    └── LibraryCardMetadata (one-to-one with evidence_cards)

EvidenceSource (deduplicated by DOI or canonical URL)
└── evidence_cards (each card references one source)

Blockfile (belongs to a user, optionally a resolution + side)
└── BlockfileSection (ordered, one level of nesting)
    └── BlockfileEntry (ordered cards within a section)
    └── Frontline (attached to a section)
        └── FrontlineResponse (ordered responses to a frontline)

CardRelationship (directed or undirected link between two cards)
CardVersion (audit history for a single card)
```

## Database tables (Pass 13)

| Table | Key columns | Notes |
|---|---|---|
| `resolutions` | id, user_id, title, season, is_active | Soft-delete via is_active |
| `arguments` | id, user_id, resolution_id, title, side, argument_type | side: pro/con/neutral |
| `evidence_sources` | id, normalized_doi, canonical_url, content_hash | Deduped by sparse unique indexes |
| `library_card_metadata` | card_id UNIQUE, resolution_id, argument_id, side, tags[], notes, status | One-to-one extension of evidence_cards |
| `blockfiles` | id, user_id, resolution_id, title, side, is_template | |
| `blockfile_sections` | id, blockfile_id, parent_section_id, title, section_type, position | Max 1 level of nesting |
| `blockfile_entries` | id, section_id, card_id, position | Deleting an entry does NOT delete the card |
| `frontlines` | id, section_id, user_id, opponent_claim/warrant/impact | Attached to blockfile sections |
| `frontline_responses` | id, frontline_id, response_type, response_claim, priority, speech_suitability[], is_analytical | |
| `card_relationships` | id, card_id_a, card_id_b, relationship_type, is_confirmed, auto_confirmed | Suggestions start unconfirmed |
| `card_versions` | id, card_id, version_number, changed_fields[], previous_values JSONB | Protected fields never stored in previous_values |

## Source deduplication

`evidence_sources` uses sparse unique indexes instead of a `NULLS NOT DISTINCT` unique constraint (for Postgres ≤14 compat):

```sql
CREATE UNIQUE INDEX evidence_sources_doi_idx
    ON evidence_sources (normalized_doi) WHERE normalized_doi IS NOT NULL;

CREATE UNIQUE INDEX evidence_sources_url_hash_idx
    ON evidence_sources (canonical_url, content_hash)
    WHERE canonical_url IS NOT NULL AND content_hash IS NOT NULL;
```

`find_or_create_source()` checks DOI first, then URL+hash, then inserts if neither match is found. Multiple cards from the same article share one source row.

## Service layer

```
backend/app/services/
  evidence_library_service.py   — CRUD, ownership checks, version recording
  library_export.py             — JSON / Markdown / DOCX export
```

`evidence_library_service.py` responsibilities:
- `_require_owner(table, row_id, user_id)` — raises `PermissionError` if caller doesn't own the row
- `save_card_to_library()` — raises `ValueError` for `unsupported`/`contradicted` unless `unsupported_save_override=True`
- `restore_version()` — skips protected fields: `body_text`, `highlighted_spans_json`, `underline_spans_json`, `support_verdict`
- `suggest_relationships_for_card()` — deterministic only (same source_id); always returns `auto_confirmed: False`
- `_check_section_nesting()` — enforces max 1 level of nesting

## API surface

All endpoints are under `/library` prefix (see `backend/app/api/evidence_library.py`).

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/library/resolutions` | List / create resolutions |
| GET/PUT/DELETE | `/library/resolutions/{id}` | Read / update / delete |
| GET/POST | `/library/arguments` | List / create arguments |
| POST | `/library/cards/save` | Save card to library with metadata |
| POST | `/library/search` | Full-text + filter search across library |
| GET/POST | `/library/blockfiles` | List / create blockfiles |
| POST | `/library/sections/{id}/duplicate` | Duplicate a section |
| POST | `/library/cards/{id}/find-related` | Returns search instructions for related cards |
| POST | `/library/cards/{id}/relationships/confirm` | Confirm a suggested relationship |
| GET | `/library/cards/{id}/versions` | Version history |
| POST | `/library/cards/{id}/versions/{v}/restore` | Restore to version |
| GET | `/library/blockfiles/{id}/export.json` | JSON export |
| GET | `/library/blockfiles/{id}/export.md` | Markdown export |
| GET | `/library/blockfiles/{id}/export.docx` | DOCX export |

## Frontend

```
frontend/src/
  app/library/page.tsx                       — Three-tab page (cards / blockfiles / frontlines)
  types/library.ts                           — TypeScript interfaces
  components/library/
    SaveToLibraryDialog.tsx                  — Resolve/arg/side/tag picker + weak-card guard
    BlockfileEditor.tsx                      — Section/entry CRUD with reorder
    FrontlineBuilder.tsx                     — Opponent claim + responses UI
    CardRelationshipPanel.tsx                — Confirmed + suggested relationships
    CardVersionHistory.tsx                   — Reversed list + restore with confirm()
```

The library page is accessible at `/library` and is listed in the Research group of the sidebar (`lib/navItems.ts`).
