# Project Plan: Dissio

## 1. Core concept

**Dissio** is an AI practice and feedback platform for speech and debate students.

The initial version should focus on **Public Forum debate** , because PF has a clear structure, a
large novice/JV user base, and strong alignment with your own experience and FSI network.

### One-line pitch

```
Dissio helps debaters record speeches, get AI-generated flows and
ballot-style feedback, identify dropped or underdeveloped arguments, and
practice targeted drills to improve faster.
```
### YC-lite framing

This should not start as “AI for debate education broadly.”

It should start as:

```
An AI flow coach for novice and JV Public Forum debaters who do not have
consistent access to high-quality coaching.
```
That is concrete, useful, and testable.

## 2. Why this is a good idea

Existing products cover pieces of the space, but not the full training loop.

**Yoodli** is a strong AI communication coach focused on public speaking, roleplay, pacing, filler
words, word choice, and presentation feedback, but it is not deeply debate-native. (Yoodli)

**Symbai** is closer to debate: it provides AI-powered debate coaching, structured practice,
rebuttal sharpening, and critical-thinking development for individuals and schools. (Symbai)

**PublicForumAI** is directly PF-focused and offers AI flowing, full practice rounds, speech
recognition, and case generation. (Public Forum AI)

The opportunity is to make something more **coach-like and improvement-loop oriented** :


```
Existing tools help students practice. Dissio should help students understand
why they are losing rounds and what exact skill to practice next.
```
Your novelty should be:

1. **Flow-first feedback** , not generic speech feedback.
2. **Dropped-argument and extension analysis** , not just “good job, be clearer.”
3. **Ballot-style RFDs from different judge perspectives.**
4. **Personalized drills generated from actual speech mistakes.**
5. **Coach/team dashboard** for tracking progress across students.
6. **Evidence-aware feedback** that checks whether claims, warrants, and cards are being
    used properly.

## 3. Target users

### Initial user

**Novice and JV Public Forum debaters.**

Especially:

```
● Students at small schools
● Students without private coaching
● Middle school debaters
● FSI students
● New debate club members
● Students preparing alone before tournaments
```
### Secondary user

**Debate coaches and club captains.**

They need to:

```
● Track student progress
● Give scalable feedback
● Assign practice drills
● Help novices understand round structure
● Manage large teams without one-on-one coaching for everyone
```
### Later users

```
● LD debaters
● Congress students
● Extemp students
```

```
● Original Oratory students
● Debate camps
● Middle school enrichment programs
● Public speaking nonprofits
● Schools without established debate infrastructure
```
## 4. Product wedge

Start with one promise:

```
Upload or record a PF speech. Dissio flows it, judges it, and gives you
three personalized drills.
```
That is the MVP.

Do not begin with full tournaments, full team management, evidence libraries, every debate
event, and full AI opponents. Those are later.

The summer goal should be to make one core workflow excellent.

## 5. Core user workflow

### Student flow

1. Student creates an account.
2. Student chooses event: **Public Forum**.
3. Student selects speech type:
    ○ Constructive
    ○ Rebuttal
    ○ Summary
    ○ Final Focus
    ○ Crossfire response practice
4. Student records or uploads audio.
5. System transcribes speech.
6. System extracts arguments.
7. System creates a flow-style breakdown.
8. System gives ballot-style feedback.
9. System identifies:
    ○ Missing warrant
    ○ Weak extension
    ○ No weighing
    ○ Dropped response
    ○ Unclear impact
    ○ Unsupported claim


```
○ New argument in later speech
```
10. System generates 3 drills.
11. Student completes a drill.
12. Student re-records.
13. System compares old vs. new attempt.

That loop is the heart of the product.

## 6. Main application modules

## Module A: Speech recording and upload

### Functionality

Users can:

```
● Record directly in browser
● Upload audio files
● Eventually upload video
● Select speech type
● Add topic/resolution
● Add side: Pro or Con
● Add judge type: lay, flow, tech, parent, coach
● Add optional opponent arguments for context
```
### Why it matters

This is the entry point. The experience should feel simple and fast.

### Tools

```
● Next.js MediaRecorder API for browser recording
● Supabase Storage for saving audio
● Whisper API , Deepgram , or AssemblyAI for transcription
```
For MVP, I would use **OpenAI Whisper API** because it is simple and reliable. Later, Deepgram
or AssemblyAI may be better for real-time transcription and diarization.

## Module B: Transcription layer

### Functionality


The system converts audio into text and stores:

```
● Full transcript
● Timestamped transcript
● Speaking rate
● Pauses
● Filler words
● Repeated phrases
● Estimated word count
● Speech duration
```
### Tools

```
● Whisper API for transcription
● Optional: Deepgram for diarization/real-time mode later
● Python text processing for filler words and pacing
```
### Data saved

speech_id
user_id
event_type
speech_type
audio_url
transcript
duration_seconds
words_per_minute
filler_word_count
created_at

## Module C: Argument extraction

### Functionality

Given a transcript, the AI extracts:

```
● Main contentions
● Subpoints
● Claims
● Warrants
● Evidence
● Impacts
```

```
● Weighing language
● Responses/refutations
● Cross-applications
● Voters
● Summary/final focus extensions
```
### Example output

#### {

"contentions": [
{
"label": "Contention 1",
"claim": "The plan improves rural healthcare access.",
"warrant": "Telehealth reduces geographic barriers and specialist shortages.",
"evidence": "The speaker references a 2023 study but does not identify the author clearly.",
"impact": "Improved treatment access and reduced mortality.",
"issues": ["evidence attribution unclear", "impact magnitude not quantified"]
}
]
}

### Tools

```
● LLM structured outputs
● Pydantic schemas
● LangGraph node for extraction
● Postgres JSONB to store argument maps
```
### Important design principle

Use structured outputs, not loose paragraphs. The app should feel analytical.

## Module D: Flow builder

### Functionality

The app converts a speech into a debate flow.

For a single speech, it shows:


```
Argument Claim Warrant Evidenc
e
```
```
Impact Strengt
h
```
```
Issu
e
```
For multiple speeches later, it should show argument evolution:

```
Argument Constructiv
e
```
```
Rebuttal Summary Final
Focus
```
```
Status
```
```
Pro C1 Introduced Attacked Extended Weighed Live
```
```
Con C2 Introduced Dropped Not
extended
```
```
Not in FF Dropped
```
### MVP version

Start with one uploaded speech. Later support full-round flow.

### Tools

```
● Next.js table UI
● shadcn/ui DataTable
● Postgres JSONB
● LLM argument mapping
```
### Novelty

This is where Dissio becomes debate-native. Many tools can transcribe and summarize;
fewer can produce a usable debate flow.

## Module E: Debate feedback engine

### Functionality

The feedback engine evaluates the speech using debate-specific rubrics.

It should score:

1. Argument structure
2. Warrant clarity
3. Evidence use
4. Impact explanation


5. Clash/refutation
6. Weighing
7. Organization
8. Strategic focus
9. Delivery clarity
10. Judge adaptation

### Example feedback

Instead of:

```
“You need stronger analysis.”
```
It should say:

```
“Your summary extends the healthcare access impact, but it does not extend the
warrant from constructive explaining why telehealth solves specialist shortages. A
flow judge may not evaluate the impact if the internal link is missing.”
```
That is the level you want.

### Tools

```
● LLM rubric evaluator
● Custom scoring schema
● DeepEval/custom evals to test feedback quality
● Human-labeled examples from you and debate friends
```
## Module F: Ballot-style RFD generator

### Functionality

The app generates a judge ballot:

```
● Winner: optional in full-round mode
● Reason for decision
● Speaker points estimate
● Strengths
● Main voting issue
● What the debater needed to do to win
● Judge paradigm selected by user
```

### Judge modes

1. **Lay judge**
    ○ Persuasiveness
    ○ Clarity
    ○ Real-world explanation
    ○ Less technical jargon
2. **Flow judge**
    ○ Extensions
    ○ Drops
    ○ Weighing
    ○ Line-by-line responses
3. **Tech judge**
    ○ Argument resolution
    ○ Conceded offense
    ○ Precise weighing
    ○ Minimal intervention
4. **Coach judge**
    ○ Educational feedback
    ○ Skill development
    ○ Improvement areas

### Why this is useful

Students need to learn that the same speech sounds different to different judges. This is a major
PF skill.

## Module G: Personalized drill generator

This should be one of your killer features.

### Functionality

After feedback, the app generates specific drills.

Examples:

**Weak warrant drill**

```
Re-explain your warrant in 45 seconds without using evidence. Focus only on the
causal chain.
```
**Weighing drill**


```
Compare your impact against the opponent’s impact using magnitude, probability,
and timeframe.
```
**Rebuttal drill**

```
Respond to this argument in 30 seconds using claim-warrant-impact structure.
```
**Summary extension drill**

```
Extend your best offensive argument in 60 seconds, including claim, warrant,
evidence, impact, and weighing.
```
**Lay judge drill**

```
Explain your argument to a parent judge using no jargon.
```
### Tools

```
● LLM drill generation
● Saved drill templates
● Speech re-recording
● Progress comparison
```
### Data saved

drill_id
speech_id
skill_target
instructions
time_limit_seconds
student_response_audio
student_response_transcript
score_before
score_after

## Module H: Progress dashboard

### Functionality

Students see progress over time.

Metrics:


```
● Average warrant score
● Weighing score
● Evidence clarity
● Organization
● Delivery pacing
● Filler word count
● Speech completion rate
● Drill completion rate
● Improvement after re-recording
```
### UI

Use simple charts:

```
● Skill radar chart
● Speech history timeline
● Drill completion streak
● Before/after comparisons
● “Your next skill to practice”
```
### Tools

```
● Recharts
● PostHog for product analytics
● Supabase/Postgres for user metrics
```
## Module I: Evidence/case upload

This is the next major feature after the core MVP.

### Functionality

Students upload:

```
● Constructive cases
● Blocks
● Evidence docs
● Research PDFs
● Cut cards
● Frontlines
```
The app can:


```
● Extract cards
● Identify tags, authors, dates, sources
● Summarize evidence
● Check whether the card supports the claim
● Suggest crossfire questions
● Suggest possible responses
● Build a mini evidence library
```
### Why it is powerful

This moves you beyond speech feedback into real debate prep.

### Tools

```
● PyMuPDF for PDF parsing
● python-docx for Word files
● Google Docs export/import later
● LlamaIndex or LangChain for RAG
● pgvector for semantic search
● Citation extraction with regex + LLM cleanup
```
### Important safety/ethics

The tool should not fabricate evidence. It should make unsupported claims visible.

Use messages like:

```
“I could not verify this evidence from the uploaded document.”
```
or:

```
“The card appears to support the general claim, but not the specific impact
magnitude stated in your tag.”
```
## Module J: Coach/team dashboard

This is not MVP day one, but it is important for monetization.

### Functionality

Coaches can:

```
● Create a team
```

```
● Invite students
● Assign drills
● View student progress
● Review uploaded speeches
● Leave comments
● Track skill gaps by team
● Export reports before tournaments
```
### Why this matters

Individual students may not pay much. Teams, camps, and schools are more likely to pay.

### Tools

```
● Supabase organization/team tables
● Role-based access control
● Team analytics dashboard
● Stripe subscriptions later
```
# 7. Technical architecture

## Recommended MVP architecture

Next.js frontend
↓
FastAPI backend
↓
Supabase Auth / Postgres / Storage
↓
Whisper transcription API
↓
LangGraph processing pipeline
↓
LLM structured outputs
↓
Postgres stores transcripts, flows, feedback, drills
↓
Next.js dashboard renders results


## Why this architecture is good for you

It teaches:

```
● Full-stack development
● API design
● Auth and storage
● AI orchestration
● Speech processing
● Structured LLM outputs
● Database schema design
● Product analytics
● Evaluation
● Deployment
```
It also avoids overengineering. You do not need GPUs, Kubernetes, or custom model training at
first.

# 8. Recommended stack

## Frontend

### Use

```
● Next.js
● React
● TypeScript
● Tailwind CSS
● shadcn/ui
● Recharts
● Framer Motion lightly
```
### Why

This is the modern startup frontend stack. It helps you build a polished product quickly.

### Frontend pages

1. Landing page
2. Login/signup


3. Dashboard
4. Record speech
5. Upload speech
6. Speech feedback report
7. Flow table
8. Drill practice page
9. Progress analytics
10. Team dashboard later

## Backend

### Use

```
● FastAPI
● Python
● Pydantic
● Uvicorn
● Celery or Dramatiq later for background jobs
```
### Why

FastAPI is excellent for AI/ML backends. It gives you clean APIs and lets you integrate Python
ML/NLP tools easily.

### Backend endpoints

POST /speeches/upload
POST /speeches/transcribe
POST /speeches/analyze
GET /speeches/{id}
GET /speeches/{id}/feedback
POST /drills/{id}/submit
GET /users/{id}/progress
POST /documents/upload
POST /documents/search

## Database

### Use


```
● Supabase Postgres
● pgvector
● Supabase Storage
● Supabase Auth
```
### Why

Supabase gives you auth, database, storage, and vector search in one place. Great for a
summer build.

### Core tables

users
teams
team_members
speeches
transcripts
argument_maps
feedback_reports
drills
drill_attempts
documents
document_chunks
evidence_cards
skill_metrics

## Speech-to-text

### MVP choice

```
● OpenAI Whisper API
```
### Later options

```
● Deepgram for real-time transcription
● AssemblyAI for speaker diarization and audio intelligence
```
### Why

Whisper is easiest to start. Real-time speech recognition can come later.


## LLMs

### Use

```
● OpenAI GPT-4.1 / GPT-4o / GPT-5 class model if available in your account
● Optionally compare with Claude and Gemini
```
### Why

You want strong reasoning and structured output reliability.

### Tasks for LLM

```
● Argument extraction
● Flow building
● Debate rubric scoring
● Ballot generation
● Drill generation
● Evidence support checking
● Student-friendly explanations
```
## Agent orchestration

### Use

```
● LangGraph
```
### Why

LangGraph lets you build a multi-step AI pipeline without making the system chaotic.

### Graph nodes

1. Transcription node
2. Transcript cleanup node
3. Speech segmentation node
4. Argument extraction node
5. Flow construction node
6. Rubric evaluation node
7. Judge-perspective feedback node
8. Drill generation node
9. Storage node


This is a great way to learn modern agent architecture.

## RAG and document processing

### Use

```
● LlamaIndex or LangChain
● PyMuPDF
● python-docx
● pgvector
● OpenAI embeddings or local sentence-transformer embeddings
```
### RAG use cases

```
● Search uploaded case docs
● Retrieve relevant cards
● Compare speech claims to evidence
● Suggest frontlines from evidence library
● Generate crossfire questions from case materials
```
## Evaluation

### Use

```
● DeepEval
● RAGAS
● Custom rubric tests
● Human review by debate friends/coaches
```
### What to evaluate

1. Does the transcript match the audio?
2. Did the system correctly identify the main arguments?
3. Did it distinguish claim/warrant/evidence/impact?
4. Did it correctly identify missing weighing?
5. Did it avoid hallucinating evidence?
6. Was the feedback actionable?


7. Did the drill match the actual weakness?

### Build a test set

Create 20–30 sample speeches:

```
● Good constructive
● Bad constructive
● Rebuttal with no clash
● Summary with dropped offense
● Final focus with new argument
● Speech with evidence but no warrant
● Speech with weighing but no extension
● Speech with strong delivery but weak argument logic
```
Label them yourself.

This will make your product much stronger than a generic LLM wrapper.

## Analytics

### Use

```
● PostHog
```
### Track

```
● Number of speeches uploaded
● Time from upload to feedback
● Drill completion rate
● Re-record rate
● Most common weaknesses
● Retention by week
● Which feedback users mark helpful/unhelpful
```
This teaches you startup/product thinking.

## Payments

Not needed immediately, but later use:


```
● Stripe
```
Possible pricing:

```
● Free: 3 speech analyses/month
● Student Pro: $8–$12/month
● Team: $99–$249/month
● FSI/nonprofit access: free or discounted
```
## Deployment

### Use

```
● Vercel for frontend
● Railway , Render , or Fly.io for FastAPI backend
● Supabase for database/auth/storage
● Modal later for background AI jobs
```
This is simple and modern.

# 9. Functional specification

## MVP v1: “Speech → Flow → Feedback → Drills”

### Must-have features

1. User login
2. Record/upload PF speech
3. Transcribe audio
4. Display transcript
5. Extract argument structure
6. Generate flow table
7. Score speech using debate rubric
8. Generate ballot-style feedback
9. Generate 3 personalized drills
10. Save speech history
11. Show progress dashboard


### Nice-to-have features

1. Evidence upload
2. Compare two speech attempts
3. Judge perspective selector
4. Team dashboard
5. Full practice round mode
6. Crossfire simulator
7. Google Docs export
8. Coach comments
9. Public leaderboard/streaks
10. Topic-specific practice packs

# 10. Data schema draft

## users

id
email
name
created_at
role

## speeches

id
user_id
team_id
event_type
speech_type
topic
side
judge_type
audio_url
duration_seconds
created_at

## transcripts


id
speech_id
text
timestamped_segments
words_per_minute
filler_count
created_at

## argument_maps

id
speech_id
arguments_json
contentions_json
responses_json
weighing_json
created_at

## feedback_reports

id
speech_id
overall_score
warrant_score
weighing_score
evidence_score
organization_score
delivery_score
rfd
strengths_json
weaknesses_json
recommendations_json
created_at

## drills

id
speech_id
skill_target
title
instructions


time_limit_seconds
created_at

## drill_attempts

id
drill_id
user_id
audio_url
transcript
score
feedback
created_at

## documents

id
user_id
team_id
filename
file_url
doc_type
created_at

## document_chunks

id
document_id
chunk_text
embedding
metadata_json
created_at

# 11. AI pipeline design

## Step 1: Transcription


Input:

audio file

Output:

timestamped transcript

## Step 2: Transcript cleanup

Fix obvious transcription issues, but preserve original meaning.

Output:

cleaned transcript

## Step 3: Speech segmentation

Break speech into sections:

```
● Intro/framework
● Contention 1
● Contention 2
● Responses
● Weighing
● Voters
● Conclusion
```
## Step 4: Argument extraction

Extract:

```
● Claims
● Warrants
● Evidence
● Impacts
● Responses
● Weighing
```
## Step 5: Debate rubric scoring


Score each dimension from 1–5.

## Step 6: Ballot generation

Generate feedback based on judge type.

## Step 7: Drill generation

Generate 3 drills from weaknesses.

## Step 8: Save and visualize

Store structured result and show dashboard.

# 12. Prompting strategy

Do not ask the LLM:

```
“Give feedback on this speech.”
```
That will produce generic comments.

Instead, force structured steps.

### Example extraction prompt goal

```
Extract all debate-relevant arguments from this Public Forum speech. For each
argument, identify claim, warrant, evidence, impact, and whether each component
is explicit, implied, or missing.
```
### Example evaluation prompt goal

```
Evaluate the speech as a PF flow judge. Do not give generic public speaking
feedback unless it affects debate performance. Identify missing extensions, weak
warrants, absent weighing, and unclear offense.
```
### Example drill prompt goal


```
Based only on the identified weaknesses, generate three drills. Each drill should
have a time limit, instructions, success criteria, and an example of a strong
response.
```
Use JSON outputs with Pydantic validation.

# 13. Product design principles

## Principle 1: Specific beats generic

Bad:

```
“Improve your argumentation.”
```
Good:

```
“Your impact is clear, but your internal link is missing. Re-explain why your evidence
proves the link between policy and outcome.”
```
## Principle 2: Feedback must be actionable

Every weakness should produce a drill.

## Principle 3: Do not hallucinate evidence

If the student cites evidence unclearly, say that.

## Principle 4: Debate-native language matters

Use terms students recognize:

```
● Flow
● Extend
● Drop
● Frontline
● Weighing
● Link
● Impact
● Warrant
```

```
● Collapse
● Voter
● RFD
```
## Principle 5: Novices need explanation

For novice mode, define terms gently.

Example:

```
“You dropped this argument, meaning you did not respond to it. In a debate round,
dropped arguments are often treated as conceded.”
```
## Principle 6: The app should encourage learning, not

## outsourcing

Do not make the main value “generate cases for me.”

Make it:

```
“Practice better and understand your mistakes.”
```
That will make it more ethical and more educational.

# 14. Competitive positioning

## Against Yoodli

Yoodli helps with public speaking and communication practice. Dissio helps with
**competitive debate strategy** : flows, drops, warrants, extensions, and judge decisions. (Yoodli)

## Against Symbai

Symbai offers AI debate coaching and critical-thinking practice. Dissio should differentiate
by going deep into **PF-specific speech analysis, flow tables, ballot-style RFDs, and drills
generated from actual uploaded speeches**. (Symbai)

## Against PublicForumAI


PublicForumAI already offers PF AI flowing, case generation, and full practice rounds.
Dissio should not simply copy “practice against AI.” Its wedge should be **post-speech
improvement analytics and coach/team workflows**. (Public Forum AI)

## Unique positioning

```
Dissio is the AI assistant coach that turns every practice speech into a
flow, a ballot, and a personalized training plan.
```
# 15. Summer build roadmap

## Week 1: Product discovery and setup

### Goals

```
● Validate the idea
● Define MVP
● Set up technical foundation
```
### Tasks

```
● Interview 10–15 debaters/coaches
● Ask what feedback they wish they got more often
● Collect 10 sample speeches
● Create landing page
● Set up GitHub repo
● Set up Next.js app
● Set up Supabase
● Set up FastAPI backend
```
### Deliverables

```
● Landing page
● Product requirements doc
● Initial database schema
● 10 sample speeches/transcripts
```

## Week 2: Recording and transcription

### Goals

Build the basic upload/recording pipeline.

### Tasks

```
● Browser audio recording
● Audio upload to Supabase Storage
● Whisper transcription
● Transcript display page
● Save speech metadata
```
### Deliverables

```
● User can record a speech
● Speech gets transcribed
● Transcript is saved and displayed
```
## Week 3: Argument extraction and flow table

### Goals

Turn transcripts into structured debate analysis.

### Tasks

```
● Create Pydantic schemas
● Build LLM extraction prompt
● Extract claims/warrants/evidence/impacts
● Render flow table
● Add manual correction option if possible
```
### Deliverables

```
● Speech → argument map
● Flow table UI
● Saved structured JSON
```

## Week 4: Feedback and ballot engine

### Goals

Generate useful debate-native feedback.

### Tasks

```
● Create PF rubric
● Build judge perspective selector
● Generate RFD
● Score speech
● Identify top 3 weaknesses
● Show feedback report
```
### Deliverables

```
● Flow judge feedback
● Lay judge feedback
● Score breakdown
● Ballot-style report
```
## Week 5: Drill generator and re-record loop

### Goals

Turn feedback into practice.

### Tasks

```
● Generate drills from weaknesses
● Add drill practice page
● Let user record drill response
● Score drill attempt
● Compare first speech vs drill response
```
### Deliverables

```
● Personalized drills
● Drill attempts
● Basic progress loop
```

## Week 6: Evidence/case upload beta

### Goals

Add RAG and document intelligence.

### Tasks

```
● Upload PDF/DOCX case files
● Parse and chunk documents
● Embed chunks into pgvector
● Search evidence library
● Link speech claims to uploaded evidence
● Flag unsupported claims
```
### Deliverables

```
● Evidence library
● Basic evidence support checker
● Searchable case docs
```
## Week 7: Progress dashboard and pilot

### Goals

Make the app useful for repeated use.

### Tasks

```
● Add speech history
● Add progress metrics
● Add skill trend charts
● Pilot with 5–10 students
● Collect feedback
● Fix confusing outputs
```
### Deliverables

```
● User dashboard
```

```
● Progress analytics
● Pilot feedback notes
```
## Week 8: Polish and launch

### Goals

Ship something public and impressive.

### Tasks

```
● Improve UI
● Add onboarding
● Add demo data
● Record demo video
● Write technical blog post
● Create pitch deck
● Prepare GitHub README or private architecture doc
```
### Deliverables

```
● Live product
● Demo video
● Technical writeup
● Pitch deck
● User testimonials if possible
```
# 16. MVP success metrics

You need measurable goals.

## Product metrics

```
● 25 users try it
● 100 speeches uploaded
● 60% of users complete at least one drill
● 30% return for a second speech
● 80% of users rate feedback as useful
```

```
● Average feedback generation under 2 minutes
```
## Learning metrics

```
● You can explain RAG
● You can deploy a full-stack app
● You can build structured LLM outputs
● You can design model evals
● You can implement auth/storage/database
● You can run a user pilot
● You can discuss tradeoffs in AI product design
```
## Impact metrics

```
● Students report clearer understanding of weaknesses
● Students improve between first and second recording
● Coaches say the tool saves feedback time
● FSI or a small team uses it during practice
```
# 17. What to avoid

Avoid these traps:

1. **Do not build every debate event at once.**
2. **Do not focus on case generation first.**
3. **Do not make feedback generic.**
4. **Do not rely only on one giant prompt.**
5. **Do not skip evaluation.**
6. **Do not overbuild team features before students like the core flow.**
7. **Do not train your own model at the start.**
8. **Do not make the app feel like cheating. Make it feel like coaching.**

# 18. Version roadmap

## V1: Speech feedback


Record/upload speech → transcript → flow → feedback → drills.

## V2: Full practice round

AI opponent gives speeches and crossfire questions.

## V3: Evidence-aware coach

Upload cases/evidence → feedback references actual evidence.

## V4: Team dashboard

Coaches assign drills and monitor student growth.

## V5: Multi-event expansion

LD, Congress, Extemp, OO, Impromptu.

## V6: Tournament prep mode

Topic briefs, case testing, frontlines, judge adaptation, round simulation.

# 19. Final product vision

Long-term, Dissio could become:

```
The AI practice infrastructure for speech and debate teams.
```
Not a replacement for coaches, but a way for students to get more reps between practices.

The strongest product loop is:

Practice speech
↓
AI flow + ballot
↓
Personalized drill
↓


Re-record
↓
Progress improves
↓
Coach sees dashboard

That loop is concrete, useful, and defensible.

# 20. Final recommendation

Build this first:

## Dissio V1: AI Flow Coach for Public Forum Debate

### Core functionality

```
● Record/upload PF speech
● Transcribe speech
● Extract claim/warrant/evidence/impact
● Generate flow table
● Give judge-specific ballot feedback
● Identify missing warrants, weak weighing, and unclear extensions
● Generate 3 personalized drills
● Let student re-record and track improvement
```
### Stack

```
● Next.js + TypeScript + Tailwind + shadcn/ui
● FastAPI + Python + Pydantic
● Supabase Auth + Postgres + Storage + pgvector
● Whisper API for transcription
● LangGraph for AI workflow orchestration
● OpenAI/Claude/Gemini for structured LLM reasoning
● LlamaIndex or LangChain for evidence RAG
● DeepEval + custom rubric tests for evaluation
● PostHog for analytics
● Vercel + Railway/Render + Supabase for deployment
```
This project will teach you modern AI engineering, full-stack product development, speech/NLP
systems, evaluation, RAG, startup validation, and user-centered design, while producing
something genuinely useful for students you can reach this summer.


