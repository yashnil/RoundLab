# Dissio Pilot Testing Guide

This guide outlines how to run a safe, structured pilot test with real users.

---

## Pilot Goals

1. **Validate core workflow** — Can students record → transcribe → get feedback → complete drills without friction?
2. **Test feedback quality** — Is the AI feedback specific, actionable, and debate-native?
3. **Identify UX friction** — Where do users get confused or stuck?
4. **Gather product feedback** — What features do users want next?

---

## Who to Test With

### Recommended Pilot Size

- **5-10 students** (novice or JV Public Forum debaters)
- **1-2 coaches or captains** (team admin/oversight role)

### Ideal Pilot Participants

- **Students**:
  - Novice or JV PF debaters
  - Comfortable recording themselves speaking
  - Willing to give honest feedback
  - Have 30-60 minutes for initial testing

- **Coaches**:
  - Lead a middle or high school debate team
  - Want to track student practice
  - Open to testing early-stage tools

### Where to Find Pilot Users

- Local debate teams (contact coaches directly)
- Debate Discord servers (e.g., "Debate Hub", "Public Forum Debate")
- Speech & Debate organizations (contact captains or student leaders)
- Public speaking clubs (Toastmasters Youth Leadership, school speech clubs)

---

## Student Testing Script

Give this to pilot students or walk them through it:

### Setup (5 minutes)

1. Go to [your-app-url.vercel.app]
2. Sign up with your email
3. Check your email and confirm your account
4. Sign in

### Practice a Speech (20-30 minutes)

1. Click **"New Speech"** on the dashboard
2. Fill in speech details:
   - **Title**: "Practice Summary Speech"
   - **Speech Type**: Summary or Final Focus
   - **Side**: Pro or Con (your choice)
   - **Judge Type**: Lay (beginner judge) or Flow (experienced flow judge)
   - **Topic**: (optional, e.g., "Increase renewable energy")

3. Click **"Create Speech"**

4. Record or upload audio:
   - **Option A (Recommended)**: Click **"Start Recording"**, speak for 45-90 seconds, then **"Stop"** and **"Save"**
   - **Option B**: Click **"Upload File"** and upload a pre-recorded audio file

5. Click **"Transcribe"** and wait ~10-20 seconds

6. Review the transcript — does it match what you said?

7. Click **"Generate Flow"** and wait ~20-30 seconds

8. Review the flow table — did it capture your claims, warrants, and impacts correctly?

9. Click **"Generate Feedback"** and wait ~20-30 seconds

10. Read the feedback:
    - Does it make sense?
    - Is it specific to your speech?
    - Are the weaknesses actionable?

11. Click **"Generate Drills"** and wait ~15-20 seconds

12. Review the 3 personalized drills:
    - Do they target your weaknesses?
    - Are the prompts clear?

### Complete a Drill (5-10 minutes)

1. Click **"Practice"** on one of the drills
2. Read the prompt and instructions
3. Click **"Start Recording"**, practice the drill for 30-60 seconds, then **"Stop"** and **"Save"**
4. (Optional) Mark the drill as **"Attempted"** or **"Completed"**

### Check Your Progress (2 minutes)

1. Go back to the **Dashboard**
2. Review:
   - Speech count
   - Drills completed
   - Skill radar chart
   - Recommended next practice

### Provide Feedback (5 minutes)

After completing the flow, answer these questions (send to pilot coordinator):

1. **Was the feedback specific?**
   - Yes / Somewhat / No
   - Example of something that was specific or too generic:

2. **Did the flow match what you said?**
   - Yes / Mostly / No
   - Any major misses or hallucinations?

3. **Did the drill feel useful?**
   - Yes / Somewhat / No
   - What would make it more useful?

4. **Did you know what to click next?**
   - Yes / Sometimes / No
   - Where did you get stuck?

5. **Would you use this before a tournament?**
   - Yes / Maybe / No
   - Why or why not?

6. **What feature do you want most?**
   - (Open response)

---

## Coach Testing Script

Give this to pilot coaches:

### Setup (5 minutes)

1. Go to [your-app-url.vercel.app]
2. Sign up with your email
3. Confirm your email and sign in

### Create a Team (2 minutes)

1. Go to the **Team** tab
2. Click **"Create New Team"**
3. Enter your team name (e.g., "Lincoln High School PF")
4. Click **"Create"**
5. Copy the invite code (e.g., "A1B2C3D4")
6. Share the invite code with your students

### Monitor Student Progress (ongoing)

1. Go to **Team** tab
2. View team dashboard:
   - Member count
   - Student activity (speeches, drills, attempts)
   - Latest practice date per student

3. Check if:
   - Students are practicing regularly
   - Drill attempts are increasing
   - Any students are inactive

### Provide Feedback (5 minutes)

After testing for 1-2 weeks, answer these questions:

1. **Was the team dashboard useful?**
   - Yes / Somewhat / No
   - What data would you want to see?

2. **Did students actually use the tool?**
   - Yes / Some did / No
   - If no, why not?

3. **What feature would make this more useful for coaches?**
   - (Open response — e.g., "See student drill completion rate", "Export feedback reports", "Set team goals")

4. **Would you recommend this to other coaches?**
   - Yes / Maybe / No
   - What would need to change for a "yes"?

---

## Feedback Questions (All Users)

Ask these questions in a follow-up survey (Google Form, Typeform, etc.):

### 1. Was the feedback specific?

- [ ] Yes, very specific
- [ ] Somewhat specific
- [ ] No, too generic

**Example:** (open text)

### 2. Did the flow match what you said?

- [ ] Yes, accurately
- [ ] Mostly, with minor errors
- [ ] No, it missed key points

**Example of an error:** (open text)

### 3. Did the drill feel useful?

- [ ] Yes, very useful
- [ ] Somewhat useful
- [ ] No, not useful

**What would make it more useful?** (open text)

### 4. Did you know what to click next?

- [ ] Yes, always
- [ ] Sometimes
- [ ] No, I was confused

**Where did you get stuck?** (open text)

### 5. Would you use this before a tournament?

- [ ] Yes, definitely
- [ ] Maybe
- [ ] No

**Why or why not?** (open text)

### 6. What feature do you want most?

(Open response)

Examples:
- Evidence upload and highlighting
- Full practice round mode (constructive + rebuttal + summary + FF)
- Case generation
- Tournament prep playlists
- Compare feedback across speeches
- Share drills with teammates

---

## Known Limitations (Tell Pilot Users)

Be transparent about what's **not** in the MVP:

1. **PF-first**: The AI is optimized for Public Forum debate. Other formats (LD, Policy, Congress) are not yet supported.

2. **No evidence upload yet**: You can't paste or upload evidence cards. The AI evaluates based on what you say, not written evidence.

3. **No full-round mode yet**: You can only practice one speech at a time (not a full round with constructive → rebuttal → summary → FF).

4. **No team member removal yet**: Once someone joins a team, only Supabase admin can remove them. (Coaches can't kick members.)

5. **No progress export**: You can't export feedback or drill data to PDF/CSV yet.

6. **No real-time feedback**: You record → transcribe → generate. It's not live commentary during your speech.

---

## Pilot Timeline

### Week 1: Setup + First Practice

- Day 1: Invite students and coaches
- Day 2-3: Students complete first speech flow (record → transcribe → flow → feedback → drills)
- Day 4-7: Students attempt at least one drill

### Week 2: Regular Use

- Students practice 2-3 speeches per week
- Coaches check team dashboard 2-3 times per week
- Collect early feedback

### Week 3: Feedback & Iteration

- Send feedback survey to all users
- Schedule 15-minute Zoom interviews with 3-5 students
- Prioritize top feature requests

---

## Red Flags to Watch For

If you see these patterns, investigate immediately:

1. **No one completes drills** → Drills aren't useful or UI is unclear
2. **Feedback is always generic** → AI prompts need improvement
3. **Flow is always wrong** → Transcription or argument extraction is broken
4. **Students sign up but never create a speech** → Onboarding is confusing
5. **Coaches never check team dashboard** → Dashboard doesn't provide value

---

## Success Metrics

Track these to measure pilot success:

### Engagement
- **Speech creation rate**: How many speeches per student per week?
- **Drill completion rate**: % of assigned drills attempted?
- **Return rate**: % of students who practice more than once?

### Quality
- **Feedback specificity**: % of students who say feedback is "very specific"?
- **Flow accuracy**: % of students who say flow "accurately" matches their speech?
- **Drill usefulness**: % of students who say drills are "very useful"?

### Intent
- **Would use before tournament**: % of students who say "yes, definitely"?
- **Would recommend**: % of students who would recommend to a teammate?

---

## Post-Pilot Next Steps

After pilot testing:

1. **Aggregate feedback** — What are the top 3 feature requests?
2. **Fix critical issues** — Any bugs or broken flows?
3. **Prioritize roadmap** — What to build next (evidence upload, full rounds, etc.)?
4. **Decide on pricing** — Free tier + paid plans, or fully free for now?
5. **Plan public launch** — Expand to more teams or open to public?

---

## Contact for Pilot Support

**Email**: yashnilmohanty@gmail.com

**Response time**: Within 24 hours for pilot participants

**Office hours**: (Optional) Schedule weekly 30-minute Q&A sessions for pilot users
