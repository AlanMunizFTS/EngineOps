"""create audit_log

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-18

Append-only. project_id is denormalized on every row for fast per-project timeline
queries (kickoff spec §4) - the one denormalization in this phase that's pre-justified
by the spec itself rather than needing its own ADR.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("diff_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_audit_log_project_id_occurred_at", "audit_log", ["project_id", "occurred_at"]
    )


def downgrade() -> None:
    op.drop_table("audit_log")
