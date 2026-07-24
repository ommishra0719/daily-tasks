from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    # Users choose a NAMED prompt config only -- never raw system-prompt
    # text. See app/services/prompts.py for why.
    prompt_name: str = Field(default="general", min_length=1, max_length=100)


class SessionOut(BaseModel):
    id: str
    prompt_name: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)


class MessageOut(BaseModel):
    role: str
    content: str
    token_count: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    session_id: str
    prompt_name: str
    messages: list[MessageOut]


class PromptInfo(BaseModel):
    name: str
    description: str
