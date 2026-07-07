"""Knowledge Genome v1 — 'reasoning DNA' as append-only JSONL.

Each record is a self-describing recipe to regenerate a strategy/operator,
with provenance (the evidence ids that justified it). Instead of saving prompts,
we save the certified, reproducible artifact + how it was earned.
"""
from __future__ import annotations

import json
import time
from typing import List

from . import config


def _read() -> List[dict]:
    path = config.GENOME_PATH
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def add_record(kind: str, name: str, recipe: dict, provenance: List[str],
               notes: str = "") -> dict:
    """Append a DNA record. kind e.g. 'operator' | 'strategy'."""
    config.ensure_workspace()
    rec = {
        "id": f"dna_{int(time.time()*1000)%10_000_000}",
        "kind": kind, "name": name, "recipe": recipe,
        "provenance": provenance, "notes": notes, "created_at": time.time(),
    }
    with open(config.GENOME_PATH, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def has(name: str) -> bool:
    return any(r.get("name") == name for r in _read())


def records() -> List[dict]:
    return _read()


def summary() -> dict:
    recs = _read()
    kinds: dict = {}
    for r in recs:
        kinds[r.get("kind", "?")] = kinds.get(r.get("kind", "?"), 0) + 1
    return {"total": len(recs), "by_kind": kinds,
            "names": [r.get("name") for r in recs[-10:]]}
