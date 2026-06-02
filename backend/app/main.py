from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import argument_maps, drills, feedback_reports, health, speeches, transcripts

app = FastAPI(title="RoundLab API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
