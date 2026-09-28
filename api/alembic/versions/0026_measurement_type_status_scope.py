"""add status scope to measurement_types

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-28

`measurement_types.status` is a third, independent scoping dimension
alongside `condition_id`/`part_number_id` - null means "any status", "ok"/
"nok" restricts the measurement to only that overall_status. Lets a
measurement type be configured for combinations like "this part number,
regardless of status" vs. "this part number, only when NOK" vs. "any part
number, only when OK", etc.

Purely additive: a new nullable column on an existing table, no data touched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "measurement_types",
        sa.Column(
            "status",
            postgresql.ENUM("ok", "nok", name="piece_status", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("measurement_types", "status")
