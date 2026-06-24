# Evidence Extraction Architecture

## Overview

Every URL that enters the Evidence Studio pipeline is processed through a
four-stage extraction chain:

```
URL / raw bytes
  → evidence_extraction_router.py   route_extraction()
  → appropriate extractor
       evidence_web_extractor.py    HTML  (Trafilatura → BS4 fallback)
       evidence_pdf_extractor.py    PDF   (PyMuPDF)
       evidence_docx_extractor.py   DOCX  (python-docx)
  → ExtractedDocument               shared typed model
  → evidence_passage_builder.py     build_passages_from_document()
  → EvidenceCandidate[]             with page/section provenance
```

## Parser Routing

`route_extraction(url, content_type=, first_bytes=)` returns one of:
`"html"`, `"pdf"`, `"docx"`, `"text"`, `"unknown"`.

Priority (first match wins):
1. HTTP `Content-Type` header from the response
2. File extension in the URL path (`.pdf`, `.docx`, `.html`, `.txt`, …)
3. Magic bytes from the first 8 bytes of the response body
4. Default: `"html"` (the most common document type)

## ExtractedDocument Model

All extractors produce an `ExtractedDocument` dataclass:

| Field | Description |
|-------|-------------|
| `source_url` | URL that was fetched |
| `canonical_url` | After redirect / OG-url / HTTP Link header |
| `document_type` | `"html"` \| `"pdf"` \| `"docx"` \| `"text"` |
| `raw_text` | **Exact, immutable extraction output** |
| `normalized_text` | Whitespace-collapsed for display only |
| `sections` | `list[DocumentSection]` with per-section offsets |
| `extraction_method` | `"trafilatura"` \| `"pymupdf"` \| `"python_docx"` \| … |
| `content_hash` | SHA-256 of `raw_text` |
| `source_text_type` | See Source-Text Classification below |
| `extraction_warnings` | List of non-fatal quality warnings |
| `metadata_provenance` | Maps field name → extraction source |

`DocumentSection` fields:
- `text`: exact section text (direct slice of `raw_text`)
- `start_char`, `end_char`: stable offsets into `raw_text`
- `page_number`: 1-based PDF page number (None for HTML/DOCX)
- `heading`: immediately preceding heading
- `paragraph_index`, `section_index`

## Source-Text Classification

| Type | Meaning |
|------|---------|
| `full_text` | Complete body text extracted |
| `abstract_only` | Only abstract available (academic provider record) |
| `partial_extraction` | Extraction succeeded but may be incomplete |
| `snippet_only` | Only a short search snippet available |
| `metadata_only` | No usable text; title/authors/date only |

**Invariants:**
- `metadata_only` records never reach card cutting
- `snippet_only` records never become evidence cards
- `abstract_only` cards may proceed but are explicitly labeled

## Web Extraction (HTML)

The existing `extract_article()` pipeline is preserved intact:
1. Fetch URL with SSRF validation
2. Trafilatura (primary, confidence 0.85)
3. BeautifulSoup paragraph-based fallback (confidence 0.40–0.55)
4. Optional Firecrawl fallback when configured
5. `article_to_document()` wraps `ExtractedArticle` in `ExtractedDocument`

Metadata cascade (all prior to JSON-LD winning):
JSON-LD → `citation_*` meta → OpenGraph → DC meta → organization heuristic

## PDF Extraction

`evidence_pdf_extractor.extract_pdf(source_bytes_or_path)`:
- Uses PyMuPDF (`fitz`), already in `requirements.txt`
- Page-by-page extraction; each page becomes one `DocumentSection`
- Scanned/image PDF detection: if fewer than half of sampled pages
  produce ≥50 chars, a warning is emitted and no text is returned
- Max 50 pages extracted (configurable via `_MAX_PAGES`)
- Password-protected PDFs fail gracefully with a warning

## DOCX Extraction

`evidence_docx_extractor.extract_docx(source_bytes_or_path)`:
- Uses python-docx, already in `requirements.txt`
- Each paragraph becomes one `DocumentSection`
- Heading paragraphs (Heading 1–6, Title, Subtitle) become `section.heading`
  on the immediately following content section
- Bold/italic/underline run metadata preserved in `parser_metadata`
- Core properties (title, author, created date) extracted when available

## Pass 8 Integration

`build_passages_from_document(document)` is the section-aware upgrade to
`build_passages(text)`:
- When `document.sections` is populated (PDF/DOCX), each section maps to
  a passage candidate preserving `page_number`, `section_heading`, `paragraph_index`
- Falls back to `build_passages(document.raw_text)` for plain HTML
- Oversized sections are split at sentence boundaries (existing logic)

All `EvidenceCandidate` objects gain P10 provenance fields:
`page_number`, `extraction_method`, `content_hash`, `retrieval_timestamp`,
`source_text_type`, `document_type`.

## Known Limitations

- Scanned PDFs are detected and rejected (no OCR in this pass)
- DOCX tables and footnotes are not currently extracted
- Dynamic JavaScript-rendered pages may produce boilerplate if neither
  Trafilatura nor Firecrawl is configured
- DOC (not DOCX) files are treated as DOCX but may fail silently
- Page count cap: PDF pages beyond 50 are not extracted
