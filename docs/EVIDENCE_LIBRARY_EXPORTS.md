# Evidence Library Exports

## Principles

- Exports contain **only debate-relevant content**: tag, cite, body text, MLA citation. No internal IDs, offsets, diagnostic traces, or AI metadata.
- Source text is never duplicated. If the same card appears in two sections, the bibliography entry appears once (deduplicated by DOI or canonical URL).
- Exports are deterministic: the same blockfile state always produces the same output.

## Safe card fields

The `_safe_card()` function restricts export to these fields:

```python
_EXPORT_CARD_FIELDS = {
    "id", "tag", "cite", "body_text",
    "author", "publication", "title", "published_date",
    "url", "mla_citation", "short_cite",
}
```

All other fields (span offsets, diagnostic JSON, AI scores, user markup) are excluded.

## Bibliography deduplication

`_bib_key(card)` returns:
- `doi:{normalized_doi}` if a DOI is present
- `url:{url_without_query}` if a URL is present  
- `None` otherwise (card is always included)

`_build_bibliography(cards)` collects all cards, deduplicates by key, and returns a sorted list of MLA citations.

## JSON export

`GET /library/blockfiles/{id}/export.json`

```json
{
  "title": "Neg frontlines on Economy",
  "side": "con",
  "resolution": "Resolved: ...",
  "exported_at": "2026-06-22T00:00:00Z",
  "sections": [
    {
      "title": "Direct Negation",
      "section_type": "neg_case",
      "entries": [
        {
          "tag": "Trade deficits have no GDP impact",
          "cite": "Smith 2024",
          "body_text": "...",
          "mla_citation": "Smith, John. ..."
        }
      ],
      "frontlines": [
        {
          "opponent_claim": "Economy collapses without intervention",
          "responses": [
            {
              "response_type": "turn",
              "response_claim": "Their mechanism causes the opposite effect",
              "priority": 1,
              "speech_suitability": ["rebuttal", "summary"]
            }
          ]
        }
      ]
    }
  ],
  "bibliography": [
    "Smith, John. \"Trade Deficits and GDP.\" ..."
  ]
}
```

## Markdown export

`GET /library/blockfiles/{id}/export.md`

```markdown
# Neg frontlines on Economy

**Side:** Con  
**Resolution:** Resolved: ...

---

## Direct Negation

### Trade deficits have no GDP impact

**Cite:** Smith 2024

Trade deficits have no measurable impact on GDP growth...

---

#### Frontline: Economy collapses without intervention

**Opponent claim:** Economy collapses without intervention

**Response 1 (Turn, P1):** Their mechanism causes the opposite effect

---

## Bibliography

Smith, John. "Trade Deficits and GDP." *Journal of Economics* vol. 12 (2024): 1–20.
```

Markdown is formatted for readability in Google Docs or Notion. Sections are H2, cards are H3, frontlines are H4.

## DOCX export

`GET /library/blockfiles/{id}/export.docx`

Requires `python-docx` to be installed (`pip install python-docx`). The DOCX export produces:

- Title in Heading 1 style
- Section titles in Heading 2 style
- Card tag in bold
- Card cite in italic
- Card body in normal style with 0.5-inch left indent
- Frontline opponent claim block with a "OPPONENT:" label in small caps
- Response entries with priority prefix (P1:, P2:, etc.)
- Bibliography as a separate section with hanging indent

If `python-docx` is not installed, the endpoint raises HTTP 500 with a message to run `pip install python-docx`.

## Frontline export

Frontlines are embedded within their section's export block. They are **not** exported as a standalone format in MVP. The JSON structure preserves full frontline data including all response fields.

## What is NOT exported

- Internal UUIDs (card_id, blockfile_id, section_id, etc.)
- Span offsets (highlighted_spans_json, underline_spans_json)
- AI diagnostic metadata (cut_confidence, coherence scores, pass traces)
- User markup data
- Support verdict (avoid leaking AI judgment into distributed documents)
- Author institution metadata beyond what appears in the MLA citation
