# Dissio Pilot Runbook — Pass 18

## Overview

This runbook covers how to run the Dissio pilot with 5–30 students and coaches. It covers setup, launch, monitoring, and shutdown.

---

## Pre-Pilot Checklist

### Infrastructure
- [ ] Supabase project created with all migrations applied
- [ ] Storage bucket `speeches` exists with correct policies
- [ ] Service role key configured in backend `.env`
- [ ] CORS origins set to your deployment domain
- [ ] `PILOT_MODE=true` in backend `.env`

### API Keys
- [ ] `OPENAI_API_KEY` configured (required for LLM features)
- [ ] `TAVILY_API_KEY` configured (required for evidence search)
- [ ] Optional: `EXA_API_KEY`, `COHERE_API_KEY`, `JINA_API_KEY`

### Health Check
Run before inviting students:
```
GET /health/readiness
```
Expected: `{ "status": "ok", "checks": { "supabase": { "status": "ok" }, ... } }`

If any check shows `"error"`, fix before proceeding.

### Feature Flags for Pilot
```env
PILOT_MODE=true
DAILY_LLM_BUDGET_USD=1.00
MAX_ROUNDS_PER_USER_DAILY=5
MAX_EVIDENCE_SEARCHES_PER_DAY=20
RESEARCH_ENABLE_LLM_REFINER=true
RESEARCH_ENABLE_CARD_VERIFICATION=true
```

---

## Student Onboarding Flow

1. Student receives signup link → creates account
2. Student lands on `/dashboard` → sees FirstRunCommandCenter (if no speeches)
3. Steps shown (in order):
   - Record your first speech
   - Search for evidence
   - Save your first card
   - Build your tournament prep
   - Run a practice round
   - Complete a drill

Students can skip any step. Progress is tracked in `onboarding_progress` table.

---

## Coach Onboarding Flow

1. Coach creates account and joins/creates team at `/team`
2. Coach adds students to team
3. Coach sees student round list at `/team` overview
4. Coach clicks a student round → opens coach review panel
5. Coach adds annotations, assigns drills

---

## Monitoring During Pilot

### Analytics Queries

**Activation rate (completed first speech):**
```sql
SELECT COUNT(DISTINCT user_id)
FROM product_events
WHERE event_name = 'first_speech_completed'
  AND created_at >= current_date - 7;
```

**Evidence card saves:**
```sql
SELECT COUNT(DISTINCT user_id), COUNT(*)
FROM product_events
WHERE event_name = 'evidence_card_saved'
  AND created_at >= current_date;
```

**Round completions:**
```sql
SELECT COUNT(DISTINCT user_id), COUNT(*)
FROM product_events
WHERE event_name = 'round_completed'
  AND created_at >= current_date - 7;
```

**Workflow failures:**
```sql
SELECT metadata_json->>'stage' AS stage,
       metadata_json->>'error_code' AS error_code,
       COUNT(*) AS count
FROM product_events
WHERE event_name = 'workflow_stage_failed'
  AND created_at >= current_date - 7
GROUP BY stage, error_code
ORDER BY count DESC;
```

**Cost per day:**
```sql
SELECT date, SUM(total_cost_usd) AS total_usd
FROM pilot_cost_summary
GROUP BY date
ORDER BY date DESC;
```

---

## Known Failure Modes and Recovery

### Evidence search returns no results
- Cause: Tavily key expired or rate-limited
- Check: `GET /health/readiness` → check `tavily.status`
- Recovery: Rotate key, then retry search

### Round speech transcription fails
- Cause: OpenAI Whisper timeout or key limit
- Recovery: Student can re-upload audio from the round speech screen
- No data is lost — round state persists

### LLM opponent speech generation fails
- Cause: OpenAI rate limit
- Recovery: Retry button on the round phase screen
- Fallback: Template-based opponent speech is used automatically

### Supabase connection failure
- Cause: Project paused (free tier pauses after 1 week inactive)
- Recovery: Resume project in Supabase dashboard
- Check: `GET /health/supabase`

### Backend restart mid-round
- Cause: Container restart / deploy
- Recovery: Round state is fully persisted — student can reload and continue
- No round data is lost (append-only design)

---

## Data Deletion

If a student requests deletion:
```
DELETE /users/{user_id}
```
This cascade-deletes: rounds, speeches, evidence cards, drills, analytics.
Audio files in Storage are removed best-effort.

If only a round should be deleted:
```
DELETE /round-simulations/{round_id}
```

If only an evidence card should be deleted:
```
DELETE /research/saved-cards/{card_id}?user_id={user_id}
```

---

## Privacy Notes

- Student speech audio is stored in Supabase Storage under `speeches/{user_id}/`
- Transcripts are stored in the `transcripts` table
- Coach notes are stored in `round_coach_annotations` — not visible to students unless the coach shares explicitly
- Analytics events contain `event_name` and `metadata_json` — no speech text or evidence body
- Service role bypasses RLS — never expose service role key to clients

---

## Cost Estimate for Pilot

For 20 students × 3 sessions each:
- Evidence: 20 × 3 × 3 cards × $0.002 = ~$0.36
- Rounds: 20 × 3 × 1 full round × $0.08 = ~$4.80
- Speeches: 20 × 3 × 2 speeches × $0.003 = ~$0.36
- **Estimated total: ~$5.50 for the full pilot**

Monitor daily with `GET /users/{id}/cost-summary` or the `pilot_cost_summary` view.

---

## End-of-Pilot Shutdown

1. Set `PILOT_MODE=false` or revoke API keys
2. Export analytics: `SELECT * FROM product_events WHERE ...`
3. Export quality reports: `SELECT * FROM round_quality_reports`
4. Archive Supabase data before account deletion
5. Send pilot participants a summary of their progress (from pilot dashboard)
