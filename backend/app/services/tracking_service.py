"""Exposes MLflow tracking data through the API layer."""
import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[4])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def get_runs(project_id: str, max_results: int = 50) -> list[dict]:
    try:
        from tracking.mlflow_tracker import get_runs_for_project
        raw = get_runs_for_project(project_id, max_results=max_results)
    except Exception:
        return []

    runs = []
    for r in raw:
        run_id = r.get("run_id") or r.get("info.run_id", "")
        status = r.get("status") or r.get("info.status", "")
        start = r.get("start_time") or r.get("info.start_time")
        params = {k.replace("params.", ""): v for k, v in r.items() if k.startswith("params.")}
        metrics = {k.replace("metrics.", ""): v for k, v in r.items() if k.startswith("metrics.")}
        tags = {k.replace("tags.", ""): v for k, v in r.items() if k.startswith("tags.") and not k.startswith("tags.mlflow")}
        runs.append({
            "run_id": str(run_id),
            "status": str(status),
            "start_time": str(start) if start else None,
            "params": params,
            "metrics": metrics,
            "tags": tags,
        })
    return runs
