# Prep Readiness Scoring (Pass 14)

## Design Principles

1. **No LLM scoring.** Every score is computed by deterministic arithmetic over structured data.
2. **None ≠ 0.** If there is no data for a dimension, the dimension score is `None` and is excluded from the composite average rather than dragging it down.
3. **Weights are documented and constant.** Changing weights requires editing `readiness_scorer.py` and this doc.
4. **Gaps deduct from base scores.** Each gap at a given severity deducts a fixed number of points from the relevant dimension.

---

## Dimension Weights

| Dimension | Weight | Rationale |
|---|---|---|
| `argument_coverage` | 1.5 | Core case structure is most critical for round readiness |
| `frontline_readiness` | 1.3 | Frontlines determine ability to win clash |
| `evidence_quality` | 1.2 | Card quality is directly critiqued by judges |
| `evidence_freshness` | 1.0 | Base weight; freshness matters but old evidence isn't wrong |
| `speech_stage_readiness` | 1.0 | Summary and final focus prep affects close rounds |
| `weighing_preparation` | 0.9 | Important but often taught through experience |
| `source_diversity` | 0.8 | Diversity helps but isn't a round-loss by itself |

---

## Severity Deductions

| Severity | Points deducted per gap |
|---|---|
| `critical` | 25 |
| `high` | 15 |
| `medium` | 8 |
| `low` | 3 |
| `info` | 0 |

---

## Per-Dimension Scoring

### `argument_coverage`

Base: 100. Subtract gap deductions for coverage gaps (missing sections, low coverage_pct).
Returns `None` if `total_arguments == 0`.

### `evidence_quality`

Base: 100. Subtract for `unsupported_card`, `weak_source`, `partial_support`, and `abstract_only` gaps.
Returns `None` if `total_cards == 0`.

### `evidence_freshness`

Base: 100. For each freshness assessment:
- `stale` or `superseded`: −10
- `aging`: −5
- `freshness_unknown`: −3

Returns `None` if no freshness assessments.

### `frontline_readiness`

Base: 100. Count frontlines by readiness level:
- `unsafe`: −30 each
- `underdeveloped`: −20 each
- `usable_with_gaps`: −8 each
- `ready`: 0

Returns `None` if `total_frontlines == 0`.

### `source_diversity`

Base: 100. Deduct for `insufficient_source_diversity` gaps:
- Check how many unique domains are present across all cards.
- If fewer than 3 unique domains: `−20`.
- If same domain cited 3+ times: `−10` per repeated domain (capped at −30).

Returns `None` if `total_cards == 0`.

### `speech_stage_readiness`

Base: 100. Deduct for `missing_summary_extension` (`−15` each) and `missing_final_focus_extension` (`−15` each).
Returns `None` if no speech stage gaps were checked.

### `weighing_preparation`

Base: 100. Deduct for `missing_weighing` gaps (−12 each).
Returns `None` if no weighing checks were run.

---

## Composite Score

```python
composite = weighted_average(
    [dim.score for dim in dimensions if dim.score is not None],
    weights=[dim.weight for dim in dimensions if dim.score is not None]
)
```

Returned as `int` (rounded). Returns `None` if all dimensions are `None`.

---

## DimensionScore Model

```python
class DimensionScore(BaseModel):
    dimension: str
    score: Optional[int] = None   # None = insufficient data
    weight: float
    explanation: str              # Human-readable explanation of score
    contributing_gaps: list[str]  # Gap titles that reduced this dimension's score
```

---

## Readiness Interpretation

| Score Range | Interpretation |
|---|---|
| 85–100 | Tournament-ready. Minor polish only. |
| 70–84 | Competition-ready with targeted work needed. |
| 55–69 | Significant gaps. Prioritize critical and high severity tasks. |
| < 55 | Case needs substantial preparation before competition. |

These thresholds are display-only. The UI colors (green/amber/red) use 80/60 as breakpoints.

---

## Re-scoring on Refresh

When `POST /prep/readiness-report` is called with `force_refresh=true`, a fresh report is generated and persisted. The previous report row is retained (not deleted). Task statuses from the prior plan are preserved.
