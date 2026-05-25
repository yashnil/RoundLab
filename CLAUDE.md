# RoundLab Claude Instructions

RoundLab is an AI flow coach for novice and JV Public Forum debaters.

Core MVP:
Record/upload PF speech → transcribe → extract claim/warrant/evidence/impact → generate flow table → generate ballot-style feedback → generate 3 personalized drills → allow re-recording and progress tracking.

Primary user:
Novice/JV PF debaters, especially students without consistent coaching.

Product principle:
Make the app feel like coaching, not cheating. Do not prioritize case generation. Prioritize practice, feedback, and skill improvement.

Feedback must be:
- Debate-native
- Specific
- Actionable
- Connected to drills
- Focused on warrants, weighing, extensions, drops, clash, and judge adaptation

Main stack:
- Next.js + TypeScript + Tailwind + shadcn/ui
- FastAPI + Python + Pydantic
- Supabase Auth + Postgres + Storage
- Whisper API for transcription
- LangGraph for AI pipeline
- Structured LLM outputs
- DeepEval/custom evals later
- PostHog later

Important docs:
- docs/project-plan.md is the full project plan.
- docs/product-requirements.md contains MVP requirements.
- docs/ai-pipeline.md contains AI workflow design.
- docs/debate-rubric.md contains scoring criteria.
- docs/sample-speeches.md contains examples/test data.

Working rules:
- Do not edit files until you explain the plan.
- For large changes, give a file-by-file plan first.
- Ask before adding major dependencies.
- Prefer simple MVP implementation over overengineering.
- Build one feature at a time.
- Use structured schemas for AI outputs.