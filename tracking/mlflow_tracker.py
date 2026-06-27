"""
MLflow experiment tracking wrapper.

All UIL experiments map to MLflow experiments by project_id.
Each research workflow run maps to one MLflow run.

Set MLFLOW_TRACKING_URI to override storage location.
Default: file:///data/mlruns  (HF Spaces persistent volume)
       or ./mlruns             (local dev)
"""
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

_DEFAULT_URI = (
    "file:///data/mlruns" if Path("/data").exists()
    else str(Path(__file__).resolve().parents[1] / "mlruns")
)


def _setup():
    if not _MLFLOW_AVAILABLE:
        return
    uri = os.getenv("MLFLOW_TRACKING_URI", _DEFAULT_URI)
    mlflow.set_tracking_uri(uri)


_setup()


@dataclass
class RunMetrics:
    confidence_score: float = 0.0
    retrieved_paper_count: int = 0
    chunk_count: int = 0
    contradiction_count: int = 0
    debate_enabled: bool = False
    critique_enabled: bool = False


@dataclass
class RunParams:
    question: str = ""
    agent_name: str = ""
    project_id: str = ""
    experiment_id: str = ""


def _get_or_create_experiment(project_id: str, project_name: str = "") -> str:
    """Return mlflow experiment_id, creating it if needed."""
    exp_name = f"project/{project_id}"
    experiment = mlflow.get_experiment_by_name(exp_name)
    if experiment is None:
        tags = {"project_id": project_id}
        if project_name:
            tags["project_name"] = project_name
        exp_id = mlflow.create_experiment(exp_name, tags=tags)
        return exp_id
    return experiment.experiment_id


def log_research_run(
    params: RunParams,
    metrics: RunMetrics,
    hypothesis_text: str = "",
    evidence_summary: str = "",
    project_name: str = "",
) -> str | None:
    """Log one research workflow run to MLflow. Returns run_id or None if MLflow unavailable."""
    if not _MLFLOW_AVAILABLE:
        return None
    try:
        exp_id = _get_or_create_experiment(params.project_id, project_name)
        with mlflow.start_run(experiment_id=exp_id) as run:
            mlflow.log_params({
                "question": params.question[:250],
                "agent_name": params.agent_name,
                "project_id": params.project_id,
                "experiment_id": params.experiment_id,
            })
            mlflow.log_metrics({
                "confidence_score": metrics.confidence_score,
                "retrieved_paper_count": float(metrics.retrieved_paper_count),
                "chunk_count": float(metrics.chunk_count),
                "contradiction_count": float(metrics.contradiction_count),
                "debate_enabled": float(metrics.debate_enabled),
                "critique_enabled": float(metrics.critique_enabled),
            })
            if hypothesis_text:
                mlflow.set_tag("hypothesis_preview", hypothesis_text[:500])
            if evidence_summary:
                mlflow.set_tag("evidence_summary_preview", evidence_summary[:300])
            return run.info.run_id
    except Exception:
        return None


def log_evaluation(run_id: str, overall_score: float, dimension_scores: list[dict]) -> None:
    """Attach evaluation metrics to an existing MLflow run."""
    if not _MLFLOW_AVAILABLE or not run_id:
        return
    try:
        with mlflow.start_run(run_id=run_id):
            metrics: dict[str, float] = {"eval_overall_score": overall_score}
            for dim in dimension_scores:
                key = f"eval_{dim.get('name', 'unknown')}"
                metrics[key] = float(dim.get("score", 0.0))
            mlflow.log_metrics(metrics)
    except Exception:
        pass


def get_runs_for_project(project_id: str, max_results: int = 50) -> list[dict]:
    """Return recent MLflow runs for a project as plain dicts."""
    if not _MLFLOW_AVAILABLE:
        return []
    try:
        exp_name = f"project/{project_id}"
        experiment = mlflow.get_experiment_by_name(exp_name)
        if experiment is None:
            return []
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=max_results,
            order_by=["start_time DESC"],
        )
        return runs.to_dict(orient="records") if not runs.empty else []
    except Exception:
        return []
