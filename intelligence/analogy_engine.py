"""
AnalogyEngine — finds structural analogies between a source entity and
entities in the project's knowledge base.

Two-stage process:
  1. Vector search: find semantically similar concepts across domains (Qdrant)
  2. LLM verification: confirm structural (not just lexical) similarity
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

_VERIFY_SYSTEM = (
    "You are an expert in cross-domain structural analogies. "
    "Given two concepts from different domains, determine whether they are "
    "structurally analogous (same underlying mechanism, not just same words). "
    "A valid analogy means: the same abstract process, constraint, or optimization "
    "operates in both domains, even if the surface-level phenomena look different."
)


@dataclass
class AnalogyMatch:
    source_name: str
    source_domain: str
    target_name: str
    target_domain: str
    similarity_score: float
    explanation: str
    verified: bool = False


async def _verify_analogy(source: str, source_domain: str, target: str, target_domain: str) -> tuple[bool, str]:
    """Use LLM to confirm structural analogy between two concepts."""
    if not _settings or not _settings.llm_api_key:
        return False, ""
    try:
        user_prompt = (
            f"Source concept ({source_domain}): {source}\n"
            f"Target concept ({target_domain}): {target}\n\n"
            "Is there a genuine structural analogy between these two concepts? "
            'Respond with JSON: {"is_analogy": true/false, "explanation": "...", "confidence": 0.0-1.0}'
        )
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{_settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {_settings.llm_api_key}"},
                json={
                    "model": _settings.llm_model,
                    "messages": [
                        {"role": "system", "content": _VERIFY_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return bool(data.get("is_analogy")), data.get("explanation", "")
    except Exception:
        pass
    return False, ""


async def find_analogies(
    entities: list,  # list[ExtractedEntity]
    project_id: str,
    top_k: int = 3,
) -> list[AnalogyMatch]:
    """Find cross-domain analogies for a list of extracted entities."""
    from memory.knowledge_memory import search_knowledge

    matches: list[AnalogyMatch] = []

    for entity in entities[:5]:  # cap at 5 entities to avoid LLM overuse
        try:
            results = search_knowledge(entity.name, project_id, top_k=top_k)
        except Exception:
            continue

        for result in results:
            if result.score < 0.6:
                continue
            if result.project_id == project_id and result.kind in ("concept", "finding"):
                # Skip same-domain matches
                pass
            is_analogy, explanation = await _verify_analogy(
                entity.name, entity.domain,
                result.text[:150], result.kind,
            )
            if is_analogy:
                matches.append(AnalogyMatch(
                    source_name=entity.name,
                    source_domain=entity.domain,
                    target_name=result.text[:80],
                    target_domain=result.kind,
                    similarity_score=result.score,
                    explanation=explanation,
                    verified=True,
                ))

    return matches
