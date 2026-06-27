import os
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.paper import Paper
from app.schemas.paper import PaperMetadata


# ── Storage helpers ────────────────────────────────────────────────────────────

def _r2_key(project_id: str, paper_id: str) -> str:
    return f"papers/{project_id}/{paper_id}.pdf"


def _upload_to_r2(content: bytes, key: str) -> str:
    """Upload bytes to Cloudflare R2; returns the R2 object key."""
    import boto3  # type: ignore
    from botocore.config import Config  # type: ignore

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.effective_r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    s3.put_object(Bucket=settings.r2_bucket_name, Key=key, Body=content, ContentType="application/pdf")
    return key


def _download_from_r2(key: str) -> bytes:
    """Download object from R2 and return raw bytes."""
    import boto3  # type: ignore
    from botocore.config import Config  # type: ignore

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.effective_r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    resp = s3.get_object(Bucket=settings.r2_bucket_name, Key=key)
    return resp["Body"].read()


def _delete_from_r2(key: str) -> None:
    import boto3  # type: ignore
    from botocore.config import Config  # type: ignore

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.effective_r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    s3.delete_object(Bucket=settings.r2_bucket_name, Key=key)


def _save_file(content: bytes, project_id: str, paper_id: str) -> str:
    """Persist PDF to R2 (if enabled) or local disk. Returns path/key string."""
    if settings.use_r2_storage:
        key = _r2_key(project_id, paper_id)
        _upload_to_r2(content, key)
        return f"r2://{key}"

    upload_dir = Path(settings.upload_dir) / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{paper_id}.pdf"
    file_path.write_bytes(content)
    return str(file_path)


def _read_file(file_path: str) -> bytes:
    """Read PDF bytes from R2 or local disk based on path prefix."""
    if file_path.startswith("r2://"):
        return _download_from_r2(file_path[5:])  # strip "r2://"
    return Path(file_path).read_bytes()


def _delete_file(file_path: str) -> None:
    if file_path.startswith("r2://"):
        _delete_from_r2(file_path[5:])
    elif os.path.exists(file_path):
        os.remove(file_path)


# ── Service functions ──────────────────────────────────────────────────────────

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
    paper_id = uuid.uuid4()
    content = await file.read()
    stored_path = _save_file(content, str(project_id), str(paper_id))

    paper = Paper(
        id=paper_id,
        project_id=project_id,
        title=metadata.title,
        authors=metadata.authors,
        abstract=metadata.abstract,
        year=metadata.year,
        doi=metadata.doi,
        file_path=stored_path,
        embedding_status="pending",
        qdrant_collection="papers",
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    background_tasks.add_task(_embed_paper, str(paper.id), stored_path, str(project_id))
    return paper


def _embed_paper(paper_id: str, file_path: str, project_id: str) -> None:
    """Background task: parse PDF, chunk, embed, upsert to Qdrant, update status."""
    import asyncio
    import tempfile
    from app.database import AsyncSessionLocal
    from sqlalchemy import update as sql_update
    from app.models.paper import Paper as PaperModel

    try:
        from tools.pdf_parser import extract_text
        from tools.text_chunker import chunk_text
        from memory.vector_store import upsert_paper
        from workflows.steps.index_knowledge_step import index_paper_knowledge

        # For R2-stored files, download to a temp file for PDF parsing
        if file_path.startswith("r2://"):
            raw = _read_file(file_path)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw)
                local_path = tmp.name
        else:
            local_path = file_path

        text = extract_text(local_path)
        chunks = chunk_text(text, size=settings.chunk_size, overlap=settings.chunk_overlap)
        count = upsert_paper(paper_id, chunks, project_id)
        index_paper_knowledge(paper_id, chunks, project_id)

        if file_path.startswith("r2://") and os.path.exists(local_path):
            os.remove(local_path)

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
    _delete_file(paper.file_path)
    await db.delete(paper)
    await db.commit()
