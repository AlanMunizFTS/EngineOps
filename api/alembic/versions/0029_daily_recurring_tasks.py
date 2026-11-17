"""add daily recurring tasks

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("repeat_daily", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "recurrence_parent_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_tasks_recurrence_parent_id_tasks",
        "tasks",
        "tasks",
        ["recurrence_parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tasks_recurrence_parent_id",
        "tasks",
        ["recurrence_parent_id"],
        unique=True,
    )
    op.alter_column("tasks", "repeat_daily", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tasks_recurrence_parent_id", table_name="tasks")
    op.drop_constraint("fk_tasks_recurrence_parent_id_tasks", "tasks", type_="foreignkey")
    op.drop_column("tasks", "recurrence_parent_id")
    op.drop_column("tasks", "repeat_daily")
