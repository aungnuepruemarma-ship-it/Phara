"""
index_knowledge_step — called from paper_service background task after PDF embedding.

Extracts key concepts and findings from paper text chunks via the LLM and
stores them in the Qdrant "knowledge" collection so the analogy engine can
find cross-domain matches.
"""
from __future__ import annotations

import uuid

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None


def index_paper_knowledge(paper_id: str, chunks: list[str], project_id: str) -> int:
    """Synchronous wrapper — called from the background task in paper_service."""
    import asyncio

    try:
        return asyncio.run(_async_index(paper_id, chunks, project_id))
    except Exception:
        return 0


async def _async_index(paper_id: str, chunks: list[str], project_id: str) -> int:
    """Extract entities/concepts from chunks and store in knowledge collection."""
    if not chunks:
        return 0

    # Build a compact representation of the paper for entity extraction
    sample_text = "\n\n".join(chunks[:10])  # use first 10 chunks (~first few pages)

    try:
        from intelligence.entity_extractor import extract_entities
        entities = await extract_entities(sample_text)
    except Exception:
        entities = []

    if not entities:
        return 0

    try:
        from memory.knowledge_memory import KnowledgeEntry, store_knowledge

        entries = [
            KnowledgeEntry(
                entry_id=str(uuid.uuid4()),
                text=f"{e.name}: {e.definition_snippet}" if e.definition_snippet else e.name,
                source_paper_id=paper_id,
                project_id=project_id,
                kind=e.entity_type if e.entity_type in ("concept", "finding", "definition", "fact") else "concept",
            )
            for e in entities
        ]
        return store_knowledge(entries)
    except Exception:
        return 0
