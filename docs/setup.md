# Universal Intelligence Lab — Setup Guide

## Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.12+ (for local backend development)

## Quick Start (Docker)

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd Phara

# 2. Configure environment
cp .env.example .env
# Edit .env — at minimum set LLM_API_KEY if you want hypothesis generation

# 3. Start all services
docker compose up --build

# 4. Run migrations (first time only)
docker compose exec backend alembic upgrade head

# 5. Seed demo data
docker compose exec backend python /app/../datasets/seed_data.py

# 6. Open the app
# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/docs
# Qdrant:    http://localhost:6333/dashboard
```

## Default Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@lab.local | Admin1234! |
| Researcher | researcher@lab.local | Research123! |

## Local Development (no Docker)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set env vars (copy .env.example to .env and adjust localhost URLs)
export DATABASE_URL=postgresql+asyncpg://phara:changeme@localhost:5432/pharalab
export QDRANT_HOST=localhost

alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev
```

## Running Tests
```bash
cd backend
pip install -r requirements.txt
pip install aiosqlite  # for in-memory test DB
pytest tests/ -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis URL | `redis://redis:6379/0` |
| `QDRANT_HOST` | Qdrant hostname | `qdrant` |
| `SECRET_KEY` | JWT signing key | *(change in prod)* |
| `LLM_API_KEY` | OpenAI-compatible API key | *(required for hypothesis gen)* |
| `LLM_BASE_URL` | LLM API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model ID | `gpt-4o-mini` |

## Architecture Overview
See [architecture.md](./architecture.md) for the full system design.
