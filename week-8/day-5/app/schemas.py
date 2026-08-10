from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Documents ─────────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    documents: List[dict]   # [{"id": "...", "text": "...", "filename": "..."}]


class IngestResponse(BaseModel):
    job_id: str
    status: str
    queued_count: int


class DocumentOut(BaseModel):
    id: str
    filename: str
    chunk_count: int
    indexed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    title: str = "New session"


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: str   # raw JSON string; parse client-side
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageOut]
