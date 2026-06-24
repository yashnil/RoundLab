# Round Simulation Permissions

## Row-Level Security

All 9 new tables have RLS enabled with two policies each:

```sql
-- Students can only access their own rounds
CREATE POLICY "user owns round" ON round_simulations
  FOR ALL USING (auth.uid() = user_id);

-- Service role bypass for background operations
CREATE POLICY "service_role bypass" ON round_simulations
  FOR ALL USING (auth.role() = 'service_role');
```

The same pattern applies to: `round_participants`, `round_speeches`, `round_crossfire_exchanges`, `round_arguments`, `round_flow_events`, `round_evidence_uses`, `round_decisions`, `round_drills`, `opponent_round_plans`, `round_adaptation_reviews`.

## API-Level Ownership Check

Every endpoint that operates on an existing round calls `_verify_owner()`:

```python
async def _verify_owner(round_id: str, user_id: str) -> dict:
    resp = supabase.table("round_simulations").select("*").eq("id", round_id).execute()
    if not resp.data:
        raise HTTPException(404)
    if resp.data[0]["user_id"] != user_id:
        raise HTTPException(403)
    return resp.data[0]
```

This is defense-in-depth: even if an RLS policy were misconfigured, the API layer independently blocks cross-user access.

## Card Ownership

Before building an opponent plan, `_fetch_approved_cards()` filters by `user_id == requesting_user_id`. A card owned by a different user is silently excluded, preventing card sharing even if its UUID is passed.

## Prep Gap Writes

`record_post_round_gaps()` only inserts gap records for the requesting user's `prep_plan_id`. It does not read or modify other users' prep plans.

## What Service Role Can Do

The service role bypass is only used for background operations initiated by the API handler itself (not user-initiated). The API handler has already performed ownership validation before any service-role call.
