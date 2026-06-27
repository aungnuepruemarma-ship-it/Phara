"""simulations and simulation_variant_results tables

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "simulations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("experiment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("simulation_type", sa.String(50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("best_variant", sa.String(200), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_simulations_project_id", "simulations", ["project_id"])

    op.create_table(
        "simulation_variant_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("simulation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_name", sa.String(200), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("run_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hypothesis_id", sa.Uuid(as_uuid=True), sa.ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evaluation_score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(20), nullable=True),
        sa.Column("dimension_scores", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_simulation_variant_results_simulation_id", "simulation_variant_results", ["simulation_id"])


def downgrade():
    op.drop_index("ix_simulation_variant_results_simulation_id", "simulation_variant_results")
    op.drop_table("simulation_variant_results")
    op.drop_index("ix_simulations_project_id", "simulations")
    op.drop_table("simulations")
