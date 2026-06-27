"""
knowledge_extractor — extract reusable lessons from a simulation result
and store them in the project knowledge base with kind="simulation_lesson".

Lessons are surfaced by the knowledge_search tool in future research runs,
so insights from past simulations inform future hypothesis generation.
"""
from __future__ import annotations

import json
import uuid


from simulations.types import SimulationResult

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None


async def extract_simulation_lessons(result: SimulationResult, project_id: str) -> int:
    """Extract lessons and store in knowledge base. Returns number of entries stored."""
    lessons = await _generate_lessons(result)
    if not lessons:
        return 0

    from memory.knowledge_memory import KnowledgeEntry, store_knowledge

    entries = [
        KnowledgeEntry(
            entry_id=str(uuid.uuid4()),
            text=lesson,
            source_paper_id=result.simulation_id,
            project_id=project_id,
            kind="simulation_lesson",
        )
        for lesson in lessons
    ]
    try:
        return store_knowledge(entries)
    except Exception:
        return 0


async def _generate_lessons(result: SimulationResult) -> list[str]:
    try:
        return await _llm_lessons(result)
    except Exception:
        pass
    return _heuristic_lessons(result)


async def _llm_lessons(result: SimulationResult) -> list[str]:
    from agents.llm_client import acall_llm
    prompt = (
        "You are analyzing a completed research simulation. "
        "Extract exactly 3 concise, actionable lessons learned.\n\n"
        f"Simulation type: {result.config.simulation_type}\n"
        f"Question: {result.config.question}\n"
        f"Best variant: {result.best_variant or 'N/A'}\n"
        f"Summary: {json.dumps(result.summary)}\n\n"
        "Return ONLY a JSON array of 3 lesson strings. "
        'Example: ["Lesson 1", "Lesson 2", "Lesson 3"]'
    )
    text = await acall_llm([{"role": "user", "content": prompt}], temperature=0.3, timeout=30)
    if not text:
        raise ValueError("No LLM configured")
    start, end = text.find("["), text.rfind("]") + 1
    if start >= 0 and end > start:
        parsed = json.loads(text[start:end])
        return [str(l) for l in parsed if l][:3]
    return []


def _heuristic_lessons(result: SimulationResult) -> list[str]:
    lessons: list[str] = []
    sim_type = result.config.simulation_type
    question = result.config.question[:80]

    if result.best_variant and result.summary:
        best_stats = result.summary.get(result.best_variant, {})
        mean = best_stats.get("mean", 0.0)
        lessons.append(
            f"Simulation '{sim_type}' on '{question}': variant '{result.best_variant}' "
            f"achieved the highest mean score ({mean:.0%})."
        )

        if len(result.summary) > 1:
            worst = min(result.summary, key=lambda v: result.summary[v].get("mean", 0))
            diff = mean - result.summary[worst].get("mean", 0)
            if diff > 0.03:
                lessons.append(
                    f"'{result.best_variant}' outperformed '{worst}' by {diff:.0%} — "
                    f"prefer this configuration for similar questions."
                )

    if "ablation" in sim_type:
        component = sim_type.replace("_ablation", "")
        lessons.append(
            f"{component.title()} ablation test completed. Compare variant scores to quantify "
            f"the contribution of the {component} component to hypothesis quality."
        )
    elif sim_type == "adversarial_simulation":
        lessons.append(
            f"Adversarial test completed for '{question}'. "
            "Low score gap between clean and adversarial variants suggests robustness."
        )
    elif sim_type == "stability_test" and result.summary:
        stds = [v.get("std", 0.0) for v in result.summary.values()]
        avg_std = sum(stds) / len(stds) if stds else 0.0
        level = "low" if avg_std < 0.05 else ("moderate" if avg_std < 0.15 else "high")
        lessons.append(
            f"Stability test shows {level} variance (avg std={avg_std:.3f}). "
            f"{'Results are reproducible.' if level == 'low' else 'Consider averaging multiple runs.'}"
        )
    elif sim_type == "scaling_simulation":
        lessons.append(
            f"Scaling test for '{question}' completed. "
            "Higher retrieval_top_k may improve coverage at the cost of latency."
        )

    if not lessons:
        lessons.append(
            f"Simulation '{sim_type}' completed for '{question}'. "
            f"Review variant_results to identify the optimal configuration."
        )

    return lessons[:3]
