# Universal Intelligence Lab — Architecture

## System Overview

```
┌─────────────────┐     HTTP/JSON     ┌──────────────────┐
│   Next.js 14    │ ◄───────────────► │   FastAPI        │
│   Frontend      │                   │   Backend        │
│   :3000         │                   │   :8000          │
└─────────────────┘                   └────────┬─────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
             ┌──────▼──────┐          ┌───────▼──────┐          ┌───────▼──────┐
             │ PostgreSQL  │          │    Qdrant    │          │    Redis     │
             │ :5432       │          │  Vector DB   │          │  Cache/Queue │
             │             │          │  :6333       │          │  :6379       │
             └─────────────┘          └──────────────┘          └──────────────┘
```

## Backend Package Structure

```
backend/app/
├── main.py          — FastAPI app factory, CORS, router mounting
├── config.py        — pydantic-settings Settings (reads from env)
├── database.py      — async SQLAlchemy engine + Base
├── dependencies.py  — get_db, get_current_user, require_role
├── models/          — SQLAlchemy ORM models (6 tables)
├── schemas/         — Pydantic request/response models
├── routers/         — FastAPI routers (one per resource)
└── services/        — Business logic (no HTTP concerns)
```

## Research Workflow Pipeline

```
POST /api/v1/research/run
         │
         ▼
ResearchPipeline.run(PipelineContext)
         │
         ├─► RetrievePapersStep
         │     embed(question) → Qdrant search → ctx.retrieved_chunks
         │
         ├─► SummarizeEvidenceStep
         │     LLM summarize chunks → ctx.evidence_summary
         │
         ├─► GenerateHypothesisStep
         │     agent_registry.get_agent(name).arun() → ctx.hypothesis
         │
         └─► SaveExperimentStep
               INSERT Hypothesis + UPDATE Experiment status
```

## Agent Extension Pattern

To add a new specialist agent:

1. Create `agents/new_agent.py` inheriting `BaseAgent`
2. Implement `run()` and `arun()` 
3. Add to `AGENT_REGISTRY` in `agents/agent_registry.py`
4. Available immediately via `GET /api/v1/research/agents` and selectable in the UI

## Data Flow: Paper Upload → Vector Search

```
Upload PDF
    │ FastAPI multipart
    ▼
paper_service.upload_paper()
    │ save file to uploads/
    │ INSERT Paper (status=pending)
    │ BackgroundTask
    ▼
_embed_paper()
    │ tools/pdf_parser.py  → extract text
    │ tools/text_chunker.py → chunk (512 words, 64 overlap)
    │ memory/embedder.py   → SentenceTransformer encode
    │ memory/vector_store.py → Qdrant upsert (payload: paper_id, project_id)
    ▼
UPDATE Paper (status=done, chunk_count=N)
```

## Security Model

- JWT tokens signed with `SECRET_KEY` (HS256), expiry configurable
- Passwords hashed with bcrypt
- Project data scoped to `owner_id` — users only see their own projects
- Role-based access: `admin` role required for `/api/v1/admin/*` endpoints
- CORS restricted to frontend origin

## Extension Points

| Area | How to extend |
|------|---------------|
| New agent | Implement `BaseAgent`, register in `agent_registry.py` |
| New workflow step | Implement `BaseWorkflowStep`, insert in `ResearchPipeline` |
| Background processing | Replace `BackgroundTasks` with Celery + Redis broker |
| Caching | Wrap `research_service` with `redis.get/set(hash(question+project))` |
| Simulations | Add long-running jobs to `simulations/` using Celery |
| Evaluation | Add model evaluation pipelines to `evaluation/` |
