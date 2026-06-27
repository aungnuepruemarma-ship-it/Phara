"""
SimulationRunner — orchestrates multiple research_graph invocations for comparative analysis.

Supports three simulation types:
  agent_sweep      — same question, different agents
  parameter_sweep  — same agent, vary workflow flags (debate/critique/contradiction)
  stability_test   — same config repeated N times, measure score variance
"""
from __future__ import annotations

import math
import uuid

from simulations.types import SimulationConfig, SimulationResult, VariantResult


class SimulationRunner:
    async def run(self, config: SimulationConfig, db, simulation_id: str) -> SimulationResult:
        from workflows.research_graph import research_graph

        all_results: list[VariantResult] = []

        for variant in config.variants:
            for run_i in range(max(1, config.runs_per_variant)):
                thread_id = f"{config.experiment_id}_{variant.name}_{run_i}_{uuid.uuid4().hex[:6]}"
                state = {
                    "question": config.question,
                    "project_id": config.project_id,
                    "experiment_id": config.experiment_id,
                    "user_id": config.user_id,
                    "agent_name": variant.agent_name,
                    "enable_debate": variant.enable_debate,
                    "enable_critique": variant.enable_critique,
                    "enable_contradiction_check": variant.enable_contradiction_check,
                    "enable_evaluation": True,
                    "retrieved_chunks": [],
                    "retrieved_paper_ids": [],
                    "debate_results": [],
                    "contradictions": [],
                    "cross_domain_insights": [],
                    "kg_entities_created": [],
                }

                hypothesis_id: str | None = None
                eval_score: float | None = None
                verdict: str | None = None
                dimension_scores: list[dict] = []

                try:
                    if research_graph is not None:
                        final = await research_graph.ainvoke(
                            state,
                            config={"configurable": {"thread_id": thread_id, "db": db}},
                        )
                        hypothesis_id = final.get("saved_hypothesis_id")
                        eval_score = final.get("evaluation_score")
                        # Pull dimension scores from DB if available
                        if hypothesis_id:
                            dimension_scores = await _fetch_dimension_scores(db, hypothesis_id)
                            if verdict is None and eval_score is not None:
                                from evaluation.rubrics import VERDICT_THRESHOLDS
                                if eval_score >= VERDICT_THRESHOLDS["strong"]:
                                    verdict = "strong"
                                elif eval_score >= VERDICT_THRESHOLDS["moderate"]:
                                    verdict = "moderate"
                                else:
                                    verdict = "weak"
                    else:
                        # LangGraph not available — run heuristic scorer directly
                        eval_score, verdict, dimension_scores = await _heuristic_fallback(
                            config.question, variant.agent_name
                        )
                except Exception:
                    pass

                all_results.append(VariantResult(
                    variant_name=variant.name,
                    agent_name=variant.agent_name,
                    run_index=run_i,
                    hypothesis_id=hypothesis_id,
                    evaluation_score=eval_score,
                    verdict=verdict,
                    dimension_scores=dimension_scores,
                ))

        return _aggregate(simulation_id, config, all_results)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch_dimension_scores(db, hypothesis_id: str) -> list[dict]:
    try:
        import uuid as _uuid
        from sqlalchemy import select
        from app.models.evaluation import HypothesisEvaluation
        result = await db.execute(
            select(HypothesisEvaluation.dimension_scores)
            .where(HypothesisEvaluation.hypothesis_id == _uuid.UUID(hypothesis_id))
            .order_by(HypothesisEvaluation.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row or []
    except Exception:
        return []


async def _heuristic_fallback(question: str, agent_name: str):
    from evaluation.scorer import _heuristic_score
    rubric = _heuristic_score(
        hypothesis_text=f"Hypothesis generated for: {question}",
        evidence_summary="",
        cross_domain_insights=[],
        prior_hypotheses=[],
    )
    dims = [{"name": d.name, "score": d.score, "reasoning": d.reasoning} for d in rubric.dimensions]
    return rubric.overall, rubric.verdict, dims


def _aggregate(simulation_id: str, config: SimulationConfig, results: list[VariantResult]) -> SimulationResult:
    # Group by variant name
    variant_scores: dict[str, list[float]] = {}
    for r in results:
        if r.evaluation_score is not None:
            variant_scores.setdefault(r.variant_name, []).append(r.evaluation_score)

    summary: dict[str, dict] = {}
    for vname, scores in variant_scores.items():
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0.0
        summary[vname] = {
            "mean": round(mean, 4),
            "std": round(math.sqrt(variance), 4),
            "runs": len(scores),
        }

    best_variant = max(summary, key=lambda v: summary[v]["mean"]) if summary else None

    return SimulationResult(
        simulation_id=simulation_id,
        config=config,
        variant_results=results,
        best_variant=best_variant,
        summary=summary,
    )
