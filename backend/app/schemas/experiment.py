import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.hypothesis import HypothesisOut


class ExperimentCreate(BaseModel):
    title: str
    description: str | None = None
    parameters: dict = {}


class ExperimentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    parameters: dict | None = None
    status: str | None = None
    results: dict | None = None


class ExperimentOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    parameters: dict
    status: str
    results: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExperimentDetail(ExperimentOut):
    hypotheses: list[HypothesisOut] = []
