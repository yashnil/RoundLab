# Gap-Driven Workouts (Pass 14)

## Purpose

Workouts translate abstract prep gaps into concrete, time-boxed practice reps. Each workout is tied to a specific evidence card from the debater's actual library — not generated text.

---

## Workout Types (7)

| Workout Type | Gap it targets | Time limit |
|---|---|---|
| `evidence_explanation` | `missing_warrant`, `missing_impact`, `abstract_only` | 90 seconds |
| `card_comparison` | `duplicate_evidence`, `insufficient_source_diversity` | 120 seconds |
| `frontline_speed` | `frontline_underdeveloped`, `missing_response` | 120 seconds |
| `summary_extension` | `missing_summary_extension` | 90 seconds |
| `evidence_indictment` | `weak_source`, `partial_support` | 90 seconds |
| `stale_evidence` | `stale_evidence` | 90 seconds |
| `lay_judge_evidence` | `missing_warrant`, `missing_impact`, `weak_source` | 90 seconds |

---

## Evidence Immutability

At the time a workout is created, the source card's body text is **copied into `source_card_body`** (truncated to 1000 characters). The workout prompt references this snapshot.

If the debater later edits or replaces the card, the workout still shows the original text. This preserves the integrity of the drill — the debater is practicing with a specific piece of evidence as it was when the gap was identified.

---

## Workout Generation Flow

```
generate_workouts_for_report(report, cards, workspace_id, user_id, max_workouts=10)
  → for each gap (in severity order):
      if gap.card_id and card is in cards:
          build workout for gap category
          append to list
          stop when max_workouts reached
  → return list[PrepWorkoutCreate]
```

Gaps are processed in severity order: `critical` first, then `high`, `medium`, `low`.
A single gap → at most one workout.

---

## Workout Structure

Each workout has:

| Field | Description |
|---|---|
| `title` | Short name (e.g., "Explain the Warrant: [card tag]") |
| `description` | One-sentence context for why this workout matters |
| `prompt` | The actual task the debater performs (spoken aloud or written) |
| `instructions` | Step-by-step breakdown (optional) |
| `success_criteria` | 2–4 bullet points describing a good rep |
| `time_limit_seconds` | Countdown for the drill |
| `source_card_body` | Snapshot of the card text at creation time |
| `source_card_tag` | Tag line of the source card |

---

## Example: Evidence Explanation Workout

**Gap:** `missing_warrant` for card "Global warming accelerates faster under ice-free conditions"

**Prompt:**
> Read the card above. In 30 seconds, explain: (1) what the evidence proves, (2) why the mechanism works, and (3) how it impacts the debate round. Do not read the card — explain it in your own words.

**Success criteria:**
- Named the specific mechanism (not just "because the card says so")
- Explained how the impact connects to your argument
- Used language a lay judge would understand
- Completed within the time limit

---

## Example: Stale Evidence Workout

**Gap:** `stale_evidence` for card "2019 study on biodiversity loss rates"

**Prompt:**
> This card is from 2019. Your opponent will say "their evidence is 5 years old — the situation has changed." Prepare a 45-second response explaining why this evidence is still valid in the round today.

**Success criteria:**
- Acknowledged the date without conceding irrelevance
- Explained why the claim is still supported (trend, law, mechanism)
- Did not lie about the card's date
- Completed within the time limit

---

## Workout Completion

When a workout is marked `completed`:

1. The `status` field updates to `completed` and `completed_at` is set.
2. A `workouts_completed` product event is emitted.
3. The parent gap is **not automatically resolved** — gap resolution requires the debater to take the recommended action (research new evidence, build a frontline, etc.).

This is intentional: completing a drill improves skill but does not substitute for finding missing evidence.

---

## Max Workouts

The `max_workouts` parameter (default 10) caps total workouts per plan generation. This prevents overwhelming the debater with a long list. The most severe gaps always get workouts first.

---

## Privacy

Workouts reference only cards owned by the requesting `user_id`. The `source_card_body` in the workout row is also owned by the same user. Coach team assignment (`team_id` on the workspace) does not grant coaches access to private card text.
