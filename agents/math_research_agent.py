import json

import httpx

from agents.base_agent import AgentInput, AgentOutput, BaseAgent

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

MATH_KEYWORDS = frozenset(
    [
        "theorem", "proof", "equation", "formula", "matrix", "eigenvalue",
        "integral", "gradient", "optimization", "convergence", "bound",
        "lemma", "corollary", "derivative", "divergence", "probability",
        "distribution", "entropy", "manifold", "topology",
    ]
)


class MathResearchAgent(BaseAgent):
    """Specialist agent for mathematical and quantitative research questions."""

    name = "math_research_agent"
    description = "Specializes in mathematical reasoning, theorem analysis, and quantitative hypothesis generation."

    def _is_math_heavy(self, question: str) -> bool:
        lower = question.lower()
        return any(kw in lower for kw in MATH_KEYWORDS)

    def _build_system_prompt(self, is_math: bool) -> str:
        base = "You are a rigorous research assistant generating evidence-based hypotheses."
        if is_math:
            base += (
                " Pay special attention to mathematical rigor: cite theorems, use precise notation,"
                " and distinguish proven facts from conjectures."
            )
        return base

    def _build_user_prompt(self, input_data: AgentInput) -> str:
        evidence = "\n\n".join(f"[Source {i+1}]: {chunk}" for i, chunk in enumerate(input_data.context))
        return (
            f"Evidence from retrieved papers:\n{evidence}\n\n"
            f"Research question: {input_data.question}\n\n"
            "Respond with JSON: {\"hypothesis\": \"...\", \"reasoning\": \"...\", \"confidence\": 0.0-1.0}"
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

    def _call_llm(self, system: str, user: str) -> dict:
        if not _settings or not _settings.llm_api_key:
            return {
                "hypothesis": "No LLM configured. Set LLM_API_KEY in environment to enable hypothesis generation.",
                "reasoning": "LLM not available.",
                "confidence": 0.0,
            }
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{_settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {_settings.llm_api_key}"},
                json={
                    "model": _settings.llm_model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return self._parse_response(content)

    async def _acall_llm(self, system: str, user: str) -> dict:
        if not _settings or not _settings.llm_api_key:
            return {
                "hypothesis": "No LLM configured. Set LLM_API_KEY in environment to enable hypothesis generation.",
                "reasoning": "LLM not available.",
                "confidence": 0.0,
            }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{_settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {_settings.llm_api_key}"},
                json={
                    "model": _settings.llm_model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def run(self, input_data: AgentInput) -> AgentOutput:
        is_math = self._is_math_heavy(input_data.question)
        raw = self._call_llm(self._build_system_prompt(is_math), self._build_user_prompt(input_data))
        return AgentOutput(
            hypothesis=raw["hypothesis"],
            reasoning=raw["reasoning"],
            confidence=float(raw.get("confidence", 0.7)),
            metadata={"math_detected": is_math},
        )

    async def arun(self, input_data: AgentInput) -> AgentOutput:
        is_math = self._is_math_heavy(input_data.question)
        raw = await self._acall_llm(self._build_system_prompt(is_math), self._build_user_prompt(input_data))
        return AgentOutput(
            hypothesis=raw["hypothesis"],
            reasoning=raw["reasoning"],
            confidence=float(raw.get("confidence", 0.7)),
            metadata={"math_detected": is_math},
        )
