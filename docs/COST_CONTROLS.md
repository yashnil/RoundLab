# Cost Controls — Pass 18

## Estimated Per-Operation Cost (USD)

All estimates use `gpt-4o-mini` pricing (input: $0.00015/1K, output: $0.0006/1K).

| Operation | Estimated Cost | Max Tokens (in+out) |
|-----------|---------------|---------------------|
| Card cut | ~$0.0008 | 2000 + 800 |
| Card verify | ~$0.0006 | 1500 + 600 |
| Card refine | ~$0.0004 | 1000 + 400 |
| Speech analysis | ~$0.001 | 3000 + 1000 |
| Feedback generation | ~$0.0015 | 4000 + 1500 |
| Opponent speech | ~$0.0007 | 2000 + 600 |
| Ballot generation | ~$0.001 | 3000 + 1000 |
| Judge adaptation | ~$0.0007 | 2000 + 800 |
| Crossfire response | ~$0.0003 | 1000 + 300 |

### Provider costs (non-token)

| Provider | Cost per call |
|----------|-------------|
| Tavily search | ~$0.005 |
| Exa search | ~$0.005 |
| Cohere reranker | ~$0.001 |
| Firecrawl scrape | ~$0.003 |
| Crossref / OpenAlex | Free |

## Per-Student Typical Session Cost

A full round + 3 evidence cards + feedback:
- 1 full round (13 phases) × crossfire + opponent speeches: ~$0.05–$0.10
- 3 evidence cards (search + cut + verify): ~$0.05
- 1 speech analysis + feedback: ~$0.003
- **Estimated total per session: $0.10–$0.20**

## Safeguards

### Feature Flags (in `.env`)

```
PILOT_MODE=true                        # Enable daily limits
DAILY_LLM_BUDGET_USD=1.0              # Max spend per user per day
MAX_ROUNDS_PER_USER_DAILY=5           # Max rounds per user per day
MAX_EVIDENCE_SEARCHES_PER_DAY=20      # Max search calls per user per day
RESEARCH_ENABLE_LLM_REFINER=true      # Disable to cut card-cut LLM cost
RESEARCH_ENABLE_LLM_ROLE_CLASSIFIER=false  # Saves ~$0.0001 per search chunk
USE_SEMANTIC_RERANKER=false           # Disables local CrossEncoder
```

### Token Caps (per LLM call)

All LLM calls have explicit `max_tokens` limits enforced at the call site:
- Card cutting: 800 tokens
- Card verifier: 600 tokens
- Speech feedback: 300 tokens
- Crossfire response: 120 tokens

### Request Deduplication

- Card drafts use idempotency keys — duplicate submissions do not re-run LLM
- Round phases are append-only — advancing twice does not re-run the LLM
- Citation enrichment results are cached in Supabase (Crossref lookup)

### Caching

- Crossref DOI lookups: cached in evidence_cards table (`citation_json`)
- Card verifier results: stored in `intelligence_json` (not re-run on view)
- Semantic scholar results: DB-cached per article

### Low-Cost Pilot Mode

For pilot use, set `RESEARCH_ENABLE_LLM_REFINER=false` and
`RESEARCH_ENABLE_LLM_ROLE_CLASSIFIER=false` to remove two LLM calls from
the evidence pipeline. Deterministic fallbacks handle both.

## Developer Cost Dashboard

Query the pilot cost summary via:

```
GET /users/{user_id}/cost-summary
```

Returns `{ total_usd, by_operation, date }` for today.

Query the database view:

```sql
SELECT * FROM pilot_cost_summary
WHERE date >= current_date - 7
ORDER BY total_cost_usd DESC;
```
