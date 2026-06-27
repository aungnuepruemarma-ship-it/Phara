import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.hypothesis import Hypothesis


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=True
    )
    simulation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    best_variant: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    variant_results: Mapped[list["SimulationVariantResult"]] = relationship(
        "SimulationVariantResult", back_populates="simulation", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_simulations_project_id", "project_id"),)


class SimulationVariantResult(Base):
    __tablename__ = "simulation_variant_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False
    )
    variant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    run_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True
    )
    evaluation_score: Mapped[float | None] = mapped_column(Float)
    verdict: Mapped[str | None] = mapped_column(String(20))
    dimension_scores: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="variant_results")

    __table_args__ = (Index("ix_simulation_variant_results_simulation_id", "simulation_id"),)
