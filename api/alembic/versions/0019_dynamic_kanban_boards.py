"""dynamic kanban: multiple boards per project, multi-status columns

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-23

Per docs/architecture/adr/0010-dynamic-kanban-boards.md: a project can now
have any number of boards (drops the one-board-per-project unique
constraint), and each column maps to zero or more `IssueStatus` values
instead of exactly one - `maps_to_status` becomes `maps_to_statuses` (array).
Card membership stays entirely status-driven; there's no separate placement
table, so this is additive - existing single-status columns become
single-element arrays.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ISSUE_STATUS_VALUES = ["backlog", "todo", "in_progress", "in_review", "done"]


def upgrade() -> None:
    op.drop_constraint("kanban_boards_project_id_key", "kanban_boards", type_="unique")
    op.create_index("ix_kanban_boards_project_id", "kanban_boards", ["project_id"])

    status_enum = postgresql.ENUM(*_ISSUE_STATUS_VALUES, name="issue_status", create_type=False)
    op.add_column(
        "kanban_columns",
        sa.Column("maps_to_statuses", postgresql.ARRAY(status_enum), nullable=True),
    )
    op.execute(
        "UPDATE kanban_columns SET maps_to_statuses = ARRAY[maps_to_status]::issue_status[]"
    )
    op.alter_column("kanban_columns", "maps_to_statuses", nullable=False)
    op.drop_column("kanban_columns", "maps_to_status")


def downgrade() -> None:
    status_enum = postgresql.ENUM(*_ISSUE_STATUS_VALUES, name="issue_status", create_type=False)
    op.add_column(
        "kanban_columns",
        sa.Column("maps_to_status", status_enum, nullable=True),
    )
    op.execute("UPDATE kanban_columns SET maps_to_status = maps_to_statuses[1]")
    op.alter_column("kanban_columns", "maps_to_status", nullable=False)
    op.drop_column("kanban_columns", "maps_to_statuses")

    op.drop_index("ix_kanban_boards_project_id", "kanban_boards")
    op.create_unique_constraint("kanban_boards_project_id_key", "kanban_boards", ["project_id"])
