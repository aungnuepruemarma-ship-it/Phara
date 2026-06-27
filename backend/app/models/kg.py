import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.hypothesis import Hypothesis


class KGEntity(Base):
    __tablename__ = "kg_entities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="concept")
    domain: Mapped[str] = mapped_column(String(100), nullable=False, server_default="general")
    description: Mapped[str | None] = mapped_column(Text)
    source_hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.8")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="kg_entities")
    source_hypothesis: Mapped["Hypothesis | None"] = relationship("Hypothesis")

    subject_relations: Mapped[list["KGRelation"]] = relationship(
        "KGRelation", foreign_keys="KGRelation.subject_id", back_populates="subject", cascade="all, delete-orphan"
    )
    object_relations: Mapped[list["KGRelation"]] = relationship(
        "KGRelation", foreign_keys="KGRelation.object_id", back_populates="object_entity"
    )


class KGRelation(Base):
    __tablename__ = "kg_relations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kg_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    # causes|enables|contradicts|extends|analogous_to|implements
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kg_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.7")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project")
    subject: Mapped["KGEntity"] = relationship("KGEntity", foreign_keys=[subject_id], back_populates="subject_relations")
    object_entity: Mapped["KGEntity"] = relationship("KGEntity", foreign_keys=[object_id], back_populates="object_relations")
