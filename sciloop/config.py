"""Workspace + environment configuration. Stdlib only."""
from __future__ import annotations

import os
from pathlib import Path

# Workspace root: env override, else ./sciloop_data under the current directory.
WORKSPACE = Path(os.environ.get("SCILOOP_HOME", "./sciloop_data")).resolve()

DB_PATH = WORKSPACE / "sciloop.db"
GENOME_PATH = WORKSPACE / "genome.jsonl"
PAPERS_DIR = WORKSPACE / "papers"
TRACES_DIR = WORKSPACE / "traces"

# LLM configuration (OpenRouter, OpenAI-compatible). No key -> degraded mode.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Primary model + free fallbacks (all currently free on OpenRouter).
_DEFAULT_CHAIN = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
]


def model_chain() -> list[str]:
    primary = os.environ.get("SCILOOP_MODEL", "").strip()
    chain = ([primary] if primary else []) + _DEFAULT_CHAIN
    seen: set[str] = set()
    out: list[str] = []
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def llm_available() -> bool:
    return bool(OPENROUTER_API_KEY)


def ensure_workspace() -> Path:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    PAPERS_DIR.mkdir(exist_ok=True)
    TRACES_DIR.mkdir(exist_ok=True)
    return WORKSPACE
