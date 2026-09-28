"""add stage/start_date/due_date/days_planned to issues (project Schedule view)

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-23

Adds the scheduling fields the Gantt-style Schedule tab needs, per
docs/architecture/adr/0009-project-schedule-priority-score.md. All four
columns are nullable - an issue with no start_date/due_date simply doesn't
appear on the Gantt grid. Urgency, Priority Score, days-taken, and schedule
status are computed at request time (see domain/scheduling.py), not stored.

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("issues", sa.Column("stage", sa.String(length=100), nullable=True))
    op.add_column("issues", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("issues", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("issues", sa.Column("days_planned", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("issues", "days_planned")
    op.drop_column("issues", "due_date")
    op.drop_column("issues", "start_date")
    op.drop_column("issues", "stage")
