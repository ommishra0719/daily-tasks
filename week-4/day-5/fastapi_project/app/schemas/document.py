from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    content: str


class DocumentUpdate(BaseModel):
    title: str
    content: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
