import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.experiment import Experiment


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_paper_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    hypothesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    agent_used: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="hypotheses")
