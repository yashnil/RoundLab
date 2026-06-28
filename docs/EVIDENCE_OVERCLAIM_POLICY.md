# Evidence Overclaim Policy (Pass 11)

Dissio detects and flags overclaims in evidence cards — cases where the generated tag or the user's claim overstates what the source evidence actually says.

## What counts as an overclaim?

An overclaim is any of the following:

| Type | Example overclaim | What the source actually says |
|---|---|---|
| Causation | "Minimum wage causes job loss" | "Minimum wage is correlated with reduced employment in some studies" |
| Certainty | "Policy X will eliminate poverty" | "Policy X may reduce poverty rates among low-income families" |
| Magnitude | "Crime fell 40%" | No specific percentage cited in the source |
| Population | "All students benefit from debate" | "Study participants (n=120 high school students) showed improvement" |
| Geography | "Nationwide results show..." | Single-state pilot program |
| Timeframe | "Current research proves..." | Study conducted in 2007 |
| Permanence | "Long-term effects are proven" | 6-month follow-up study |

## What does NOT count as an overclaim?

The verifier is deliberately conservative. The following are **not** flagged:

- Minor wording differences that don't change the core claim's accuracy
- Small numeric differences (e.g., source says "37%" and claim says "about a third")
- Active vs. passive voice differences
- Adding or removing "the" or similar articles
- Differences in citation format or author attribution style

## Treatment of detected overclaims

| Severity | Action |
|---|---|
| Critical (CONTRADICTED) | Card moved to counter-evidence; not shown as supporting card |
| Major mismatch | Card kept with `partially_supported` verdict and warning |
| Minor imprecision | Card kept; `safer_tag` suggestion shown |
| No issues | Card accepted normally as `supported` |

## Safer tag policy

When a `partially_supported` verdict is issued, the verifier may generate a safer tag with narrowed language. This tag:

1. Is displayed to the user in `EvidenceSupportPanel` as a **suggestion only**
2. Requires explicit user action to apply (click "Apply safer tag")
3. Is **never auto-applied** to the card
4. Contains only language grounded in the original source
5. Is purely deterministic (no LLM synthesis) — it replaces causal/certain language with the source's actual register

## Why this matters for debate

In Public Forum debate, judge challenges often center on:
- "Does your evidence actually say that?"
- "Your author says 'may contribute' — that's not the same as 'causes'"
- "That's a local study — you can't generalize to the national level"

The verifier is designed to help debaters pre-empt these challenges. A card with a `partially_supported` label gives the debater a signal to either find stronger evidence or use more careful in-round language.
