import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import argument_maps, assignments, blockfiles, coach, dev, documents, drills, evidence_library, feedback_reports, health, jobs, judge_adaptation, missions, output_feedback, pilot, research, round_simulations, shared_reports, speeches, teams, tournament_prep, training, transcripts, users, workouts
from app.config import settings
from app.middleware.correlation import CorrelationMiddleware

# Structured logging: consistent key=value output for log aggregation
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
        "openai": {"level": "WARNING"},
        "supabase": {"level": "WARNING"},
    },
})

app = FastAPI(title="Dissio API", version="0.1.0")

# CORS: support multiple origins from environment (comma-separated)
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation middleware: injects x-request-id into every request/response
app.add_middleware(CorrelationMiddleware)

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
app.include_router(evidence_library.router)
app.include_router(tournament_prep.router)
app.include_router(judge_adaptation.router)
app.include_router(round_simulations.router)
app.include_router(missions.router)
app.include_router(coach.router)
app.include_router(training.router)

# Dev-only endpoints (disabled in production via environment check)
if settings.environment != "production":
    app.include_router(dev.router)
