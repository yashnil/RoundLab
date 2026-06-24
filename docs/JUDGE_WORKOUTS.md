# Judge Adaptation Workouts (Pass 15)

## Purpose

Judge workouts build the skill of adapting arguments and evidence introductions for different types of judges. They are generated from the student's actual prepared material. They do not require the AI to rewrite the material.

## Workout Types

### lay_explanation (30 seconds)
**When generated:** Evidence source + lay judge type.
**Goal:** Explain the evidence without debate jargon.
**Success criteria:**
- No debate jargon used
- Connected to a real-world consequence
- Completed within 30 seconds

### parent_context (45 seconds)
**When generated:** Evidence source + parent judge type.
**Goal:** Set up the topic, claim, and real-world example for a parent judge.
**Success criteria:**
- Defined at least one debate term
- Provided real-world context
- Did not assume policy knowledge

### flow_extension (20 seconds)
**When generated:** Argument/section source + flow or coach judge type.
**Goal:** Deliver a complete labeled extension in under 20 seconds.
**Format:** `Extend [label] — [evidence tag] — still true because [one sentence] — impacts [impact label]`

### technical_concession (60 seconds)
**When generated:** Frontline source + technical judge type.
**Goal:** Identify concessions and build a precise logical chain.
**Format:** `They conceded X in their [speech]. That means Y. Which means Z.`

### judge_switch (120 seconds)
**When generated:** Argument source + lay or parent judge type (when technical frontline not available).
**Goal:** Deliver the same argument twice: once for a lay judge, once for a technical judge.
**Constraint:** Facts and source do not change between rounds.

### evidence_adaptation (90 seconds)
**When generated:** Evidence source + flow, technical, or coach judge type.
**Goal:** Introduce the same card differently for a parent judge and a flow judge.
**Parent format:** `According to [source], [finding in plain terms]. This matters because [one sentence].`
**Flow format:** `[Short citation] — [claim] — [warrant] — [impact label].`

### final_focus_voter (90 seconds)
**When generated:** Summary or final focus source.
**Goal:** Frame the same voter for two different judge types in final focus.
**Constraint:** No new arguments may be introduced.

## Source Material Handling

- `source_card_body_snapshot` is capped at 500 characters.
- The snapshot is for student reference only; it is never used as evidence text.
- The full card body is NOT stored in the workout record.
- Source card ID (`source_card_id`) is stored as a reference.

## Coach Assignments

Coaches may assign workouts to students via `POST /judge-adaptation/workouts/assign`.
The snapshot constraint applies to coach assignments as well.
Students complete assignments via `PATCH /judge-adaptation/workouts/{id}/complete`.

## Student Notes

Students may attach notes when completing a workout. Notes are stored in `student_notes` on the `judge_workout_assignments` record. Notes are private to the student and the assigning coach.

## Completion Tracking

Completing a judge workout updates `judge_readiness` signals but does NOT modify:
- Evidence freshness state
- Evidence quality/support verdict
- Argument coverage scores
