"""graph — Knowledge Graph module (Blueprint v1.0).

Connects concepts, experiments, and hypotheses across domains.
Wraps the existing KG ORM models and provides a clean interface
independent of the FastAPI / SQLAlchemy layer.

Modules:
  builder        — extract entities + relations from text and store them
  entity_linker  — match new entities to existing nodes (deduplication)
  ontology       — domain taxonomy: entity types and relation types
  reasoning      — graph-based inference over stored entities
  graph_store    — low-level CRUD over KGEntity / KGRelation tables
"""
from graph.graph_store import get_graph, store_entity, store_relation
from graph.ontology import ENTITY_TYPES, RELATION_TYPES

__all__ = ["get_graph", "store_entity", "store_relation", "ENTITY_TYPES", "RELATION_TYPES"]
