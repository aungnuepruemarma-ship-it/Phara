import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.services import note_service

router = APIRouter(prefix="/projects/{project_id}/notes", tags=["notes"])


@router.get("", response_model=list[NoteOut])
async def list_notes(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.list_notes(db, project_id)


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    project_id: uuid.UUID,
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.create_note(db, body, project_id, current_user.id)


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    project_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.get_note(db, note_id, project_id)


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(
    project_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.update_note(db, note_id, body, project_id)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    project_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await note_service.delete_note(db, note_id, project_id)
