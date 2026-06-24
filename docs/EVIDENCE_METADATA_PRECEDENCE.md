# Evidence Metadata Precedence (Pass 12)

## Confidence tiers

| Tier | Rank | Examples |
|---|---|---|
| `verified` | 4 | User edit; Crossref DOI-confirmed data |
| `high` | 3 | OpenAlex; Semantic Scholar; JSON-LD; citation meta tag |
| `medium` | 2 | PDF parser; DOCX parser; OpenGraph; provider metadata; visible page text |
| `low` | 1 | URL-based inference; domain inference |
| `unknown` | 0 | No source; not detected |

## Merge rules

1. **A field is only replaced when the incoming confidence is strictly higher.**
   Equal confidence does not overwrite.
2. **Empty fields may always be enriched from any source.**
3. **When two non-empty values conflict at similar confidence, a CitationConflict
   is recorded** but the higher-confidence value (or existing value if same tier)
   is retained.
4. **Organization names are never split into fake person names.**
   A name containing "Institute", "University", "Department", etc. is stored
   as `CitationPerson(literal=name, is_organization=True)`.
5. **DOI and URL are normalized before comparison.**
6. **Dates retain the finest precision available.**  Year-only overrides nothing
   when a full date is already known.
7. **User edits always win** (`confidence=verified`, `manually_edited=True`).
   No subsequent merge step may overwrite a user-edited field.

## Precedence order

Higher position → higher precedence:

1. User-confirmed value (confidence = verified, manually_edited = True)
2. Crossref DOI-verified metadata (confidence = verified)
3. OpenAlex / Semantic Scholar (confidence = high)
4. JSON-LD structured metadata (confidence = high)
5. Citation meta tags (`<meta name="citation_author" ...>`) (confidence = high)
6. PDF parser metadata (confidence = medium)
7. DOCX parser metadata (confidence = medium)
8. OpenGraph metadata (`og:title`, `og:site_name`) (confidence = medium)
9. Search provider metadata (confidence = medium)
10. Visible page text extraction (confidence = medium)
11. URL path inference (volume, year from URL pattern) (confidence = low)
12. Domain label inference (publication name from domain map) (confidence = low)

## Conflict detection rules

Conflicts are recorded when two non-empty values from different sources materially
differ AND one source does not clearly dominate the other.

| Field | Conflict condition |
|---|---|
| `title` | Fewer than 50% of 4+ character words overlap |
| `container_title` | Same as title |
| `year` / `doi` | Any non-matching string value |
| `authors` | Surnames share no overlap between lists |

Minor wording differences, punctuation, and case differences do not produce conflicts.

## What does NOT trigger a conflict

- Crossref title differs only in capitalization or punctuation
- Year differs because one source only has decade ("2020s") vs specific year
- Author middle initials present in one source but not another
- Publisher vs container title confusion on a record where both are plausible

## Conflict resolution

When a conflict is recorded:
- The **higher-confidence source wins** and sets the field value.
- The lower-confidence conflicting value is stored in `CitationConflict.conflicting_value`.
- A human-readable `message` is generated (shown in `CitationDetailsPanel`).
- No automatic correction is applied.
- The user may inspect and correct using the inline field editor.

## Source type inference

Source type is inferred **conservatively**:

- Not every PDF is classified as "report" — it defaults to `document` unless the
  domain is `.gov` or the URL contains thesis-related terms.
- Not every webpage is classified as "news" — it requires clear journal/newspaper
  container title signals.
- `crossref_type` from the Crossref API always wins over heuristic inference.
- When uncertain, use `document` and record a low-confidence note.
