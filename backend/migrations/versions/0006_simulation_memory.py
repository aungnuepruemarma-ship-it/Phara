"""Add full_state column to simulation_variant_results (simulation memory)

Revision ID: 0006
Revises: 0005
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "simulation_variant_results",
        sa.Column("full_state", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("simulation_variant_results", "full_state")
