# Evidence Legacy Citation Migration (Pass 12)

## What changed

Before Pass 12, all citation data was stored as a flat `CitationMetadata` object
with a pre-rendered `mla_citation` string and a `short_cite` string.

Pass 12 introduces `CitationRecord` as the structured internal model.  The old
format is preserved for backward compatibility.

## Migration behavior

### New cards (after Pass 12)

`enrich_citation_metadata()` now also calls `build_citation_record()` and
`attach_rendered()`, then assigns the result to `citation.citation_record`.

The rendered outputs in CitationRecord (MLA, APA, Chicago, BibTeX, RIS, debate)
are computed from the structured CitationRecord — they may differ slightly from
the pre-Pass 12 `mla_citation` string.

The legacy `mla_citation` field remains populated for backward compatibility.

### Legacy cards (before Pass 12)

Legacy `CardDraftRow` and `CitationMetadata` objects without `citation_record`
continue to work everywhere:

- Frontend `CitationDetailsPanel` renders `legacyMla` when `record` is absent.
- All existing citation display components use `mla_citation` and `short_cite`
  directly — no change required.
- No automatic migration of existing saved cards.

### Reading a legacy CitationMetadata as CitationRecord

`from_legacy_citation_metadata(legacy)` in `citation_normalizer.py` converts
a `CitationMetadata` object to a partial `CitationRecord`:

- Authors: parsed from `legacy.authors` list or `author_display` string.
- Year: parsed from `legacy.year` string.
- Title, container_title, publisher from corresponding legacy fields.
- DOI from `legacy.doi`.
- URL from `legacy.url`.
- Provenance: uses the four `*_source` string fields to set confidence.
- Rendered strings: NOT populated (only available after `attach_rendered()`).

This is a read-only migration helper — it does not modify the saved card.

## What is NOT changed

- Evidence body text (never rewritten)
- Tag
- Source offsets
- Page/section provenance
- Support verdict (Pass 11)
- Content hash
- Source snapshot
- Existing `mla_citation` string (preserved as-is; not overwritten by new renderer)

## Database schema

No new database columns are added in Pass 12.  The `citation_record` is stored
as part of the `draft_json` blob when a card is saved:

```json
{
  "citation_record": {
    "source_type": "article-journal",
    "title": "...",
    "authors": [{"given": "Jane", "family": "Smith", ...}],
    ...
  }
}
```

Legacy cards that do not have `citation_record` in `draft_json` simply return
`None` for the `citation_record` field — no migration query needed.

## Rendering differences

The Pass 12 MLA renderer follows MLA 9th edition more closely than the original
`enrich_citation_metadata` string builder:

| Case | Legacy | Pass 12 |
|---|---|---|
| Book title | No italics marker | `*Title*` (plaintext asterisks) |
| Vol/issue | `vol. 3, no. 2` | Same |
| MLA month | Not included | Month abbreviation included |
| Author format | Surname only | `Last, First` for first author |
| No author | Omits field | Uses "Accessed DATE." |

The `short_cite` and `mla_citation` fields on `CitationMetadata` are NOT updated
by Pass 12 — they retain the pre-Pass 12 format.  The structured renderers are
accessed via `CitationRecord.rendered_*`.

## Legal and government source limitations

Legal cases and statutes have specialized citation formats (Bluebook, etc.) not
fully implemented in Pass 12's deterministic renderers.  These sources:

- Get `source_type = "legal_case"` or `"legislation"` when detected
- Render MLA and APA with best-effort using available fields
- Do not render Bluebook or jurisdiction-specific formats
- Mark completeness as `usable_with_warnings` when docket/court are available

Full legal citation support is deferred to a future pass.
