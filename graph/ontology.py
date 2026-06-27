"""Ontology — entity types and relation types for the UIL knowledge graph."""

ENTITY_TYPES = frozenset([
    "concept", "method", "phenomenon", "principle",
    "dataset", "model", "algorithm", "theorem",
    "organism", "compound", "material", "system",
    "person", "institution", "paper",
])

RELATION_TYPES = frozenset([
    "causes", "enables", "contradicts", "extends",
    "analogous_to", "implements", "uses", "produces",
    "derived_from", "evaluated_by", "compared_to",
])

DOMAINS = frozenset([
    "mathematics", "physics", "biology", "chemistry",
    "computer_science", "ai_ml", "economics", "engineering",
    "medicine", "materials_science", "general",
])
