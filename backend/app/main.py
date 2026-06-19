from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import argument_maps, assignments, blockfiles, dev, documents, drills, feedback_reports, health, jobs, output_feedback, pilot, research, shared_reports, speeches, teams, transcripts, users, workouts
from app.config import settings

app = FastAPI(title="RoundLab API", version="0.1.0")

# CORS: support multiple origins from environment (comma-separated)
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(speeches.router)
app.include_router(transcripts.router)
app.include_router(argument_maps.router)
app.include_router(feedback_reports.router)
app.include_router(drills.speech_drills_router)
app.include_router(drills.drills_router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(assignments.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(output_feedback.router)
app.include_router(pilot.router)
app.include_router(shared_reports.router)
app.include_router(workouts.router)
app.include_router(blockfiles.router)
app.include_router(research.router)

# Dev-only endpoints (disabled in production via environment check)
if settings.environment != "production":
    app.include_router(dev.router)
