"""retrieval — unified retrieval layer (Blueprint v1.0).

Modules:
  vector_search  — semantic embedding-based search (wraps memory/vector_store)
  graph_search   — entity/relation traversal over the KG
  hybrid_search  — merge vector and graph results
  reranker       — cross-encoder re-scoring of candidate passages
  retriever      — high-level interface used by LangGraph nodes and tools
"""
from retrieval.retriever import retrieve

__all__ = ["retrieve"]
