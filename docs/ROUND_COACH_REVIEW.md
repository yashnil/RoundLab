# Coach Round Review — Pass 17

## Overview

Coaches authorized to view a team round can add annotations, rate automated findings, assign drills, and export a round report. **Coach feedback never alters historical speech, flow, or evidence records.**

## Services

`coach_round_review.py`:
- `add_coach_annotation()` — timestamped note on a speech, argument, or finding
- `list_coach_annotations()` — list all annotations for a round
- `assign_drill_from_round()` — assign a round drill to a student
- `export_round_report()` — export a printable round report
- `rate_automated_finding()` — mark a finding correct/incorrect/useful

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/{round_id}/annotations` | Add coach annotation |
| GET | `/{round_id}/annotations` | List annotations |
| POST | `/{round_id}/findings/{id}/rate` | Rate a finding |
| GET | `/{round_id}/report` | Export round report |

## Annotation Types

- `speech_note` — note on a speech
- `argument_note` — note on a specific argument
- `correction` — correction to an automated finding (set `is_correction=True`)
- `drill_assignment` — drill assigned to student
- `highlight` — highlighted moment for review

## Finding Ratings

- `correct` — finding is accurate
- `partly_correct` — partially right
- `incorrect` — finding is wrong
- `useful` — helpful regardless of accuracy
- `not_useful` — not helpful

## Database Tables

- `round_coach_annotations` — all coach annotations
- `round_finding_ratings` — finding quality ratings

## Ownership Model

The caller (API endpoint) must verify round ownership via `_verify_owner()` before calling any coach review service. Service layer trusts that the caller has already verified.

## Constraints

- `export_round_report()` NEVER exposes raw speech transcripts
- Private notes only included when `include_private_notes=True`
- Annotations insert-only — never update historical records
