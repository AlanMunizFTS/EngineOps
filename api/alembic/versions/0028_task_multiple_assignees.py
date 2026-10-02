"""allow multiple assignees per task

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-02

The legacy ``tasks.assignee_id`` column remains as a compatibility projection
of the first assignee. Existing assignments are copied into the new relation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_assignees",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "user_id"),
    )
    op.create_index("ix_task_assignees_user_id", "task_assignees", ["user_id"])
    op.execute("""
        INSERT INTO task_assignees (task_id, user_id, position)
        SELECT id, assignee_id, 0
        FROM tasks
        WHERE assignee_id IS NOT NULL
        """)


def downgrade() -> None:
    op.drop_index("ix_task_assignees_user_id", table_name="task_assignees")
    op.drop_table("task_assignees")
