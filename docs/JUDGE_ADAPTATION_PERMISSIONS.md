# Judge Adaptation Permissions (Pass 15)

## Row-Level Security

All judge adaptation tables use Postgres RLS:

- `judge_profiles`: Users may read all public profiles and their own private profiles.
- `judge_adaptations`: Users may read and write their own adaptations only.
- `judge_adaptation_notes`: Users may read their own notes only.
- `judge_workout_assignments`: Students see rows where `assigned_to = auth.uid()`. Coaches see rows where `assigned_by = auth.uid()`.

## Application-Level Ownership

The service layer enforces ownership before DB operations:
```python
if row["user_id"] != user_id:
    return None  # or raise PermissionError
```

This is necessary because service-role keys bypass RLS.

## Coach Role

A user is treated as a coach if `profiles.role = 'coach'` or `team_members.role = 'coach'`.

Coaches may:
- Assign judge workouts to any student in their team (`POST /workouts/assign`)
- View completion status of assigned workouts (`GET /workouts`)
- Create custom judge profiles for team use

Coaches may **not**:
- Read a student's adaptation notes
- Modify a student's adaptation results
- Override risk flags

## Custom Profile Visibility

Custom judge profiles are private by default (`is_public = false`).
A user may create a team-scoped profile by setting `team_id`.
Team profiles are visible to all members of that team.

## Public Judge Rating System

A public judge-rating or judge-ranking system is **not** built and must not be built in future passes. This is a product decision, not a technical one.

## Evidence Body Access

The judge adaptation API never returns `body_text` from `evidence_cards`.
The 500-character `source_card_body_snapshot` is the only allowable excerpt, and it is only stored once at workout creation for auditability.

## Data Retention

Adaptation results are stored indefinitely. Users may not delete adaptation records through the API. Notes may be managed by the user who created them.
