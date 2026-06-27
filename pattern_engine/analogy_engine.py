"""analogy_engine — structural analogy mapping across domains (wraps intelligence/)."""
from __future__ import annotations


async def find_cross_domain_analogies(entities: list[dict], project_id: str) -> list[dict]:
    """Delegate to intelligence.analogy_engine with a clean interface."""
    try:
        from intelligence.analogy_engine import find_analogies
        from intelligence.entity_extractor import ExtractedEntity
        entity_objs = [
            ExtractedEntity(
                name=e.get("name", ""),
                entity_type=e.get("entity_type", "concept"),
                domain=e.get("domain", "general"),
                definition_snippet=e.get("definition_snippet", ""),
                confidence=float(e.get("confidence", 0.8)),
            )
            for e in entities
        ]
        analogies = await find_analogies(entities=entity_objs, project_id=project_id)
        return [a.to_dict() if hasattr(a, "to_dict") else vars(a) for a in analogies]
    except Exception:
        return []
