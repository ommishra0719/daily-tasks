from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class DependencyStatus(BaseModel):
    database: bool


class ReadyResponse(BaseModel):
    status: str
    dependencies: DependencyStatus
