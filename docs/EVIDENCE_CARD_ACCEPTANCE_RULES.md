# Evidence Card Acceptance Rules (Pass 11)

This document defines the complete decision tree for whether a generated evidence card is included in the final result, moved to counter-evidence, or excluded.

## Card acceptance pipeline

```
Evidence passage found
        │
        ▼
[Role classification]
        │
        ├── counter_evidence → counter_evidence_drafts (always, before verification)
        │
        └── supporting role
                │
                ▼
        [Quality gates]  (score ≥ 3.0, non-empty best_supported_claim)
                │
                ├── FAIL → excluded (filtered_low_quality)
                │
                └── PASS
                        │
                        ▼
                [Deduplication]  (body hash, URL domain caps)
                        │
                        ├── DUPLICATE → excluded
                        │
                        └── NEW
                                │
                                ▼
                        [generate_card_draft()]
                        (body_text, tag, citation, intelligence)
                                │
                                ▼
                        [Tag validation]
                                │
                                ▼
                        [Pass 11: Support verification]  ◄─── NEW
                                │
                                ├── CONTRADICTED → move to counter_evidence_drafts
                                │
                                ├── UNSUPPORTED → excluded (filtered_no_support)
                                │
                                └── SUPPORTED / PARTIALLY_SUPPORTED / INSUFFICIENT_CONTEXT
                                        │
                                        ▼
                                [card_drafts.append(draft)]  ← accepted with support_verification dict
```

## Verification-based exclusion rules

| Verdict | Action | Reason |
|---|---|---|
| `supported` | Accept | Evidence directly supports the claim |
| `partially_supported` | Accept with warning | Useful but overstated; safer_tag suggested |
| `insufficient_context` | Accept with label | Can't verify, but source is plausibly relevant |
| `verification_unavailable` | Accept | Verification failed gracefully; prefer over-exclusion |
| `unsupported` | Exclude | Evidence is off-topic for this claim |
| `contradicted` | Move to counter_evidence_drafts | Useful for pre-emption, not as a supporting card |

## Non-exclusion guarantee

The verifier uses **conservative thresholds** to avoid false exclusion:

- A card is only excluded if the keyword overlap is < 30% AND no specific magnitude match exists
- Minor wording differences (synonyms, paraphrases, active/passive) are NOT grounds for exclusion
- Prestige or citation count of the source is NOT a factor
- A card is never excluded for having caveats — only for actively contradicting the claim

## Fields in draft_json

Accepted cards include a `support_verification` key in their `draft_json`:

```json
{
  "support_verification": {
    "overall_verdict": "partially_supported",
    "claim_verdict": "partially_supported",
    "tag_verdict": "partially_supported",
    "dimensions": [...],
    "safer_tag": "Minimum wage is associated with reduced employment in some contexts",
    "safer_tag_generated": true,
    "source_text_type": "full_text",
    "context_limitation": "",
    "deterministic_mismatches": ["causal_strength: claim asserts causation..."],
    "semantic_verifier_used": false,
    "verifier_confidence": 0.5,
    "verification_duration_ms": 1.2
  }
}
```

## Backward compatibility

- `support_verification` is absent from cards generated before Pass 11 or with verification disabled
- Frontend components check for presence before rendering `EvidenceSupportPanel`
- Setting `RESEARCH_ENABLE_CARD_VERIFICATION=false` disables all verification; all cards are accepted
