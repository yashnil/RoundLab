# Evidence Support Verification (Pass 11)

Dissio verifies that each generated evidence card actually supports the user's claim and tag before adding it to the results. This document describes the verification architecture.

## Overview

Verification runs in three independently testable layers:

1. **Deterministic mismatch checks** — pure pattern matching, no LLM, always run
2. **Semantic/LLM verifier** — optional, disabled by default in the search loop
3. **Verdict aggregation** — deterministic rules that combine signals from layers 1 and 2

## Verdicts

| Verdict | Meaning | Pipeline action |
|---|---|---|
| `supported` | Evidence directly supports claim and tag | Accept |
| `partially_supported` | Evidence supports the idea but has a scope/causal/magnitude mismatch | Accept with warning |
| `insufficient_context` | Source is abstract-only, snippet-only, or metadata-only | Accept with label |
| `unsupported` | Evidence does not address the claim | Exclude |
| `contradicted` | Evidence argues against the claim | Move to counter-evidence |
| `verification_unavailable` | Verification did not run or returned an error | Accept (degraded) |

## Dimensions

Each dimension is evaluated independently. The overall verdict is aggregated from all dimensions.

| Dimension | What it checks |
|---|---|
| `core_claim` | Keyword overlap between claim and evidence body |
| `causal_strength` | Claim says "causes" but source only shows correlation |
| `certainty` | Claim says "will/always" but source says "may/suggests" |
| `magnitude` | Claim contains a specific figure not found in source |
| `timeframe` | Historical data presented as current, or short-term as permanent |
| `population_scope` | Universal population claim vs. specific study subgroup |
| `geographic_scope` | National/global claim vs. local/state study |
| `policy_or_intervention_match` | Policy terms in claim absent from source |
| `source_attribution` | Journalism presented as original research |
| `caveat_completeness` | Important limitations in surrounding context not captured |

## Safer Tags

When a card is `partially_supported`, the verifier generates a **safer tag suggestion** by narrowing the language. For example, replacing "causes" with "is associated with" or "always" with "likely."

**Safer tags are never auto-applied.** They appear as suggestions in `EvidenceSupportPanel` and require explicit user confirmation.

## Source Text Types

The verifier respects source-text completeness:

- `full_text` — full article extraction, all dimensions checked
- `abstract_only` — at most `partially_supported` verdict
- `partial_extraction` — dimensions checked with a warning
- `snippet_only` — `insufficient_context` (cannot verify from a snippet alone)
- `metadata_only` — `insufficient_context` (no body text available)

## Configuration

| Setting | Default | Description |
|---|---|---|
| `RESEARCH_ENABLE_CARD_VERIFICATION` | `true` | Enable/disable the verification pass |
| `CARD_VERIFIER_BACKEND` | `"llm"` | `"llm"` or `"disabled"` |
| `CARD_VERIFIER_TIMEOUT_S` | `10.0` | LLM verifier timeout in seconds |
| `CARD_VERIFIER_MAX_CARDS` | `4` | Maximum cards to verify per search call |
| `CARD_VERIFIER_MAX_CONTEXT_CHARS` | `3000` | Maximum surrounding context passed to LLM |

In the search loop, the LLM verifier is disabled for speed (`enable_semantic=False`). It can be enabled for individual card quality checks via the API.

## Safety Invariants

- Evidence body text is **never modified** by the verifier.
- Safer tags are **never auto-applied**.
- No outside web knowledge is used during verification.
- Invalid quoted spans from the LLM are discarded before use.
- Verification failure **never fails evidence generation** — errors degrade to `verification_unavailable` gracefully.
