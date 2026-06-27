from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentInput:
    question: str
    context: list[str]
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    hypothesis: str
    reasoning: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, input_data: AgentInput) -> AgentOutput:
        ...

    @abstractmethod
    async def arun(self, input_data: AgentInput) -> AgentOutput:
        ...

    def validate_input(self, input_data: AgentInput) -> bool:
        return bool(input_data.question.strip())

    def __repr__(self) -> str:
        return f"<Agent name={self.name!r}>"
