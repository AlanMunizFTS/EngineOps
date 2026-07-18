"""create implementations

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "implementations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "machine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("machines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned", "active", "superseded", "decommissioned", name="implementation_status"
            ),
            nullable=False,
            server_default="planned",
        ),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("implementations.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_implementations_machine_id", "implementations", ["machine_id"])


def downgrade() -> None:
    op.drop_table("implementations")
    sa.Enum(name="implementation_status").drop(op.get_bind(), checkfirst=True)
