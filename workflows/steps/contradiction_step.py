"""
ContradictionStep — scans retrieved evidence chunks for contradicting claims.

Uses the LLM to identify pairs of statements that directly contradict each other.
Results are stored in ctx.contradictions as a list of dicts:
  {"claim_a": str, "claim_b": str, "source_a": int, "source_b": int, "severity": "high"|"medium"|"low"}
"""
import json

import httpx

from workflows.base_step import BaseWorkflowStep, PipelineContext

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

_SYSTEM_PROMPT = (
    "You are a scientific fact-checker. Given a list of evidence chunks, "
    "identify pairs of statements that directly contradict each other. "
    "Focus on factual contradictions (different measurements, opposite conclusions, "
    "conflicting mechanisms). Ignore minor differences in emphasis or scope."
)


def _build_prompt(chunks: list[str]) -> str:
    numbered = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(chunks))
    return (
        f"Evidence chunks:\n{numbered}\n\n"
        "Find contradictions between these chunks. "
        "Respond with JSON array (empty array if none found):\n"
        '[{"claim_a": "...", "source_a": 1, "claim_b": "...", "source_b": 2, '
        '"explanation": "...", "severity": "high|medium|low"}]'
    )


def _parse(text: str) -> list[dict]:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return []


async def _detect(chunks: list[str]) -> list[dict]:
    if not _settings or len(chunks) < 2:
        return []
    creds = _settings.llm_credentials
    if not creds:
        return []
    base_url, api_key, model = creds
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": _build_prompt(chunks)},
                    ],
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            return _parse(resp.json()["choices"][0]["message"]["content"])
    except Exception:
        return []


class ContradictionStep(BaseWorkflowStep):
    """Optional pipeline step: detect contradictions in retrieved evidence."""

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.enable_contradiction_check or len(ctx.retrieved_chunks) < 2:
            return ctx
        ctx.contradictions = await _detect(ctx.retrieved_chunks)
        return ctx
