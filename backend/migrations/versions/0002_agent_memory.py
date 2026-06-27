"""Add agent_memories table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False, server_default="learning"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_question", sa.Text(), server_default=""),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_memories_project_id", "agent_memories", ["project_id"])
    op.create_index("ix_agent_memories_agent_name", "agent_memories", ["agent_name"])


def downgrade() -> None:
    op.drop_index("ix_agent_memories_agent_name", table_name="agent_memories")
    op.drop_index("ix_agent_memories_project_id", table_name="agent_memories")
    op.drop_table("agent_memories")
