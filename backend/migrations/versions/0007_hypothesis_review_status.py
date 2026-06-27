"""Add review_status, review_notes, reviewed_at to hypotheses

Revision ID: 0007
Revises: 0006
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hypotheses",
        sa.Column("review_status", sa.String(20), nullable=True, server_default="candidate"),
    )
    op.add_column(
        "hypotheses",
        sa.Column("review_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "hypotheses",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hypotheses_review_status", "hypotheses", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_hypotheses_review_status", "hypotheses")
    op.drop_column("hypotheses", "reviewed_at")
    op.drop_column("hypotheses", "review_notes")
    op.drop_column("hypotheses", "review_status")
