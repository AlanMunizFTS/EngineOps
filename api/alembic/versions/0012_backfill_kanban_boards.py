"""backfill kanban boards for projects created before kanban_boards existed

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-19

Projects created before 0011 predate kanban_boards/kanban_columns - the
create_project flow now seeds a board automatically going forward, but
existing rows need a one-time backfill so every project ends up with exactly
one board and its 5 fixed columns.

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_COLUMNS: list[tuple[str, str]] = [
    ("Backlog", "backlog"),
    ("To Do", "todo"),
    ("In Progress", "in_progress"),
    ("In Review", "in_review"),
    ("Done", "done"),
]


def upgrade() -> None:
    conn = op.get_bind()

    projects_table = sa.table("projects", sa.column("id", postgresql.UUID(as_uuid=True)))
    boards_table = sa.table(
        "kanban_boards",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("project_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
    )
    columns_table = sa.table(
        "kanban_columns",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("board_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("order_index", sa.Integer),
        sa.column(
            "maps_to_status",
            postgresql.ENUM(
                *[s for _, s in _DEFAULT_COLUMNS], name="issue_status", create_type=False
            ),
        ),
    )

    boarded_project_ids = {
        row.project_id for row in conn.execute(sa.select(boards_table.c.project_id))
    }
    project_ids = [row.id for row in conn.execute(sa.select(projects_table.c.id))]
    unboarded_project_ids = [pid for pid in project_ids if pid not in boarded_project_ids]

    for project_id in unboarded_project_ids:
        board_id = uuid.uuid4()
        conn.execute(
            boards_table.insert().values(id=board_id, project_id=project_id, name="Board")
        )
        conn.execute(
            columns_table.insert(),
            [
                {
                    "id": uuid.uuid4(),
                    "board_id": board_id,
                    "name": name,
                    "order_index": order_index,
                    "maps_to_status": status,
                }
                for order_index, (name, status) in enumerate(_DEFAULT_COLUMNS)
            ],
        )


def downgrade() -> None:
    # Backfilled boards are indistinguishable from ones created through the
    # normal flow - nothing to reverse; 0011's downgrade drops the tables
    # entirely along with everything seeded here.
    pass
