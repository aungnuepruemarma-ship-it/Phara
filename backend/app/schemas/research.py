import uuid
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.hypothesis import HypothesisOut


class WorkflowRequest(BaseModel):
    question: str
    project_id: uuid.UUID
    experiment_id: Optional[uuid.UUID] = None
    agent_name: str = "math_research_agent"
    enable_debate: bool = False
    enable_critique: bool = False
    enable_contradiction_check: bool = False
    enabled_tools: list[str] = []
    auto_tools: bool = True  # when True and enabled_tools empty, agent auto-selects tools

    @field_validator("experiment_id", mode="before")
    @classmethod
    def _blank_experiment_id_to_none(cls, v):
        # Frontends may send "" for "no experiment selected" — treat as None so
        # the workflow auto-creates one instead of failing UUID validation (422).
        if v in ("", None):
            return None
        return v


class DebateEntry(BaseModel):
    role: str
    hypothesis: str
    reasoning: str
    confidence: float


class ContradictionItem(BaseModel):
    claim_a: str
    source_a: int
    claim_b: str
    source_b: int
    explanation: str
    severity: str


class WorkflowResult(BaseModel):
    hypothesis: HypothesisOut
    evidence_summary: str
    retrieved_paper_count: int
    debate: list[DebateEntry] = []
    critique: DebateEntry | None = None
    contradictions: list[ContradictionItem] = []
    mlflow_run_id: str | None = None
    tool_results: list[dict] = []


# ── Multi-agent chat roundtable ──────────────────────────────────────────────
class ChatHistoryEntry(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class RoundtableRequest(BaseModel):
    question: str
    project_id: uuid.UUID
    agent_names: list[str]
    experiment_id: Optional[uuid.UUID] = None
    history: list[ChatHistoryEntry] = []
    tools: list[str] = []  # tool names the panel may use (incl. "code_sandbox")
    auto_tools: bool = False

    @field_validator("experiment_id", mode="before")
    @classmethod
    def _blank_experiment_id_to_none(cls, v):
        if v in ("", None):
            return None
        return v


class AgentTurn(BaseModel):
    agent_name: str
    role: str  # "perspective" | "rebuttal" | "synthesis"
    content: str
    confidence: float


class DomainPatternOut(BaseModel):
    pattern_type: str
    description: str
    domains_seen: list[str] = []
    confidence: float = 0.7


class RoundtableResult(BaseModel):
    turns: list[AgentTurn]
    final_text: str
    final_confidence: float
    patterns: list[DomainPatternOut] = []
    tool_results: list[dict] = []
    saved_hypothesis_id: str | None = None
    retrieved_paper_count: int = 0
