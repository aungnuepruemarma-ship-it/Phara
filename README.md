---
title: Universal Intelligence Lab
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# Universal Intelligence Lab

An AI research operating system for developing and testing new theories of intelligence.

## Features

- **Project Management** — Organize research into projects with tags
- **Paper Upload** — Upload PDFs; text is chunked and embedded into a vector store
- **Experiments** — Track experimental setups with parameters and status history
- **Research Notes** — Markdown notes per project
- **Research Workflow** — Ask a question, retrieve relevant papers, summarize evidence, generate a hypothesis
- **Math Research Agent** — Specialist agent with math-aware reasoning
- **Modular Architecture** — Add new specialist agents and workflow steps without touching existing code

## Running Locally (Docker Compose — full stack)

```bash
cp .env.example .env          # add LLM_API_KEY for hypothesis generation
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python datasets/seed_data.py
```

Open `http://localhost:3000` — login with `admin@lab.local` / `Admin1234!`

## Running Locally (single container — HF Spaces mode)

```bash
docker build -t uil .
docker run -p 7860:7860 \
  -e SECRET_KEY=change-me \
  -e LLM_API_KEY=sk-your-key \
  uil
```

Open `http://localhost:7860`

## Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Backend | FastAPI + SQLAlchemy 2.0 (async) |
| Database | PostgreSQL (local) / SQLite (HF Spaces) |
| Vector Store | Qdrant (local) / in-memory (HF Spaces) |
| Embeddings | SentenceTransformers `all-MiniLM-L6-v2` |
| Auth | JWT + bcrypt, roles: admin / researcher |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key |
| `LLM_API_KEY` | OpenAI-compatible key (for hypothesis generation) |
| `LLM_BASE_URL` | LLM API base URL (default: OpenAI) |
| `USE_SQLITE` | `true` to use SQLite instead of PostgreSQL |
| `QDRANT_IN_MEMORY` | `true` to use in-memory Qdrant |
