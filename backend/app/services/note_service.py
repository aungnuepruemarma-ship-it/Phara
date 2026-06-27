import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate


async def list_notes(db: AsyncSession, project_id: uuid.UUID) -> Sequence[Note]:
    result = await db.execute(select(Note).where(Note.project_id == project_id).order_by(Note.updated_at.desc()))
    return result.scalars().all()


async def get_note(db: AsyncSession, note_id: uuid.UUID, project_id: uuid.UUID) -> Note:
    result = await db.execute(select(Note).where(Note.id == note_id, Note.project_id == project_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


async def create_note(db: AsyncSession, data: NoteCreate, project_id: uuid.UUID, author_id: uuid.UUID) -> Note:
    note = Note(id=uuid.uuid4(), project_id=project_id, author_id=author_id, **data.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def update_note(db: AsyncSession, note_id: uuid.UUID, data: NoteUpdate, project_id: uuid.UUID) -> Note:
    note = await get_note(db, note_id, project_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note_id: uuid.UUID, project_id: uuid.UUID) -> None:
    note = await get_note(db, note_id, project_id)
    await db.delete(note)
    await db.commit()
