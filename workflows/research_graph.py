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


# ---------------------------------------------------------------------------
# Node functions — each wraps one existing workflow step
# ---------------------------------------------------------------------------

async def retrieve_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.retrieve_papers import RetrievePapersStep
    from app.config import settings
    from workflows.base_step import PipelineContext

    ctx = _to_ctx(state)
    ctx = await RetrievePapersStep(top_k=settings.retrieval_top_k).execute(ctx)
    return _from_ctx(state, ctx)


async def summarize_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
    from workflows.steps.summarize_evidence import SummarizeEvidenceStep
    from workflows.base_step import PipelineContext

    ctx = _to_ctx(state)
    ctx = await SummarizeEvidenceStep().execute(ctx)
    return _from_ctx(state, ctx)


async def cross_domain_node(state: ResearchState, config: RunnableConfig | None = None) -> ResearchState:
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

    # Populate KG (best-effort)
    kg_ids: list[str] = []
    if ctx.saved_hypothesis_id:
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
    builder.add_node("cross_domain", cross_domain_node)
    builder.add_node("contradiction", contradiction_node)
    builder.add_node("hypothesis", hypothesis_node)
    builder.add_node("critique", critique_node)
    builder.add_node("debate", debate_node)
    builder.add_node("save", save_node)
    builder.add_node("evaluate", evaluate_node)

    builder.set_entry_point("retrieve")
    builder.add_edge("retrieve", "summarize")
    builder.add_edge("summarize", "cross_domain")
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
