import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.hypothesis import Hypothesis


class HypothesisEvaluation(Base):
    __tablename__ = "hypothesis_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[list] = mapped_column(JSON, default=list)
    benchmark_scores: Mapped[list] = mapped_column(JSON, default=list)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    hypothesis: Mapped["Hypothesis"] = relationship("Hypothesis")

    __table_args__ = (
        Index("ix_hypothesis_evaluations_hypothesis_id", "hypothesis_id"),
        Index("ix_hypothesis_evaluations_project_id", "project_id"),
    )
