import uuid
from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] = []


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    project: ProjectOut
    paper_count: int
    experiment_count: int
    note_count: int
