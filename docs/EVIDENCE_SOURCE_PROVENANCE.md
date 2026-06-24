# Evidence Source Provenance

## Provenance Chain

Every evidence card traces back through an unbroken chain:

```
Source URL
  → ExtractedDocument          (content_hash, extraction_method, timestamp)
    → DocumentSection          (start_char, end_char, page_number, heading)
      → EvidenceCandidate      (all fields above + domain, title, author)
        → PassageProvenance    (typed provenance record)
          → CardDraft          (forwarded into saved card metadata)
```

## PassageProvenance Fields

| Field | Description |
|-------|-------------|
| `source_url` | The original fetched URL |
| `canonical_url` | Canonical URL (after redirect or OG-url) |
| `document_type` | `"html"` / `"pdf"` / `"docx"` / `"text"` |
| `content_hash` | SHA-256 of parent document's `raw_text` |
| `retrieval_timestamp` | ISO-8601 UTC when fetch occurred |
| `start_char`, `end_char` | Offsets of passage in document `raw_text` |
| `page_number` | PDF page (1-based); None for HTML/DOCX |
| `section_heading` | Immediately preceding heading |
| `extraction_method` | Parser backend used |
| `source_text_type` | Full text / abstract only / partial / … |
| `raw_text_snapshot` | First 500 chars of passage (bounded excerpt) |
| `extraction_warnings` | Non-fatal quality warnings |

## Exact-Text Invariants

1. `ExtractedDocument.raw_text` is exact extraction output; never synthesized.
2. `DocumentSection.text` is a direct slice of `raw_text[start_char:end_char]`.
3. `EvidenceCandidate.text` is always exact passage text.
4. `CardDraft.body_text` is derived from an exact substring of the passage.

## Metadata Precedence

1. **Crossref** (Pass 9): highest authority for DOI-verified bibliographic fields.
   Fields verified by Crossref are never overwritten by downstream metadata.
2. **JSON-LD / schema.org**: primary web metadata source.
3. **`citation_*` meta tags**: academic article markup.
4. **OpenGraph / Dublin Core**: general web metadata.
5. **HTML `<title>`, `<meta name="author">`**: fallback.
6. **Organization heuristic**: maps known domains to institutional author names.
7. **PDF/DOCX core properties**: used for PDF/DOCX documents.

## Offset Validation

`validate_passage_offsets(document_text, passage_text, start, end)`:
- Checks `document_text[start:end].strip() == passage_text`
- Returns `(bool, error_message)`

`validate_card_body_in_document(document_text, card_body)`:
- Strips ellipsis markers (`[…]`) and verifies each span is an exact substring
- Returns `(bool, error_message)`

Offset validation failures are counted in the P10 trace
(`offset_validation_failures` field) but do not fail evidence generation.

## Page Attribution

PDF page numbers are:
- Preserved from PyMuPDF page enumeration (1-based)
- Stored on `DocumentSection.page_number`
- Forwarded to `EvidenceCandidate.page_number`
- Displayed in `SourceProvenancePanel` when non-null

Passages from separate pages are never merged (each page is one section).

## Normalized vs Raw Text

`normalized_text` exists for display only. It has whitespace collapsed but
identical content. The `raw_text` field is the authoritative source for:
- Content hashing
- Offset arithmetic
- Card body validation
- Snapshot excerpts
