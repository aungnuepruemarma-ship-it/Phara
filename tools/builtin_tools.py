"""
Built-in tool implementations — auto-registered on import.

Five tools:
  knowledge_search  — semantic search over project knowledge base (Qdrant)
  extract_entities  — named entity extraction from text (LLM)
  find_analogies    — cross-domain structural analogies (embedding + LLM)
  arxiv_search      — live Arxiv paper search (no auth, stdlib XML parse)
  agent_run         — invoke any registered research agent
"""
from __future__ import annotations

from tools.tool_registry import register_tool
from tools.tool_spec import ToolSpec


# ---------------------------------------------------------------------------
# 1. knowledge_search
# ---------------------------------------------------------------------------

async def _knowledge_search(query: str, project_id: str, top_k: int = 5) -> list[dict]:
    try:
        from memory.knowledge_memory import search_knowledge
        entries = search_knowledge(query=query, project_id=project_id, top_k=top_k)
        return [{"text": e.text, "kind": e.kind, "score": round(e.score, 3), "source_paper_id": e.source_paper_id} for e in entries]
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="knowledge_search",
        description="Semantic search over papers and knowledge entries indexed for this project. Returns the most relevant passages.",
        category="memory",
        input_schema={
            "type": "object",
            "properties": {
                "query":      {"type": "string", "description": "Search query"},
                "project_id": {"type": "string", "description": "Project UUID"},
                "top_k":      {"type": "integer", "default": 5, "description": "Number of results"},
            },
            "required": ["query", "project_id"],
        },
    ),
    _knowledge_search,
)


# ---------------------------------------------------------------------------
# 2. extract_entities
# ---------------------------------------------------------------------------

async def _extract_entities(text: str, context: str = "") -> list[dict]:
    try:
        from intelligence.entity_extractor import extract_entities
        entities = await extract_entities(text=text, context=context)
        return [{"name": e.name, "entity_type": e.entity_type, "domain": e.domain, "definition_snippet": e.definition_snippet, "confidence": e.confidence} for e in entities]
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="extract_entities",
        description="Extract named concepts, methods, and phenomena from a research question or hypothesis using LLM-powered NER.",
        category="analysis",
        input_schema={
            "type": "object",
            "properties": {
                "text":    {"type": "string", "description": "Text to extract entities from"},
                "context": {"type": "string", "default": "", "description": "Optional additional context"},
            },
            "required": ["text"],
        },
    ),
    _extract_entities,
)


# ---------------------------------------------------------------------------
# 3. find_analogies
# ---------------------------------------------------------------------------

async def _find_analogies(entities: list[dict], project_id: str) -> list[dict]:
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


register_tool(
    ToolSpec(
        name="find_analogies",
        description="Find structural analogies between extracted entities and cross-domain concepts in the knowledge base.",
        category="analysis",
        input_schema={
            "type": "object",
            "properties": {
                "entities":   {"type": "array", "items": {"type": "object"}, "description": "List of entity dicts from extract_entities"},
                "project_id": {"type": "string", "description": "Project UUID"},
            },
            "required": ["entities", "project_id"],
        },
    ),
    _find_analogies,
)


# ---------------------------------------------------------------------------
# 4. arxiv_search
# ---------------------------------------------------------------------------

async def _arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    import xml.etree.ElementTree as ET
    import httpx

    url = "https://export.arxiv.org/api/query"
    params = {"search_query": f"all:{query}", "max_results": str(max_results), "sortBy": "relevance"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            results.append({
                "title":   (title_el.text or "").strip() if title_el is not None else "",
                "summary": (summary_el.text or "").strip()[:300] if summary_el is not None else "",
                "arxiv_id": (id_el.text or "").split("/abs/")[-1] if id_el is not None else "",
            })
        return results
    except Exception:
        return []


register_tool(
    ToolSpec(
        name="arxiv_search",
        description="Search Arxiv for recent papers matching a query. Returns titles, abstracts (truncated), and arxiv IDs.",
        category="research",
        input_schema={
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5, "description": "Number of results (max 10)"},
            },
            "required": ["query"],
        },
    ),
    _arxiv_search,
)


# ---------------------------------------------------------------------------
# 5. agent_run
# ---------------------------------------------------------------------------

async def _agent_run(agent_name: str, question: str, context: list[str] | None = None) -> dict:
    from agents.agent_registry import get_agent
    from agents.base_agent import AgentInput

    agent = get_agent(agent_name)
    output = await agent.arun(AgentInput(question=question, context=context or []))
    return {
        "hypothesis": output.hypothesis,
        "reasoning": output.reasoning,
        "confidence": output.confidence,
        "agent": agent_name,
    }


register_tool(
    ToolSpec(
        name="agent_run",
        description="Run any registered research agent and return its hypothesis and reasoning. Useful for getting a specialist perspective before the primary agent runs.",
        category="research",
        input_schema={
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Agent name from the agent registry"},
                "question":   {"type": "string", "description": "Research question"},
                "context":    {"type": "array", "items": {"type": "string"}, "description": "Optional list of context passages"},
            },
            "required": ["agent_name", "question"],
        },
    ),
    _agent_run,
)
