"""
KnowledgeMemory — a project-scoped store of extracted concepts and facts.

Each entry is a short text fragment (concept, definition, or key finding)
embedded and stored in Qdrant under the "knowledge" collection.
This allows the research workflow to query structured knowledge across
papers rather than raw text chunks.
"""
from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from memory.embedder import embed, embed_single
from memory.qdrant_client import ensure_collection, get_qdrant_client

COLLECTION = "knowledge"


@dataclass
class KnowledgeEntry:
    entry_id: str
    text: str
    source_paper_id: str
    project_id: str
    kind: str  # "concept" | "finding" | "definition" | "fact"
    score: float = 0.0


def store_knowledge(entries: list[KnowledgeEntry]) -> int:
    """Embed and upsert knowledge entries. Returns count stored."""
    if not entries:
        return 0
    ensure_collection(COLLECTION)
    client = get_qdrant_client()

    texts = [e.text for e in entries]
    vectors = embed(texts)
    points = [
        PointStruct(
            id=entries[i].entry_id,
            vector=vectors[i].tolist(),
            payload={
                "text": entries[i].text,
                "source_paper_id": entries[i].source_paper_id,
                "project_id": entries[i].project_id,
                "kind": entries[i].kind,
            },
        )
        for i in range(len(entries))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(entries)


def search_knowledge(query: str, project_id: str, top_k: int = 5, kind: str | None = None) -> list[KnowledgeEntry]:
    """Retrieve the most relevant knowledge entries for a query within a project."""
    ensure_collection(COLLECTION)
    client = get_qdrant_client()

    conditions = [FieldCondition(key="project_id", match=MatchValue(value=project_id))]
    if kind:
        conditions.append(FieldCondition(key="kind", match=MatchValue(value=kind)))

    query_vector = embed_single(query)
    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(must=conditions),
        limit=top_k,
        with_payload=True,
    )
    return [
        KnowledgeEntry(
            entry_id=str(r.id),
            text=r.payload.get("text", ""),
            source_paper_id=r.payload.get("source_paper_id", ""),
            project_id=r.payload.get("project_id", ""),
            kind=r.payload.get("kind", "fact"),
            score=r.score,
        )
        for r in results
    ]


def delete_paper_knowledge(paper_id: str) -> None:
    """Remove all knowledge entries sourced from a specific paper."""
    client = get_qdrant_client()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="source_paper_id", match=MatchValue(value=paper_id))]
        ),
    )
