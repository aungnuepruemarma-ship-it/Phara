"""
EntityExtractor — pulls named concepts from a question or hypothesis text.

Uses the LLM to extract structured entities (concept, method, phenomenon, etc.)
that can later be stored in the Knowledge Graph and searched for analogies.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

_SYSTEM = (
    "You are a scientific knowledge extractor. "
    "Given a research question or hypothesis, identify the key named concepts, methods, "
    "phenomena, and principles mentioned or implied. "
    "Assign each a domain (e.g. mathematics, physics, biology, computer_science, ai_ml, chemistry, general) "
    "and an entity_type (concept | method | phenomenon | principle | dataset | person)."
)


@dataclass
class ExtractedEntity:
    name: str
    entity_type: str  # concept | method | phenomenon | principle | dataset | person
    domain: str
    definition_snippet: str = ""
    confidence: float = 0.8


def _parse(text: str) -> list[ExtractedEntity]:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start < 0 or end <= start:
        return []
    try:
        items = json.loads(text[start:end])
    except json.JSONDecodeError:
        return []
    entities = []
    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            continue
        entities.append(ExtractedEntity(
            name=item.get("name", ""),
            entity_type=item.get("entity_type", "concept"),
            domain=item.get("domain", "general"),
            definition_snippet=item.get("definition_snippet", ""),
            confidence=float(item.get("confidence", 0.8)),
        ))
    return entities


async def extract_entities(text: str, context: str = "") -> list[ExtractedEntity]:
    """Extract named entities from a research question or hypothesis text."""
    from agents.llm_client import acall_llm

    user_prompt = f"Text: {text}"
    if context:
        user_prompt += f"\n\nAdditional context: {context[:500]}"
    user_prompt += (
        "\n\nExtract entities. Respond with a JSON array:\n"
        '[{"name": "...", "entity_type": "concept|method|phenomenon|principle|dataset|person", '
        '"domain": "...", "definition_snippet": "...", "confidence": 0.0-1.0}]'
    )

    try:
        content = await acall_llm(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_prompt}],
            temperature=0.1,
            timeout=60,
        )
        if content:
            return _parse(content) or _heuristic_extract(text)
    except Exception:
        pass
    return _heuristic_extract(text)


def _heuristic_extract(text: str) -> list[ExtractedEntity]:
    """Fallback: extract capitalized noun phrases as entities without LLM."""
    import re
    # Find capitalized multi-word phrases or known domain terms
    words = re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b', text)
    seen: set[str] = set()
    entities = []
    for w in words:
        if w not in seen and len(w) > 3:
            seen.add(w)
            entities.append(ExtractedEntity(
                name=w,
                entity_type="concept",
                domain="general",
                confidence=0.4,
            ))
    return entities[:5]
