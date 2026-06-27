"""
research_graph — LangGraph StateGraph replacing the sequential ResearchPipeline.

All existing step logic is preserved; only the orchestration shell changes.
DB session is injected via config["configurable"]["db"] so nodes stay pure.
Thread ID (= experiment_id) enables per-experiment checkpointing.
"""
from typing import Any, TypedDict

from agents.base_agent import AgentOutput

try:
    from langchain_core.runnables import RunnableConfig
    _CONFIG_TYPE = RunnableConfig
except ImportError:
    _CONFIG_TYPE = dict  # type: ignore[assignment,misc]
    RunnableConfig = dict  # type: ignore[assignment,misc]


class ResearchState(TypedDict, total=False):
    # Core identifiers
    question: str
    project_id: str
    experiment_id: str
    user_id: str
    agent_name: str
    # Feature flags
    enable_debate: bool
    enable_critique: bool
    enable_contradiction_check: bool
    # Pipeline outputs
    retrieved_chunks: list[str]
    retrieved_paper_ids: list[str]
    evidence_summary: str
    hypothesis: AgentOutput | None
    saved_hypothesis_id: str | None
    debate_results: list[AgentOutput]
    critique: AgentOutput | None
    contradictions: list[dict]
    mlflow_run_id: str | None
    # Sprint 2: cross-domain intelligence
    cross_domain_insights: list[dict]
    kg_entities_created: list[str]
    # Sprint 3: evaluation
    enable_evaluation: bool
    evaluation_score: float | None
    # Sprint 5: tool broker
    enabled_tools: list[str]
    tool_results: list[dict]
    # Sprint 6: ablation framework
    ablate_retrieval: bool
    ablate_memory: bool
    ablate_kg: bool
    ablate_tools: bool
    adversarial_context: list[str]
    retrieval_top_k: int | None
    # Sprint 7: autonomous tool selection
    auto_tools: bool


# ---------------------------------------------------------------------------
# Node functions — each wraps one existing workflow step
# ---------------------------------------------------------------------------

async def retrieve_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    adversarial = list(state.get("adversarial_context") or [])

    if state.get("ablate_retrieval"):
        # Ablation: skip paper retrieval; optionally inject adversarial chunks only
        new_state = ResearchState(**state)
        new_state["retrieved_chunks"] = adversarial
        new_state["retrieved_paper_ids"] = []
        new_state["evidence_summary"] = ""
        return new_state

    from workflows.steps.retrieve_papers import RetrievePapersStep
    from app.config import settings

    top_k = state.get("retrieval_top_k") or settings.retrieval_top_k
    ctx = _to_ctx(state)
    ctx = await RetrievePapersStep(top_k=top_k).execute(ctx)
    new_state = _from_ctx(state, ctx)

    # Inject adversarial chunks after real retrieval (adversarial_simulation type)
    if adversarial:
        new_state["retrieved_chunks"] = list(new_state.get("retrieved_chunks") or []) + adversarial

    return new_state


async def summarize_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.summarize_evidence import SummarizeEvidenceStep
    from workflows.base_step import PipelineContext

    ctx = _to_ctx(state)
    ctx = await SummarizeEvidenceStep().execute(ctx)
    return _from_ctx(state, ctx)


async def cross_domain_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    if state.get("ablate_kg"):
        return state
    from intelligence.cross_domain_agent import cross_domain_node as _cdn
    updated = await _cdn(dict(state))
    return ResearchState(**updated)


async def contradiction_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.contradiction_step import ContradictionStep

    ctx = _to_ctx(state)
    ctx = await ContradictionStep().execute(ctx)
    return _from_ctx(state, ctx)


async def hypothesis_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.generate_hypothesis import GenerateHypothesisStep

    ctx = _to_ctx(state)
    ctx = await GenerateHypothesisStep().execute(ctx)
    return _from_ctx(state, ctx)


async def critique_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.critique_step import CritiqueStep

    ctx = _to_ctx(state)
    ctx = await CritiqueStep().execute(ctx)
    return _from_ctx(state, ctx)


async def debate_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.debate_step import DebateStep

    ctx = _to_ctx(state)
    ctx = await DebateStep().execute(ctx)
    return _from_ctx(state, ctx)


async def save_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    db = (config or {}).get("configurable", {}).get("db")  # type: ignore[union-attr]
    if db is None:
        return state

    from workflows.steps.save_experiment import SaveExperimentStep
    from app.services.kg_service import extract_and_store_from_hypothesis

    ctx = _to_ctx(state)
    ctx = await SaveExperimentStep(db=db).execute(ctx)
    new_state = _from_ctx(state, ctx)

    # Populate KG (best-effort; skipped for kg ablation)
    kg_ids: list[str] = []
    if not state.get("ablate_kg") and ctx.saved_hypothesis_id:
        try:
            from sqlalchemy import select
            from app.models.hypothesis import Hypothesis
            import uuid
            result = await db.execute(
                select(Hypothesis).where(Hypothesis.id == uuid.UUID(ctx.saved_hypothesis_id))
            )
            hypothesis = result.scalar_one_or_none()
            if hypothesis:
                entities = await extract_and_store_from_hypothesis(db, hypothesis, ctx.project_id)
                kg_ids = [str(e.id) for e in entities]
        except Exception:
            pass

    new_state["kg_entities_created"] = kg_ids
    return new_state


async def tool_selector_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    """Autonomously pick the most relevant tools for the research question.

    Skipped when:
      - enabled_tools is already set (user made an explicit selection), or
      - auto_tools is False
    Otherwise uses LLM with keyword-heuristic fallback to fill enabled_tools.
    """
    if list(state.get("enabled_tools") or []):
        return state  # manual selection takes precedence
    if not state.get("auto_tools", True):
        return state  # auto-select explicitly disabled

    question = state.get("question", "")
    selected = _heuristic_select_tools(question)

    try:
        llm_picks = await _llm_select_tools(question, selected)
        if llm_picks:
            selected = llm_picks
    except Exception:
        pass

    new_state = ResearchState(**state)
    new_state["enabled_tools"] = selected
    return new_state


def _heuristic_select_tools(question: str) -> list[str]:
    """Keyword-based tool selection — always fast, no LLM required."""
    q = question.lower()
    tools: list[str] = []

    # Universal: broad academic search + background knowledge
    tools.append("semantic_scholar_search")
    tools.append("wikipedia_search")

    # Biomedical domain
    _bio = {"gene", "protein", "cell", "cancer", "drug", "clinical", "disease",
            "biology", "medical", "health", "virus", "bacteria", "dna", "rna",
            "genomic", "brain", "psychiatric", "neuron", "enzyme", "antibody"}
    if any(w in q for w in _bio):
        tools.append("pubmed_search")

    # CS / ML / Physics / Math
    _cs = {"algorithm", "machine learning", "neural", "deep learning", "model",
           "transformer", "gradient", "quantum", "computing", "cryptography",
           "optimization", "reinforcement", "embedding", "attention", "diffusion",
           "topology", "differential", "probability", "statistics"}
    if any(w in q for w in _cs):
        tools.append("arxiv_search")

    # Current events / recent data
    _recent = {"current", "recent", "latest", "new", "today", "news", "2024", "2025",
               "state of the art", "sota", "breakthrough", "emerging"}
    if any(w in q for w in _recent):
        tools.append("web_search")

    # General scholarly coverage
    tools.append("openalex_search")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique[:5]


async def _llm_select_tools(question: str, heuristic_picks: list[str]) -> list[str]:
    """Ask the LLM to refine/replace the heuristic tool list. Returns [] on any failure."""
    import json
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)

    import tools.builtin_tools  # noqa: F401
    from tools.tool_registry import list_tools
    from agents.llm_client import acall_llm

    all_tools = [t.name for t in list_tools()]

    tool_descriptions = "\n".join(
        f"  {t.name}: {t.description[:80]}"
        for t in list_tools()
    )
    prompt = (
        f"Research question: {question}\n\n"
        f"Available tools:\n{tool_descriptions}\n\n"
        "Select 2 to 5 tools that would provide the most useful real-time evidence for this question. "
        "Prefer live-data tools (web_search, wikipedia_search, semantic_scholar_search, pubmed_search, "
        "openalex_search, crossref_search, arxiv_search). "
        "Return ONLY a JSON array of tool name strings, e.g. [\"semantic_scholar_search\", \"pubmed_search\"]"
    )

    try:
        content = await acall_llm([{"role": "user", "content": prompt}], temperature=0.0, timeout=20)
        if content:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                names: list[str] = json.loads(content[start:end])
                valid = [n for n in names if n in set(all_tools)]
                if valid:
                    return valid[:5]
    except Exception:
        pass

    return []


async def tool_use_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    enabled = list(state.get("enabled_tools") or [])
    if not enabled:
        return state

    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)

    import tools.builtin_tools  # noqa: F401 — ensure registration
    from tools.tool_registry import call_tool

    results: list[dict] = []
    extracted_entities: list[dict] = []

    for tool_name in enabled:
        args: dict = {}
        question = state.get("question", "")
        project_id = state.get("project_id", "")
        if tool_name == "knowledge_search":
            args = {"query": question, "project_id": project_id, "top_k": 5}
        elif tool_name == "extract_entities":
            args = {"text": question}
        elif tool_name == "find_analogies":
            args = {"entities": extracted_entities, "project_id": project_id}
        elif tool_name == "arxiv_search":
            args = {"query": question, "max_results": 5}
        elif tool_name == "agent_run":
            args = {"agent_name": state.get("agent_name", "math_research_agent"), "question": question, "context": list(state.get("retrieved_chunks") or [])}
        # Sprint 7: real-time data tools
        elif tool_name == "web_search":
            args = {"query": question, "max_results": 5}
        elif tool_name == "web_browse":
            # browse first retrieved URL or skip if none
            chunks = list(state.get("retrieved_chunks") or [])
            import re as _re_tun
            url_match = _re_tun.search(r"https?://\S+", " ".join(chunks[:3]))
            args = {"url": url_match.group(0) if url_match else "https://en.wikipedia.org/wiki/" + question.replace(" ", "_")[:60], "max_chars": 3000}
        elif tool_name == "wikipedia_search":
            args = {"query": question, "top_k": 3}
        elif tool_name == "semantic_scholar_search":
            args = {"query": question, "max_results": 5}
        elif tool_name == "pubmed_search":
            args = {"query": question, "max_results": 5}
        elif tool_name == "crossref_search":
            args = {"query": question, "max_results": 5}
        elif tool_name == "openalex_search":
            args = {"query": question, "max_results": 5}

        tr = await call_tool(tool_name, args)
        result_dict = tr.to_dict()
        results.append(result_dict)

        # Pass entity output to find_analogies if both are enabled
        if tool_name == "extract_entities" and tr.success and isinstance(tr.output, list):
            extracted_entities = tr.output

    new_state = ResearchState(**state)
    new_state["tool_results"] = results

    # Merge real-time data into retrieved_chunks so hypothesis node sees it
    live_chunks: list[str] = []
    LIVE_TOOLS = {"web_search", "wikipedia_search", "semantic_scholar_search",
                  "pubmed_search", "crossref_search", "openalex_search", "web_browse", "arxiv_search"}
    for r in results:
        if not r.get("success") or r["tool_name"] not in LIVE_TOOLS:
            continue
        output = r.get("output")
        if isinstance(output, list):
            for item in output[:5]:
                if isinstance(item, dict):
                    parts = []
                    for field in ("title", "snippet", "summary", "abstract", "text"):
                        if item.get(field):
                            parts.append(str(item[field])[:300])
                    if parts:
                        live_chunks.append(" | ".join(parts))
        elif isinstance(output, dict) and output.get("text"):
            live_chunks.append(output["text"][:600])

    if live_chunks:
        existing = list(new_state.get("retrieved_chunks") or [])
        new_state["retrieved_chunks"] = existing + live_chunks

    return new_state


async def evaluate_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    if not state.get("enable_evaluation"):
        return state
    hypothesis_id = state.get("saved_hypothesis_id")
    if not hypothesis_id:
        return state
    db = (config or {}).get("configurable", {}).get("db")  # type: ignore[union-attr]
    if db is None:
        return state
    try:
        from app.services.evaluation_service import evaluate_hypothesis
        evaluation = await evaluate_hypothesis(db, hypothesis_id)
        if evaluation:
            new_state = ResearchState(**state)
            new_state["evaluation_score"] = evaluation.overall_score
            # Log to MLflow if run_id available
            if state.get("mlflow_run_id"):
                from tracking.mlflow_tracker import log_evaluation
                log_evaluation(state["mlflow_run_id"], evaluation.overall_score, evaluation.dimension_scores or [])
            return new_state
    except Exception:
        pass
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_ctx(state: ResearchState):
    from workflows.base_step import PipelineContext
    from agents.base_agent import AgentOutput

    return PipelineContext(
        question=state.get("question", ""),
        project_id=state.get("project_id", ""),
        experiment_id=state.get("experiment_id", ""),
        user_id=state.get("user_id", ""),
        agent_name=state.get("agent_name", "math_research_agent"),
        retrieved_chunks=list(state.get("retrieved_chunks") or []),
        retrieved_paper_ids=list(state.get("retrieved_paper_ids") or []),
        evidence_summary=state.get("evidence_summary", ""),
        hypothesis=state.get("hypothesis"),
        saved_hypothesis_id=state.get("saved_hypothesis_id"),
        debate_results=list(state.get("debate_results") or []),
        critique=state.get("critique"),
        enable_debate=state.get("enable_debate", False),
        enable_critique=state.get("enable_critique", False),
        contradictions=list(state.get("contradictions") or []),
        enable_contradiction_check=state.get("enable_contradiction_check", False),
        mlflow_run_id=state.get("mlflow_run_id"),
    )


def _from_ctx(base: ResearchState, ctx) -> ResearchState:
    return ResearchState(
        **{
            **base,
            "retrieved_chunks": ctx.retrieved_chunks,
            "retrieved_paper_ids": ctx.retrieved_paper_ids,
            "evidence_summary": ctx.evidence_summary,
            "hypothesis": ctx.hypothesis,
            "saved_hypothesis_id": ctx.saved_hypothesis_id,
            "debate_results": ctx.debate_results,
            "critique": ctx.critique,
            "contradictions": ctx.contradictions,
            "mlflow_run_id": ctx.mlflow_run_id,
        }
    )


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _make_checkpointer():
    try:
        import os
        if os.getenv("USE_SQLITE", "").lower() in ("true", "1", "yes"):
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            db_path = os.getenv("SQLITE_PATH", "/data/lab.db")
            checkpoints_path = db_path.replace(".db", "_checkpoints.db")
            return AsyncSqliteSaver.from_conn_string(checkpoints_path)
    except Exception:
        pass
    try:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    except Exception:
        return None


def _build_graph():
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        return None

    builder = StateGraph(ResearchState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("tool_selector", tool_selector_node)
    builder.add_node("tool_use", tool_use_node)
    builder.add_node("cross_domain", cross_domain_node)
    builder.add_node("contradiction", contradiction_node)
    builder.add_node("hypothesis", hypothesis_node)
    builder.add_node("critique", critique_node)
    builder.add_node("debate", debate_node)
    builder.add_node("save", save_node)
    builder.add_node("evaluate", evaluate_node)

    builder.set_entry_point("retrieve")
    builder.add_edge("retrieve", "summarize")
    builder.add_edge("summarize", "tool_selector")
    builder.add_edge("tool_selector", "tool_use")
    builder.add_edge("tool_use", "cross_domain")
    builder.add_edge("cross_domain", "contradiction")
    builder.add_edge("contradiction", "hypothesis")
    builder.add_edge("hypothesis", "critique")
    builder.add_edge("critique", "debate")
    builder.add_edge("debate", "save")
    builder.add_edge("save", "evaluate")
    builder.add_edge("evaluate", END)

    checkpointer = _make_checkpointer()
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


research_graph = _build_graph()
