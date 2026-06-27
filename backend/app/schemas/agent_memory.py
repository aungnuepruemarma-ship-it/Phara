import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentMemoryCreate(BaseModel):
    agent_name: str
    content: str
    memory_type: str = "learning"
    source_question: str = ""
    tags: list[str] = []


class AgentMemoryOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    agent_name: str
    memory_type: str
    content: str
    source_question: str
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
