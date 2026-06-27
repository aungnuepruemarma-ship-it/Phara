from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from memory.embedder import embed, embed_single
from memory.qdrant_client import ensure_collection, get_qdrant_client

COLLECTION = "papers"


@dataclass
class SearchResult:
    chunk_text: str
    paper_id: str
    score: float


def upsert_paper(paper_id: str, chunks: list[str], project_id: str) -> int:
    """Embed and upsert all chunks for a paper. Returns chunk count."""
    ensure_collection(COLLECTION)
    client = get_qdrant_client()

    vectors = embed(chunks)
    points = [
        PointStruct(
            id=f"{paper_id}_{i}",
            vector=vectors[i].tolist(),
            payload={"paper_id": paper_id, "project_id": project_id, "chunk_index": i, "text": chunks[i]},
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(chunks)


def search_similar(query: str, project_id: str, top_k: int = 5) -> list[SearchResult]:
    """Search for the most relevant chunks within a project."""
    ensure_collection(COLLECTION)
    client = get_qdrant_client()

    query_vector = embed_single(query)
    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(must=[FieldCondition(key="project_id", match=MatchValue(value=project_id))]),
        limit=top_k,
        with_payload=True,
    )
    return [
        SearchResult(
            chunk_text=r.payload.get("text", ""),
            paper_id=r.payload.get("paper_id", ""),
            score=r.score,
        )
        for r in results
    ]


def delete_paper_vectors(paper_id: str) -> None:
    """Remove all vectors for a paper from Qdrant."""
    client = get_qdrant_client()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]),
    )
