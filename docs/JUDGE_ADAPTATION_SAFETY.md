# Judge Adaptation Safety Rules (Pass 15)

## Purpose

This document defines what the system is and is not allowed to do when adapting debate material for different judge types. These rules are enforced deterministically. No LLM override is permitted for any constraint in this document.

## Absolute Prohibitions

The following transformations are **never** permitted regardless of judge type:

1. **Do not alter evidence body text.**
   The verbatim text of any quoted source is immutable. AdaptationChange records contain framing guidance only, never quoted rewrites.

2. **Do not fabricate source qualifications.**
   Author credentials, institutional affiliations, and publication dates are read from the original citation. If a qualification is not in the source, it cannot be added.

3. **Do not strengthen claims for a persuasive judge.**
   If the evidence supports a moderate causal claim, the adaptation cannot present it as definitive for a lay judge. The original causal strength is preserved.

4. **Do not change the support verdict.**
   The support verdict from Pass 11 evidence verification passes through unchanged. An "insufficient" verdict remains "insufficient" for all judge types.

5. **Do not alter citation metadata.**
   Author name, publication name, publication date, URL, and MLA/APA string are never modified.

6. **Do not introduce new factual content.**
   All factual claims in an adaptation must trace to material already in the prepared source.

7. **Do not write the evidence for the student.**
   The system provides guidance on *how* to frame and introduce evidence. It does not rewrite the card or generate persuasive substitute text.

## Permitted Adaptations

The following changes are permitted:

- **Framing guidance:** How to introduce the card for a lay vs. flow judge.
- **Jargon replacement guidance:** A list of terms to replace and suggested plain-language alternatives.
- **Response ordering:** Which responses to lead with for a given judge type.
- **Extension format:** Whether to use a concise label-first or narrative extension.
- **Condensation guidance:** Which responses are less important and may be compressed.
- **Voter framing:** How to frame a final focus voter for the judge's decision-making style.
- **Risk flags:** Warnings about presenting the argument in a way the judge may reject.

## LLM Boundary

The optional LLM path (if enabled) may only:
- Generate suggested phrasing for introductions
- Suggest alternative jargon replacements

The LLM path may **not**:
- Access evidence body text
- Generate factual claims
- Suggest changes to support verdicts or citations
- Override deterministic risk flags

## Risk Categories That Prevent Export

An adaptation with a `critical` risk at the `causal_overstatement` category triggers a warning that must be acknowledged before the student can use the adaptation output. The adaptation itself is still shown (for learning purposes), but the risk is displayed prominently.

## Separation from Evidence Quality

Judge readiness scores are **always** separate from:
- Evidence quality scores (Pass 11 support verification)
- Evidence freshness scores (Pass 14 freshness assessment)

These dimensions must never be merged in the UI or in composite scoring.
