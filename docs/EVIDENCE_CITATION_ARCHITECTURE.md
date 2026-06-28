# Evidence Citation Architecture (Pass 12)

## Overview

Pass 12 introduces `CitationRecord` as the canonical internal representation for
all evidence card citations.  Rendered strings (MLA, APA, Chicago, BibTeX, RIS,
CSL-JSON, debate) are derived from this record; they are never stored as the
source of truth.

## Components

### CitationRecord (`app/models/citation.py`)

The normalized citation model.  Fields are grouped as:

| Group | Fields |
|---|---|
| Identity | `source_type`, `source_type_confidence` |
| People | `authors[]`, `editors[]`, `authors_prov` |
| Titles | `title`, `title_prov`, `container_title`, `container_title_prov`, `collection_title` |
| Publication | `publisher`, `publisher_prov`, `publisher_place`, `edition` |
| Issue | `volume`, `issue`, `page`, `article_number` |
| Dates | `issued` (CitationDate), `issued_prov`, `accessed` |
| Identifiers | `doi`, `doi_prov`, `url`, `url_prov`, `canonical_url` |
| Legal/gov | `court`, `case_name`, `docket_number`, `legislation_title`, `section`, `institution`, `report_number`, `jurisdiction` |
| Language | `language` |
| Quality | `completeness`, `conflicts[]`, `warnings[]`, `citation_version` |
| Rendered cache | `rendered_debate`, `rendered_mla`, `rendered_apa`, `rendered_chicago`, `rendered_bibtex`, `rendered_ris` |

Each key field carries a `_prov` sibling (`FieldProvenance`) that records:
- `source` — where the value came from
- `confidence` — tier (verified/high/medium/low/unknown)
- `manually_edited` — True when user explicitly changed this field
- `warning` — any anomaly about this field

### Citation normalizer (`app/services/citation_normalizer.py`)

`build_citation_record(...)` converts raw metadata inputs into a CitationRecord
with provenance.  Key functions:

- `normalize_doi(doi)` — strips URL prefixes, lowercases prefix
- `normalize_url(url)` — strips tracking parameters (utm_*, fbclid, etc.)
- `parse_person(raw)` — converts "Last, First" or "First Last" to CitationPerson
- `parse_authors(raw)` — splits multi-author strings on `; and &`
- `infer_source_type(...)` — conservative type inference from URL/domain/container title
- `merge_crossref(record, crossref_data)` — applies Crossref API data with verified confidence
- `merge_structured_metadata(record, data, source)` — applies any metadata dict with precedence
- `apply_user_edit(record, field, value)` — always wins; marks field as manually_edited
- `validate_completeness(record)` — sets completeness state per source type rules
- `from_legacy_citation_metadata(legacy)` — creates a partial CitationRecord from existing CitationMetadata

### Citation renderers (`app/services/citation_renderers.py`)

Deterministic renderer functions — no external library required.

| Function | Output |
|---|---|
| `render_debate(record)` | Dissio compact debate citation |
| `render_mla(record)` | MLA 9th edition string |
| `render_apa(record)` | APA 7th edition string |
| `render_chicago(record)` | Chicago 17th author-date string |
| `render_bibtex(record)` | BibTeX entry |
| `render_ris(record)` | RIS format |
| `render_csl_json(record)` | CSL-JSON dict |
| `render_all(record)` | Dict of all formats |
| `attach_rendered(record)` | Computes all and caches on record |
| `citation_key(record)` | Deterministic BibTeX key (surname+year+title_word) |
| `export_bibliography(records, fmt)` | Deduplicated bibliography, duplicate DOIs collapsed |

The renderers are optional — if an import fails, `enrich_citation_metadata`
catches the exception and continues without attaching a CitationRecord.

### Backend integration (`app/services/card_cutting.py`)

`enrich_citation_metadata()` now builds a CitationRecord alongside the existing
`CitationMetadata` and attaches it as `citation.citation_record`.  Backward
compatibility is preserved: the original `mla_citation`, `short_cite`, and
`citation_quality` fields remain.

### Frontend (`CitationDetailsPanel.tsx`)

Collapsible panel showing:
1. Completeness badge
2. Conflict count
3. Format selector (Debate / MLA / APA / Chicago / BibTeX / RIS / CSL-JSON)
4. Rendered citation with copy button
5. Download button for BibTeX / RIS / CSL-JSON
6. Field rows with provenance badges (source + confidence)
7. Inline field editing (marks field as user_edit)
8. Advanced metadata collapse (volume, issue, pages, institution, legal fields)

## CitationPerson schema

```json
{
  "given": "Jane A.",
  "family": "Smith",
  "literal": "",
  "suffix": "",
  "is_organization": false
}
```

Organization authors use `literal` and set `is_organization: true`.  They are
never split into fake given/family names.

## CitationDate schema

```json
{
  "year": 2024,
  "month": 3,
  "day": null
}
```

Year/month/day precision is retained as known.  `month` and `day` may be null.

## FieldProvenance schema

```json
{
  "source": "crossref",
  "confidence": "verified",
  "manually_edited": false,
  "warning": ""
}
```

## Backward compatibility

- Legacy `CitationMetadata` (no `citation_record`) continues to work everywhere.
- `mla_citation`, `short_cite`, and `citation_quality` remain on `CitationMetadata`.
- Frontend `CitationDetailsPanel` shows a plain MLA string for legacy cards.
- New cards built via `enrich_citation_metadata` carry a `citation_record`.
- The `CardDraftRow` has an optional `citation_record` field.
