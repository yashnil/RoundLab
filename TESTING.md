# Dissio Testing Guide

This guide covers testing workflows, golden samples for calibration, and dev-only tools.

---

## Testing Golden / High-Scoring Speeches

### What is the Golden Sample?

Dissio includes a high-quality PF summary speech transcript designed to score 85-95/100. Use it to:
- Calibrate what a tournament-ready performance looks like
- Test the scoring rubric
- Verify feedback quality at the high end

### How to Use (Development/Staging Only)

The `/dev/demo-speech` endpoint is **only available when `ENVIRONMENT != "production"`**.

#### Step 1: Create Demo Speech

Use the dev endpoint to create a speech with the golden transcript:

```bash
curl -X POST "http://localhost:8000/dev/demo-speech?user_id=YOUR_USER_ID"
```

Or using JavaScript in the browser console:
```javascript
const userId = "your-supabase-user-id";
fetch(`http://localhost:8000/dev/demo-speech?user_id=${userId}`, { method: "POST" })
  .then(r => r.json())
  .then(console.log);
```

The response includes:
```json
{
  "speech_id": "abc123...",
  "transcript_id": "def456...",
  "message": "Demo speech created. Now generate flow → feedback → drills to see what a high-quality performance looks like. Expected score: 85-95/100."
}
```

#### Step 2: Generate Flow, Feedback, and Drills

1. Go to the speech page: `http://localhost:3000/speech/{speech_id}`
2. The transcript is already present (no audio needed)
3. Click **"Generate Flow"**
4. Click **"Generate Feedback"**
5. Review the score (should be 85-95/100)
6. Click **"Generate Drills"**

#### Step 3: Compare with Real Speeches

Use the golden sample as a reference when evaluating real student speeches:
- What's different about the warranting?
- Does the golden sample weigh impacts explicitly?
- Are extensions and drops handled correctly?

### Golden Transcript Content

The sample is a PF summary speech on renewable energy that includes:
- ✓ Clear claim-warrant-impact structure on 3 contentions
- ✓ Explicit magnitude, probability, and timeframe weighing
- ✓ Extensions from prior speeches
- ✓ Identification of dropped arguments
- ✓ Judge adaptation (mentions both lay and flow judges)
- ✓ Voter language and decision calculus

Location: `backend/app/examples/golden_pf_summary.txt`

---

## Manual Testing Checklist

### Core Workflow (Required Before Deployment)

1. **Sign up and sign in**
   - [ ] Email/password sign up works
   - [ ] Email/password sign in works
   - [ ] Google OAuth sign-in works (if configured)
   - [ ] Confirmation email received (if required)

2. **Create speech**
   - [ ] "New Speech" creates a session
   - [ ] All speech types selectable
   - [ ] Judge types selectable

3. **Record/upload audio**
   - [ ] Recording works (30-60 seconds)
   - [ ] Upload works (MP3, M4A, WAV)
   - [ ] Audio saved correctly

4. **Transcribe**
   - [ ] Transcription completes (~10-20 seconds)
   - [ ] Transcript matches audio
   - [ ] Word count displayed

5. **Generate flow**
   - [ ] Flow generation completes (~20-30 seconds)
   - [ ] Claims, warrants, evidence, impacts extracted
   - [ ] Argument cards displayed

6. **Generate feedback**
   - [ ] Feedback generation completes (~20-30 seconds)
   - [ ] Overall score present (1-100)
   - [ ] Category scores add up correctly
   - [ ] Strengths and weaknesses specific
   - [ ] Decision logic present

7. **Generate drills**
   - [ ] Drill generation completes (~15-20 seconds)
   - [ ] Exactly 3 drills generated
   - [ ] Each drill targets a different skill
   - [ ] Drills reference specific weaknesses

8. **Drill attempts**
   - [ ] Can record drill attempt
   - [ ] Attempt saves correctly
   - [ ] Attempt count updates

9. **Progress dashboard**
   - [ ] Speech count correct
   - [ ] Drills assigned count correct
   - [ ] Drill attempts count correct
   - [ ] Skill breakdown displayed

10. **Team features**
    - [ ] Can create team
    - [ ] Invite code generated
    - [ ] Can join team with code
    - [ ] Coach sees team dashboard
    - [ ] Student activity visible

11. **Delete session**
    - [ ] Delete confirms with dialog
    - [ ] Delete removes session
    - [ ] Dashboard updates after delete
    - [ ] If delete fails, error shown

---

## Scoring Consistency Test

To verify scoring stability (same input → similar output):

1. Create two separate speeches with the **exact same audio file**
2. Transcribe both
3. Generate flow for both
4. Generate feedback for both
5. **Compare overall scores** — they should be within ±3-5 points
6. If variance is >10 points, investigate:
   - Was the transcript identical?
   - Were any fields (speech_type, judge_type, side) different?
   - Check backend logs for errors

With `temperature=0.0` in feedback generation, identical transcripts should produce nearly identical scores.

---

## Edge Case Testing

### Short Audio (<30 seconds)

- [ ] Transcript generated but with low word count
- [ ] Feedback shows calibration note: "short transcript, scored conservatively"
- [ ] Score capped appropriately (typically <60)

### Long Audio (>5 minutes)

- [ ] Transcription completes successfully
- [ ] Flow extraction handles long text
- [ ] Feedback generation doesn't timeout

### No Evidence Cited

- [ ] Feedback notes lack of evidence
- [ ] Evidence score is low (0-5)
- [ ] Drill targets evidence use

### Perfect Speech (Golden Sample)

- [ ] Score is 85-95/100
- [ ] Feedback highlights strengths
- [ ] Drills still suggest areas for refinement

### Access Control

- [ ] Cannot view another user's speech (404)
- [ ] Cannot delete another user's speech (404)
- [ ] Cannot update another user's drill (404)

---

## Load Testing (Optional)

For staging/production readiness:

1. Create 10 speeches sequentially
2. Generate feedback for all 10
3. Verify all complete successfully
4. Check OpenAI API usage and costs
5. Verify Supabase DB and storage usage

---

## Dev-Only Endpoints

These endpoints are **disabled in production** via `ENVIRONMENT` check:

### `POST /dev/demo-speech?user_id={user_id}`

Creates a demo speech with the golden high-quality transcript.

**Availability**: `ENVIRONMENT != "production"`

**Response**:
```json
{
  "speech_id": "uuid",
  "transcript_id": "uuid",
  "message": "Demo speech created. Expected score: 85-95/100."
}
```

**Security**: Requires `user_id` query param. Only creates speeches for the authenticated user. Disabled in production.

---

## Troubleshooting

### Feedback score is always low (<50)

- Check if transcript is too short
- Verify OpenAI API key has credits
- Compare against golden sample

### Feedback score varies wildly (>15 points) for same input

- Before fix: `temperature=1.0` (default) caused variance
- After fix: `temperature=0.0` ensures determinism
- Verify `temperature=0.0` is set in `backend/app/services/feedback_generation.py`

### Demo endpoint returns 403

- Check `ENVIRONMENT` variable in backend `.env`
- Must be `development` or `staging`, not `production`

### Google sign-in doesn't redirect

- Verify redirect URL in Google Cloud Console
- Check Supabase Auth → URL Configuration
- Ensure `https://YOUR_PROJECT.supabase.co/auth/v1/callback` is in Google OAuth config

---

## Contact

For testing issues or questions: yashnilmohanty@gmail.com
