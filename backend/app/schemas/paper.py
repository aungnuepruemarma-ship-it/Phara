import uuid
from datetime import datetime

from pydantic import BaseModel


class PaperMetadata(BaseModel):
    title: str
    authors: list[str] = []
    abstract: str | None = None
    year: int | None = None
    doi: str | None = None


class PaperOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    doi: str | None
    file_path: str
    embedding_status: str
    chunk_count: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class PaperStatusOut(BaseModel):
    id: uuid.UUID
    embedding_status: str
    chunk_count: int
