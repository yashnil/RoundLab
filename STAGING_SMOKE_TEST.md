# RoundLab Staging Smoke Test

Run this checklist after deploying to staging (Vercel + Render/Railway) to verify all core flows work correctly.

---

## Prerequisites

- Staging frontend URL (e.g., `https://roundlab-staging.vercel.app`)
- Staging backend URL (e.g., `https://roundlab-api-staging.onrender.com`)
- Two test accounts (for team testing)
- Test audio file or microphone access

---

## 1. Backend Health Check

**Test**: Verify backend is running and accessible.

1. Visit: `https://your-backend-url.onrender.com/health`
2. Expected response: `{"status": "healthy"}`

**Pass/Fail**: ______

---

## 2. Sign Up (Email/Password)

**Test**: New user can create an account with email.

1. Open staging frontend
2. Click "Sign Up"
3. Enter email and password
4. Check email for confirmation link
5. Click confirmation link
6. Should redirect to login or dashboard

**Pass/Fail**: ______

**Notes**: _____________

---

## 3. Sign In (Email/Password)

**Test**: User can sign in with email credentials.

1. Go to login page
2. Enter email and password from step 2
3. Click "Sign In"
4. Should reach dashboard

**Pass/Fail**: ______

---

## 3b. Sign In (Google OAuth)

**Test**: User can sign in with Google account.

**Prerequisites**: Google OAuth must be configured in Supabase (see DEPLOYMENT.md).

1. Go to login page
2. Click "Continue with Google"
3. Should redirect to Google sign-in
4. Sign in with Google account
5. Should redirect to `/auth/callback` briefly (shows "Completing sign-in...")
6. Should then redirect to `/dashboard`
7. Verify user is logged in (shows dashboard content, not login page)

**Expected behavior**: Smooth redirect from Google → callback → dashboard with no errors.

**Common issues**:
- If you see "PKCE code verifier missing": Check Supabase Auth redirect URLs include `/auth/callback`
- If stuck on callback page: Check browser console for errors, verify Supabase keys in `.env.local`
- If redirected back to login with error: Check Supabase OAuth provider is enabled and configured

**Pass/Fail**: ______

**Notes**: _____________

---

## 4. Create Speech

**Test**: User can create a new speech.

1. From dashboard, click "New Speech"
2. Fill in:
   - Title: "Staging Test Speech"
   - Speech Type: Summary
   - Side: Pro
   - Judge Type: Lay
   - Topic: (optional)
3. Click "Create Speech"
4. Should redirect to speech page

**Pass/Fail**: ______

---

## 5. Upload/Record Audio

**Test**: User can upload or record audio.

### Option A: Upload
1. Click "Upload File"
2. Select test audio file (30-90 seconds recommended)
3. Audio should upload successfully

### Option B: Record
1. Click "Start Recording"
2. Grant microphone permission
3. Speak for 30-60 seconds
4. Click "Stop"
5. Click "Save"

**Pass/Fail**: ______

**Notes**: _____________

---

## 6. Transcribe Speech

**Test**: Transcription pipeline works.

1. Click "Transcribe"
2. Wait ~10-20 seconds
3. Transcript should appear
4. Verify transcript matches audio content (approximately)

**Pass/Fail**: ______

**Transcript accuracy**: Good / Acceptable / Poor

---

## 7. Generate Flow

**Test**: Argument extraction pipeline works.

1. Click "Generate Flow"
2. Wait ~20-30 seconds
3. Flow table should appear with:
   - Claims
   - Warrants
   - Evidence (if mentioned)
   - Impacts

**Pass/Fail**: ______

**Flow accuracy**: Good / Acceptable / Poor

---

## 8. Generate Feedback

**Test**: Feedback generation pipeline works.

1. Click "Generate Feedback"
2. Wait ~20-30 seconds
3. Feedback report should appear with:
   - Overall score
   - Dimension scores (Warrants, Weighing, Extensions, etc.)
   - Key strengths (2-3 bullets)
   - Key weaknesses (2-3 bullets)
   - Recommended focus area

**Pass/Fail**: ______

**Feedback specificity**: Specific / Generic / Too vague

---

## 9. Generate Drills

**Test**: Drill generation pipeline works.

1. Click "Generate Drills"
2. Wait ~15-20 seconds
3. Should see 3 personalized drills
4. Each drill should have:
   - Title
   - Skill area
   - Prompt/instructions

**Pass/Fail**: ______

**Drill relevance**: Highly relevant / Somewhat relevant / Not relevant

---

## 10. Record Drill Attempt

**Test**: User can practice a drill.

1. Click "Practice" on one of the drills
2. Read the prompt
3. Click "Start Recording"
4. Speak for 30-60 seconds
5. Click "Stop" and "Save"
6. Drill attempt should be saved

**Pass/Fail**: ______

---

## 11. View Progress Dashboard

**Test**: Dashboard shows user progress.

1. Navigate back to dashboard
2. Verify displayed:
   - Speech count (should be 1+)
   - Drills attempted (should be 1+)
   - Skill radar chart (should show data)
   - Recommended next practice

**Pass/Fail**: ______

---

## 12. Create Team

**Test**: User can create a team.

1. Go to "Team" tab
2. Click "Create New Team"
3. Enter team name: "Staging Test Team"
4. Click "Create"
5. Should see team dashboard with invite code

**Pass/Fail**: ______

**Invite code**: _____________

---

## 13. Join Team (Second Account)

**Test**: Another user can join the team.

1. Open staging frontend in incognito/private window
2. Sign up with a second email
3. Confirm email and sign in
4. Go to "Team" tab
5. Click "Join Team"
6. Enter invite code from step 12
7. Click "Join"
8. Should see team dashboard

**Pass/Fail**: ______

---

## 14. Coach Views Team Dashboard

**Test**: Team owner can see member activity.

1. Go back to first account (team owner)
2. Navigate to "Team" tab
3. Should see:
   - Team member count (should be 2)
   - Student list with activity
   - Speeches count per student
   - Drills attempted per student
   - Last practice date

**Pass/Fail**: ______

---

## 15. Access Control Test

**Test**: User cannot access another user's speech.

1. Copy the URL of the speech created in step 4
2. Sign out
3. Sign in with the second account
4. Paste the speech URL directly
5. Should see 404 or access denied (not the speech data)

**Pass/Fail**: ______

---

## 16. Edge Case: Short Audio

**Test**: System handles very short audio appropriately.

1. Create a new speech
2. Record or upload audio <10 seconds
3. Attempt to transcribe
4. Should show appropriate error or warning

**Pass/Fail**: ______

**Error message**: _____________

---

## 17. Sign Out and Sign In

**Test**: Session persistence works.

1. Sign out
2. Sign in again
3. Navigate to dashboard
4. All previous speeches and drills should still be visible

**Pass/Fail**: ______

---

## Critical Issues Log

Record any blocking issues here:

| # | Issue | Severity | Steps to Reproduce |
|---|-------|----------|-------------------|
| 1 |       | Critical / Major / Minor |  |
| 2 |       | Critical / Major / Minor |  |
| 3 |       | Critical / Major / Minor |  |

---

## Summary

**Total tests**: 17  
**Passed**: ______  
**Failed**: ______  
**Critical issues**: ______

**Ready for pilot testing?** Yes / No / Needs fixes

**Tested by**: _____________  
**Date**: _____________  
**Frontend URL**: _____________  
**Backend URL**: _____________

---

## Notes

- **Critical** = Blocks core workflow, must fix before pilot
- **Major** = Degrades user experience, should fix soon
- **Minor** = Small issue, can fix later

If any test fails, check:
1. Backend logs (Render/Railway dashboard)
2. Frontend logs (Vercel dashboard → Logs)
3. Supabase logs (Supabase dashboard → Logs)
4. Browser console (F12 → Console)
