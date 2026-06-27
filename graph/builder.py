"""builder — extract entities and relations from hypothesis/paper text and store them."""
from __future__ import annotations

from typing import Any


async def build_from_hypothesis(hypothesis_text: str, question: str, project_id: str, db: Any) -> list[Any]:
    """Extract entities from a hypothesis and store them in the KG."""
    try:
        from intelligence.entity_extractor import extract_entities
        entities = await extract_entities(text=hypothesis_text, context=question)
        stored = []
        for e in entities:
            from graph.graph_store import store_entity
            node = await store_entity(
                {
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "domain": e.domain,
                    "description": e.definition_snippet,
                    "confidence": e.confidence,
                },
                project_id=project_id,
                db=db,
            )
            stored.append(node)
        return stored
    except Exception:
        return []
