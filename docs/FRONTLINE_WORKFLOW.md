# Frontline Workflow

## What is a frontline?

A frontline is a prepared answer to a specific opponent argument. It records:
- **The opponent's claim** — what they say
- **The opponent's warrant** — why they say it's true
- **The opponent's impact** — why it matters
- **Your responses** — a prioritized list of refutations

Frontlines are attached to blockfile sections, not to individual cards. A single section can contain multiple frontlines (e.g., different opponents on the same topic).

## Creating a frontline

1. Open a blockfile → select or create a section
2. In the `BlockfileEditor`, click **Add Frontline**
3. Fill in the opponent claim/warrant/impact
4. Call `POST /library/sections/{section_id}/frontlines`

## Adding responses

Each frontline holds an ordered list of `FrontlineResponse` records.

```
POST /library/frontlines/{frontline_id}/responses
{
  "response_type": "turn",
  "response_claim": "Their mechanism causes the opposite effect",
  "explanation": "If X causes Y, and Y causes Z, then ...",
  "wording_for_speech": "Cross-apply our third impact — their own warrant proves our side",
  "priority": 1,
  "speech_suitability": ["rebuttal", "summary"],
  "is_analytical": false
}
```

## Response types

| Type | When to use |
|---|---|
| `no_link` | Opponent's evidence doesn't apply to the resolution |
| `link_defense` | Defend why your case doesn't trigger their harm |
| `impact_defense` | Their impact doesn't materialize / is exaggerated |
| `uniqueness_takeout` | The harm exists regardless of the plan |
| `turn` | Their argument actually proves your side |
| `counterplan` | Offer an alternative that solves their concern |
| `mitigation` | Reduce the weight of their impact |
| `non_unique` | The harm happens without the plan anyway |
| `weighing` | Concede the argument but win on comparison |
| `evidence_indictment` | Their source is biased, outdated, or miscited |
| `source_challenge` | Their evidence doesn't say what they claim |

## Priority

Priority 1 = lead response (read every round). Priority 2 = conditional (read if they extend). Priority 3+ = in reserve.

The UI renders P1 responses with green text, P2 with amber, P3+ in muted gray.

## Speech suitability

Each response can be tagged for one or more speeches:
- `rebuttal` — first rebuttal
- `summary` — summary speech
- `final_focus` — final focus

This lets coaches mark which responses are only worth reading in longer speeches and which must always be in the two-minute final focus.

## Analytical responses

Set `is_analytical: true` when the response is a logical argument that doesn't require an evidence card. Analytical responses show an "Analytical" badge and skip the card-linking flow.

## Ordering

Responses are ordered by `position` within a frontline. The default sort is position ascending. Re-ordering is done by `PATCH /library/responses/{id}` with a new `position` value.

## Deleting frontlines

`DELETE /library/frontlines/{id}` removes the frontline and all its responses. It does **not** affect any cards referenced in those responses.

## Viewing frontlines

The **Frontlines** tab on the library page shows a message directing users to open a blockfile section. Frontlines are embedded in the blockfile workflow, not browsed independently.
