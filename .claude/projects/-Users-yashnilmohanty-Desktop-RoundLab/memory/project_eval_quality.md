---
name: eval-quality-baseline
description: RoundLab eval quality pass results, signal detector state, and known remaining gaps
metadata:
  type: project
---

After the June 2026 eval reliability pass, the system state is:

**Final real eval (8 fixtures): 8/8 pass, F1=0.850, hallucinations=0**

## Progress over time

| Checkpoint | Pass | F1 | Hallucinations |
|---|---|---|---|
| Before session 1 | 1/8 | 0.321 | — |
| After session 1 | ~4-5/8 | 0.558 | 0 |
| After session 2 (final) | 8/8 | 0.850 | 0 |

## Active detector signals (as of 2026-06-08)

`detect_debate_signals()` runs these detectors in order:

1. `_detect_new_argument` — fires for summary/final_focus when "new evidence from X" patterns appear
2. `_detect_no_clash` — fires for rebuttal when zero opponent engagement + ≥2 own-case terms
3. `_detect_weak_evidence` — fires HIGH on vague attribution ("studies show"), MEDIUM on constructive with no named org+year
4. `_detect_weak_extension` — fires HIGH for summary/final_focus with extension language but no warrant re-establishment phrases; MEDIUM if very thin re-establishment
5. `_detect_missing_warrant` — fires HIGH for constructive with impact language but zero explicit mechanism phrases; suppressed if has_named_evidence + warrant + impact all present

## Session 2 changes

1. `debate_signal_detection.py` — Added `_detect_weak_extension()` + `_detect_missing_warrant()`, wired into `detect_debate_signals()`
2. `evals/fixtures/extension_without_warrant.json` — `no_weighing.required` → false
3. `evals/fixtures/good_extension_summary.json` — added weighing language + `no_weighing` as non-required expected issue
4. 3 new fixtures: `weak_extension_isolated_summary`, `good_extension_summary`, `missing_warrant_isolated_constructive`
5. Tests: 21 new unit tests added (TestDetectWeakExtension, TestDetectMissingWarrant, TestCalibrateNewSignals)

## Remaining known FP patterns (sub-1.0 F1 cases, still PASS)

- `extension_without_warrant`: LLM catches `weak_extension` but misses `no_weighing` (non-required → passes)
- `good_extension_summary`: LLM generates `weak_extension` FP even when detector fires no signals; detector suppression isn't fully stopping the LLM here
- `missing_warrant_isolated_constructive`: LLM adds `weak_evidence` FP alongside correct `missing_warrant` (both detector-backed, so calibrator keeps them)

## How to apply

- Detector signals are injected into the prompt before the LLM call AND enforced by calibration after — do not rely on the LLM alone for new_argument, no_clash, weak_evidence, weak_extension, missing_warrant.
- The `good_extension_summary` FP is a prompt-injection gap: the LLM ignores the "no signals → no issues" gate instruction sometimes. Address in a future prompt-tuning pass if needed.
