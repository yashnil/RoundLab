# Judge Readiness Scoring (Pass 15)

## Overview

Judge readiness is a separate scoring dimension from evidence quality (Pass 11) and evidence freshness (Pass 14). It measures how well a student's prepared material is adapted for a specific judge type.

**These scores must never be merged or averaged with evidence quality or freshness scores.**

## Eight Dimensions

| Dimension | What it Measures |
|-----------|-----------------|
| clarity | Jargon-free explanation and plain-language accessibility |
| organization | Argument label discipline and structural completeness |
| extension_completeness | Whether extensions are explicitly stated for the judge type |
| evidence_explanation | How well evidence is introduced for the judge's expectations |
| weighing_fit | Whether weighing is at the right level of detail |
| jargon_fit | Whether the jargon level matches the judge's tolerance |
| strategic_focus | Strategic soundness (causal accuracy, qualifier preservation) |
| speech_stage_legality | Compliance with PF speech-stage rules |

## Scoring

Each dimension starts at a base score (0-100) and loses points for detected risks:

| Risk Severity | Deduction |
|---------------|-----------|
| critical | 30 |
| high | 18 |
| medium | 10 |
| low | 4 |

**Composite score** = average of all scored dimensions (None dimensions excluded).
Critical risks apply an additional deduction of 15 per risk to the composite.

## None (No Data)

A dimension returns `None` when:
- Extension completeness is checked for a non-summary/final-focus source
- Evidence explanation is checked when no evidence cards are linked

`None` is displayed as "No data" in the UI. It is **not** treated as 0.

## Risk Integration

Judge readiness pulls risks from `adaptation_risk_checker.py`. Each risk maps to one or more dimensions:

| Risk Category | Affects Dimension |
|---------------|------------------|
| jargon_overflow | clarity, jargon_fit |
| under_explanation | clarity |
| narrative_over_flow | clarity |
| dropped_argument_uncovered | organization |
| missing_extension | extension_completeness, speech_stage_legality |
| evidence_without_analysis | evidence_explanation |
| unsafe_card_used | evidence_explanation |
| stale_card_used | evidence_explanation |
| warrant_collapsed | weighing_fit |
| causal_overstatement | strategic_focus |
| source_qualification_inflated | strategic_focus |
| new_argument_late_speech | speech_stage_legality |

## Independence from Evidence Quality

Pass 11 generates `support_verdict` for each card. This verdict is:
- Displayed in adaptation output as a read-only reference
- Used to flag `unsafe_card_used` risk
- **Never** used to adjust the evidence quality score

Judge readiness does not contribute to and does not receive from:
- `ReadinessDimensions` in `prep_readiness_scorer.py` (Pass 14)
- `EvidenceFreshnessAssessment` in `evidence_freshness.py` (Pass 14)

## API

`POST /judge-adaptation/readiness-score` accepts a `JudgeAdaptationRequest` and returns a `JudgeReadinessReport` with all 8 dimensions plus composite score.
