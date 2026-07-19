"""add nullable phase_status_id to plants, machines, implementations

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-19

See docs/architecture/adr/0003-phase-inheritance.md. NULL means "inherit the
parent's effective phase" (the default for every existing row - purely
additive, no backfill needed); non-NULL is an explicit override/deviation.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ["plants", "machines", "implementations"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "phase_status_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("area_statuses.id"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "phase_status_id")
