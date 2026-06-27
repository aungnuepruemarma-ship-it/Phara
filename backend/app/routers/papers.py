import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.paper import PaperMetadata, PaperOut, PaperStatusOut
from app.services import paper_service

router = APIRouter(prefix="/projects/{project_id}/papers", tags=["papers"])


@router.get("", response_model=list[PaperOut])
async def list_papers(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await paper_service.list_papers(db, project_id)


@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meta = PaperMetadata(**json.loads(metadata))
    return await paper_service.upload_paper(db, file, meta, project_id, background_tasks)


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await paper_service.get_paper(db, paper_id, project_id)


@router.get("/{paper_id}/status", response_model=PaperStatusOut)
async def get_paper_status(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper = await paper_service.get_paper(db, paper_id, project_id)
    return PaperStatusOut(id=paper.id, embedding_status=paper.embedding_status, chunk_count=paper.chunk_count)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await paper_service.delete_paper(db, paper_id, project_id)
