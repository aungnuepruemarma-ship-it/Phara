"""hypothesis_evaluations table

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hypothesis_evaluations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("hypothesis_id", sa.Uuid(as_uuid=True), sa.ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("dimension_scores", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("benchmark_scores", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hypothesis_evaluations_hypothesis_id", "hypothesis_evaluations", ["hypothesis_id"])
    op.create_index("ix_hypothesis_evaluations_project_id", "hypothesis_evaluations", ["project_id"])


def downgrade():
    op.drop_index("ix_hypothesis_evaluations_project_id", "hypothesis_evaluations")
    op.drop_index("ix_hypothesis_evaluations_hypothesis_id", "hypothesis_evaluations")
    op.drop_table("hypothesis_evaluations")
