import os
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.paper import Paper
from app.schemas.paper import PaperMetadata


async def list_papers(db: AsyncSession, project_id: uuid.UUID):
    result = await db.execute(select(Paper).where(Paper.project_id == project_id).order_by(Paper.uploaded_at.desc()))
    return result.scalars().all()


async def get_paper(db: AsyncSession, paper_id: uuid.UUID, project_id: uuid.UUID) -> Paper:
    result = await db.execute(select(Paper).where(Paper.id == paper_id, Paper.project_id == project_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return paper


async def upload_paper(
    db: AsyncSession,
    file: UploadFile,
    metadata: PaperMetadata,
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> Paper:
    upload_dir = Path(settings.upload_dir) / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    paper_id = uuid.uuid4()
    file_path = upload_dir / f"{paper_id}.pdf"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    paper = Paper(
        id=paper_id,
        project_id=project_id,
        title=metadata.title,
        authors=metadata.authors,
        abstract=metadata.abstract,
        year=metadata.year,
        doi=metadata.doi,
        file_path=str(file_path),
        embedding_status="pending",
        qdrant_collection="papers",
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    background_tasks.add_task(_embed_paper, str(paper.id), str(file_path), str(project_id))
    return paper


def _embed_paper(paper_id: str, file_path: str, project_id: str) -> None:
    """Background task: parse PDF, chunk, embed, upsert to Qdrant, update status."""
    import asyncio
    from app.database import AsyncSessionLocal
    from sqlalchemy import update as sql_update
    from app.models.paper import Paper as PaperModel

    try:
        from tools.pdf_parser import extract_text
        from tools.text_chunker import chunk_text
        from memory.vector_store import upsert_paper

        text = extract_text(file_path)
        chunks = chunk_text(text, size=settings.chunk_size, overlap=settings.chunk_overlap)
        count = upsert_paper(paper_id, chunks, project_id)

        async def _update_status():
            async with AsyncSessionLocal() as session:
                await session.execute(
                    sql_update(PaperModel)
                    .where(PaperModel.id == paper_id)
                    .values(embedding_status="done", chunk_count=count)
                )
                await session.commit()

        asyncio.run(_update_status())
    except Exception:
        async def _mark_failed():
            async with AsyncSessionLocal() as session:
                await session.execute(
                    sql_update(PaperModel)
                    .where(PaperModel.id == paper_id)
                    .values(embedding_status="failed")
                )
                await session.commit()

        asyncio.run(_mark_failed())


async def delete_paper(db: AsyncSession, paper_id: uuid.UUID, project_id: uuid.UUID) -> None:
    paper = await get_paper(db, paper_id, project_id)
    try:
        from memory.vector_store import delete_paper_vectors
        delete_paper_vectors(str(paper_id))
    except Exception:
        pass
    if os.path.exists(paper.file_path):
        os.remove(paper.file_path)
    await db.delete(paper)
    await db.commit()
