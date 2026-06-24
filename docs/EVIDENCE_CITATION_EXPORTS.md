# Evidence Citation Exports (Pass 12)

## Single card export actions

| Action | Format | How |
|---|---|---|
| Copy Debate | Compact RoundLab format | Copy button in CitationDetailsPanel |
| Copy MLA | MLA 9th edition | Format selector → copy |
| Copy APA | APA 7th edition | Format selector → copy |
| Copy Chicago | Chicago 17th author-date | Format selector → copy |
| Download BibTeX | `.bib` file | Format selector → Download .bib |
| Download RIS | `.ris` file | Format selector → Download .ris |
| Copy CSL-JSON | JSON string | Format selector → copy |
| Download CSL-JSON | `.json` file | Format selector → Download .json |

## Bibliography export (multiple cards)

`export_bibliography(records, fmt)` in `citation_renderers.py` produces a
deduplicated bibliography for a list of CitationRecord objects.

**Deduplication:** Cards sharing the same DOI (case-insensitive) collapse to
one entry.  Cards using the same source URL (without DOI) are NOT automatically
deduplicated — they may represent different excerpts from the same page.

**Citation key stability:** `citation_key(record)` is deterministic:
`{first_surname}{year}{first_title_word}` (alphanumeric only, max 40 chars).
Collisions are handled by uniqueness tracking within a single export call.

**Supported output formats:** `mla`, `apa`, `chicago`, `bibtex`, `ris`, `csl_json`.

**Ordering:** Records are output in the order passed.  Callers should sort
before calling (e.g. alphabetical by author surname for bibliographies).

## RoundLab debate citation format

The `debate` format is a compact header suitable for card reading aloud:

```
Surname Year — Institution, Publication
```

Rules:
- Author surname(s) or organization name
- Year (or n.d. if unavailable)
- Institution only when `institution_prov.confidence >= high`; never fabricated
- Container title (journal, publication, website)
- Separator `—` used only when a qualification follows

Examples:
- `Smith & Jones 2024 — Harvard Medical School, NEJM`
- `Congressional Research Service 2023 — CRS Report`
- `RAND Corporation 2022`
- `Brookings 2021 — Economic Studies`
- `n.d.` (minimal fallback when no author and no year)

## Format specifications used

| Format | Edition/version |
|---|---|
| MLA | 9th edition |
| APA | 7th edition |
| Chicago | 17th edition, author-date style |
| BibTeX | Standard BibTeX (biblatex-compatible) |
| RIS | RIS (Reference Manager) format |
| CSL-JSON | Citation Style Language JSON schema |

## Field coverage by format

| Field | debate | MLA | APA | Chicago | BibTeX | RIS | CSL |
|---|---|---|---|---|---|---|---|
| authors | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| year | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| title | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| container_title | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| publisher | — | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| volume/issue | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| page | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| doi | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| url | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| institution | ✓ | — | — | — | ✓ | ✓ | — |

## Export exclusions

Exports never include:
- Internal trace fields (`p11_*`, `p12_*`, search diagnostics)
- API keys or provider tokens
- Support verification details or NLI scores
- Source snapshots or raw HTML
- User session data

The CitationRecord exported via CSL-JSON includes only citation-relevant fields.
