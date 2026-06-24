# Blockfile Coverage Rules (Pass 14)

## Purpose

The blockfile coverage analyzer inspects each section of a blockfile and reports which debate-native dimensions are covered by entries, cards, or frontlines, and which are missing.

---

## Argument Type Detection

Each top-level section is assigned one of four roles:

| Role | Section types |
|---|---|
| `contention` | `contention`, `subpoint`, `observation`, `overview` |
| `response` | `response`, `rebuttal` |
| `framework` | `framework`, `value`, `criterion` |
| `general` | `summary`, `note`, `extension`, anything else |

The role determines which dimension set to check.

---

## Contention Dimensions (13)

| Dimension | What is checked |
|---|---|
| `claim` | Entry has a card with tag containing claim/contend/argue/point |
| `uniqueness` | Entry or card text mentions unique/only/distinct/hasn't happened/not currently |
| `link` | Entry/card mentions cause/leads/because/link/trigger |
| `warrant` | Entry has evidence cards or body_text containing warrant/mechanism/explain |
| `impact` | Entry/card mentions impact/harm/result/consequence/effect |
| `magnitude` | Entry/card mentions magnitude/extent/scope/scale/million/billion |
| `probability` | Entry/card mentions likely/probability/risk/chance/possible |
| `timeframe` | Entry/card mentions timeframe/by 2X/short-term/long-term |
| `weighing` | Entry/card mentions outweighs/more important/magnitude/breadth/probability |
| `primary_source` | At least one saved evidence card in this section |
| `summary` | Entry/card contains summary/summarize/in sum/in short |
| `final_focus` | Entry/card contains final focus/crystallize/two reasons |

---

## Response Dimensions (7)

| Dimension | What is checked |
|---|---|
| `response_claim` | Section entry has a direct response claim |
| `explanation` | Entry body explains why the argument fails |
| `supporting_evidence` | At least one evidence card linked to the response |
| `response_type` | Known response type: turn/non-unique/no-link/impact-defense |
| `speech_suitability` | Entry notes which speech (1AR/2NR/etc.) this response suits |
| `offensive_option` | (Optional, not required) Turn or offensive answer present |
| `defensive_coverage` | Defensive answer present (at minimum) |

Note: `offensive_option` is checked but **not required** for a "covered" state. A well-formed defensive response without a turn is still considered covered.

---

## Framework Dimensions (4)

| Dimension | What is checked |
|---|---|
| `value` | Entry or card mentions value/morality/justice/rights |
| `criterion` | Entry mentions criterion/standard/measure |
| `application` | Entry applies framework to the resolution explicitly |
| `framework_source` | At least one source card in the framework section |

---

## Coverage States (5)

| State | Meaning |
|---|---|
| `covered` | Dimension satisfied by at least one card or entry |
| `partially_covered` | Some signal present but incomplete |
| `missing` | No signal for this dimension |
| `not_applicable` | Dimension doesn't apply to this argument type |
| `warning` | Dimension check found a potential issue (e.g., card present but unsupported verdict) |

---

## Coverage Percentage

For each section:

```
coverage_pct = covered_count / total_applicable_count * 100
```

`total_applicable_count` excludes `not_applicable` dimensions.

A section with `coverage_pct < 50` generates a `missing_argument` or `missing_response` gap (severity: `high`).
A section with `50 <= coverage_pct < 75` generates a gap with severity `medium`.

---

## Nesting Behavior

Only **top-level sections** within a blockfile are analyzed. Sub-entries within a section are included in the analysis (cards and entries recurse through the section), but nested sub-sections are not analyzed as separate entities.

---

## API

```
POST /prep/blockfile-coverage/{blockfile_id}?user_id=<uid>
→ list[BlockfileCoverageResult]
```

Each `BlockfileCoverageResult` includes:
- `argument_id`, `section_id`, `section_title`, `argument_type`
- `dimensions: list[CoverageDimension]`
- `covered_count`, `total_applicable_count`, `coverage_pct`
- `gaps: list[str]` (human-readable missing dimension names)
