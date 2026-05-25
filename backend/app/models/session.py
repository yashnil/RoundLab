from pydantic import BaseModel


# Sprint 2: expand these with transcription, flow, feedback fields.


class SessionCreateRequest(BaseModel):
    title: str


class SessionResponse(BaseModel):
    id: str
    title: str
    status: str
