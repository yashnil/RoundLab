# Latency Budgets — Pass 18

## Target Budgets (server-side, P95)

| Operation | Target | Notes |
|-----------|--------|-------|
| UI interaction feedback | < 200 ms | Button press, state change |
| First visible search progress | < 1 s | Progress bar must appear |
| Evidence search (total) | < 30 s | `LATENCY_EVIDENCE_SEARCH_S` |
| Card cutting (LLM) | < 15 s | `LATENCY_CARD_CUT_S` |
| Citation enrichment | < 5 s | Crossref/Zotero lookup |
| Speech transcription (30 s clip) | < 20 s | Whisper API |
| Speech analysis (argument map) | < 25 s | LLM pipeline |
| Feedback generation | < 30 s | Full ballot |
| Opponent speech generation | < 20 s | `LATENCY_OPPONENT_SPEECH_S` |
| Crossfire response | < 5 s | Must feel conversational |
| Ballot generation | < 25 s | `LATENCY_BALLOT_S` |
| Round replay build | < 2 s | Deterministic, DB-only |
| Coach annotation save | < 1 s | Insert-only |
| Health readiness check | < 10 s | All external pings |

## Config Variables

Set these in `.env` to adjust targets for monitoring:

```
LATENCY_EVIDENCE_SEARCH_S=30.0
LATENCY_CARD_CUT_S=15.0
LATENCY_OPPONENT_SPEECH_S=20.0
LATENCY_BALLOT_S=25.0
```

## Measurement

Every request includes `x-response-time-ms` in the response header (set by `CorrelationMiddleware`). Stage-level timing is logged at `DEBUG` level.

## Indefinite Loading States (Prohibited)

All loading states must be bounded. If an operation exceeds its budget:
- Show a user-facing error with a retry option
- Log `workflow_stage_failed` event to analytics
- Return a structured error with `stage` and `error_code` fields

Never show a spinner that can spin forever. Minimum: a timeout + fallback message.

## Fallbacks

| Stage | Fallback |
|-------|---------|
| LLM card refiner | Deterministic cut (no refiner cost) |
| Semantic reranker | BM25 only |
| Academic search | Web results only |
| Citation enrichment | MLA from metadata fields |
| Opponent speech (LLM) | Template-based speech |
| Crossfire response | Pre-written response bank |
