"""Shared LLM call machinery for all specialist agents."""
import json

from agents.base_agent import AgentInput, AgentOutput, BaseAgent
from agents.llm_client import resilient_chat, resilient_chat_sync

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None


class LLMAgent(BaseAgent):
    """BaseAgent subclass that adds async/sync LLM calling and JSON parsing."""

    temperature: float = 0.7

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        return "You are a rigorous research assistant generating evidence-based hypotheses."

    def _build_user_prompt(self, input_data: AgentInput) -> str:
        evidence = "\n\n".join(f"[Source {i+1}]: {chunk}" for i, chunk in enumerate(input_data.context))
        evidence_block = f"Evidence from retrieved papers:\n{evidence}\n\n" if evidence.strip() else ""

        # Multi-agent collaboration: an extra instruction and a digest of other
        # agents' contributions are injected so this agent can respond to peers.
        instruction = input_data.parameters.get("instruction", "")
        peer_context = input_data.parameters.get("peer_context", "")
        history = input_data.parameters.get("history", "")
        instruction_block = f"{instruction}\n\n" if instruction else ""
        peer_block = f"What other expert agents said:\n{peer_context}\n\n" if peer_context else ""
        history_block = f"Earlier conversation:\n{history}\n\n" if history else ""

        return (
            f"{instruction_block}"
            f"{history_block}"
            f"{evidence_block}"
            f"{peer_block}"
            f"Research question: {input_data.question}\n\n"
            'Respond with JSON: {"hypothesis": "...", "reasoning": "...", "confidence": 0.0-1.0}'
        )

    def _parse_response(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"hypothesis": text.strip(), "reasoning": "Parsed from raw response.", "confidence": 0.5}

    def _no_llm_response(self) -> dict:
        return {
            "hypothesis": "No LLM configured. Set LLM_API_KEY (OpenAI) or HF_TOKEN (free HF Inference) in environment.",
            "reasoning": "LLM not available.",
            "confidence": 0.0,
        }

    def _unavailable_response(self) -> dict:
        """Degraded response when every model/retry failed — never raise, so the
        research workflow always completes and returns a result."""
        return {
            "hypothesis": (
                "Hypothesis generation is temporarily unavailable — the free model "
                "provider is rate-limited right now. Please run it again in a moment."
            ),
            "reasoning": "All configured LLM models were unavailable (rate-limited or busy) after retries.",
            "confidence": 0.0,
        }

    def _messages(self, system: str, user: str) -> list[dict]:
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _call_llm(self, system: str, user: str) -> dict:
        creds = _settings.llm_credentials if _settings else None
        if not creds:
            return self._no_llm_response()
        text = resilient_chat_sync(self._messages(system, user), temperature=self.temperature)
        return self._parse_response(text) if text else self._unavailable_response()

    async def _acall_llm(self, system: str, user: str) -> dict:
        creds = _settings.llm_credentials if _settings else None
        if not creds:
            return self._no_llm_response()
        text = await resilient_chat(self._messages(system, user), temperature=self.temperature)
        return self._parse_response(text) if text else self._unavailable_response()

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        return {}

    def run(self, input_data: AgentInput) -> AgentOutput:
        raw = self._call_llm(self._build_system_prompt(input_data), self._build_user_prompt(input_data))
        return AgentOutput(
            hypothesis=raw["hypothesis"],
            reasoning=raw["reasoning"],
            confidence=float(raw.get("confidence", 0.7)),
            metadata=self._extra_metadata(input_data),
        )

    async def arun(self, input_data: AgentInput) -> AgentOutput:
        raw = await self._acall_llm(self._build_system_prompt(input_data), self._build_user_prompt(input_data))
        return AgentOutput(
            hypothesis=raw["hypothesis"],
            reasoning=raw["reasoning"],
            confidence=float(raw.get("confidence", 0.7)),
            metadata=self._extra_metadata(input_data),
        )
