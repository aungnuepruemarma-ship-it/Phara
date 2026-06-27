from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, projects, papers, experiments, notes, research, admin, memory, reports
from app.routers import knowledge_graph, evaluation, simulations, tools, hypotheses

app = FastAPI(
    title="Universal Intelligence Lab API",
    description="AI research operating system for developing and testing theories of intelligence.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(papers.router, prefix=API_PREFIX)
app.include_router(experiments.router, prefix=API_PREFIX)
app.include_router(notes.router, prefix=API_PREFIX)
app.include_router(research.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(knowledge_graph.router, prefix=API_PREFIX)
app.include_router(evaluation.router, prefix=API_PREFIX)
app.include_router(simulations.router, prefix=API_PREFIX)
app.include_router(tools.router, prefix=API_PREFIX)
app.include_router(hypotheses.router, prefix=API_PREFIX)


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.on_event("startup")
async def on_startup():
    if settings.use_sqlite:
        import os
        os.makedirs(os.path.dirname(settings.sqlite_path), exist_ok=True)
        from app.database import engine, Base
        import app.models  # noqa: F401 — register all models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


# Serve Next.js static export when present (HF Spaces single-container mode)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "out"

if FRONTEND_DIR.exists():
    _next_dir = FRONTEND_DIR / "_next"
    if _next_dir.exists():
        app.mount("/_next", StaticFiles(directory=_next_dir), name="nextjs-assets")

    @app.get("/", include_in_schema=False)
    async def spa_root():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Try exact file match (e.g. favicon.ico, images)
        candidate = FRONTEND_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        # Try directory index (trailing-slash pages)
        index = candidate / "index.html"
        if index.is_file():
            return FileResponse(index)
        # SPA fallback
        return FileResponse(FRONTEND_DIR / "index.html")
