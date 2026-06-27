"""
cross_domain_node — LangGraph node that runs the Cross-Domain Intelligence Engine.

Extracts entities from the research question, finds structural analogies across
the project's knowledge base, and injects cross-domain insights into the pipeline
state so the hypothesis generator can use them.
"""
from __future__ import annotations

from intelligence.analogy_engine import find_analogies
from intelligence.entity_extractor import extract_entities


async def cross_domain_node(state: dict) -> dict:
    """LangGraph node: enrich state with cross-domain insights."""
    question = state.get("question", "")
    project_id = state.get("project_id", "")

    try:
        entities = await extract_entities(question)
        analogies = await find_analogies(entities, project_id)

        state["cross_domain_insights"] = [
            {
                "source": a.source_name,
                "source_domain": a.source_domain,
                "target": a.target_name,
                "target_domain": a.target_domain,
                "similarity": a.similarity_score,
                "explanation": a.explanation,
            }
            for a in analogies
        ]
    except Exception:
        state["cross_domain_insights"] = []

    return state
