"""issues.parent_assigned_at

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-23

Per docs/architecture/adr/0014-parent-assigned-at.md: stamps when
`parent_issue_id` last changed (set, cleared, or re-pointed), separate from
`created_at`. The Schedule view sorts a parent's children by this instead
of their own `created_at`, so un-linking a child and re-linking it later
moves it to the end of its new siblings rather than pinning it to whenever
it was originally created.

A plain nullable ADD COLUMN - existing rows get NULL, which the frontend
falls back to `created_at` for, so no backfill is needed.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "issues", sa.Column("parent_assigned_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("issues", "parent_assigned_at")
