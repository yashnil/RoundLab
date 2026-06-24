# Evidence Library Permissions

## Ownership model

Every library entity is owned by a single user. The `user_id` column on each table is set at creation and is immutable. All CRUD operations verify `user_id` matches the requesting user before proceeding.

## Row-level security (RLS)

Each table has RLS enabled. The ownership policy pattern:

```sql
-- Only the owner can read their own rows
CREATE POLICY "owner read" ON resolutions
    FOR SELECT USING (auth.uid() = user_id);

-- Only the owner can insert their own rows
CREATE POLICY "owner insert" ON resolutions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Only the owner can update their own rows
CREATE POLICY "owner update" ON resolutions
    FOR UPDATE USING (auth.uid() = user_id);

-- Only the owner can delete their own rows
CREATE POLICY "owner delete" ON resolutions
    FOR DELETE USING (auth.uid() = user_id);
```

Team-scoped tables (`blockfiles`, `blockfile_sections`, `blockfile_entries`, `frontlines`, `frontline_responses`) also have a team-read policy:

```sql
-- Team members can read blockfiles for their team
CREATE POLICY "team read blockfiles" ON blockfiles
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM team_members
            WHERE team_members.team_id = blockfiles.team_id
              AND team_members.user_id = auth.uid()
        )
    );
```

## Server-side ownership enforcement

RLS provides database-level enforcement, but the service layer also enforces ownership explicitly via `_require_owner()`:

```python
def _require_owner(table: str, row_id: str, user_id: str) -> None:
    row = sb.table(table).select("user_id").eq("id", row_id).single().execute()
    if not row.data or row.data["user_id"] != user_id:
        raise PermissionError(f"Not authorized to modify {table}/{row_id}")
```

This prevents any edge case where RLS might be bypassed (e.g., service-role key usage in server-side APIs).

## API error codes

| Exception | HTTP status |
|---|---|
| `PermissionError` | 403 Forbidden |
| `ValueError` | 404 Not Found (or 422 for validation) |

The `_http(exc)` helper in `evidence_library.py` maps these exceptions to appropriate responses.

## Cross-user isolation

- Users cannot read, modify, or delete another user's resolutions, arguments, cards, blockfiles, or frontlines
- Team read access to blockfiles is granted only for `blockfiles.team_id` members
- Evidence source rows (`evidence_sources`) are shared (no `user_id` column) to enable deduplication, but contain no private information — only bibliographic metadata
- `library_card_metadata` is owned by the card owner; team members cannot see another user's library organization

## Unsupported verdict save guard

Saving a card with `support_verdict = "unsupported"` or `"contradicted"` to the library requires explicit override:

```python
# Raises ValueError unless override is set
save_card_to_library(card_id=..., user_id=..., unsupported_save_override=True)
```

The `SaveToLibraryDialog` frontend component shows an amber warning and requires the user to check a box before the Save button is enabled. This prevents debaters from accidentally building cases on evidence flagged as contradicted.

## Version history and protected fields

Card version history records `previous_values` for all changed fields **except**:
- `body_text`
- `highlighted_spans_json`
- `underline_spans_json`
- `support_verdict`

These fields represent the AI-assessed integrity of the card. They are never overwritten by a version restore. If a user edits metadata (tags, notes, argument assignment), the version is recorded and can be restored. The evidence itself cannot be silently mutated through version restore.
