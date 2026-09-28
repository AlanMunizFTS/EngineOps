"""issue subtasks (parent_issue_id); drop stage and days_planned

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-23

Per docs/architecture/adr/0011-issue-subtasks-and-history.md:
- `stage` (free-text Kanban-grouping field) is dropped, superseded by
  dynamic Kanban columns (ADR 0010).
- `days_planned` is dropped as a stored column - it's now computed from
  `start_date`/`due_date` at read time (domain/scheduling.py), so it can
  never drift out of sync with them.
- `parent_issue_id` (nullable, self-referential, ON DELETE SET NULL) lets
  an issue be a subtask of another issue in the same project.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("issues", "stage")
    op.drop_column("issues", "days_planned")
    op.add_column(
        "issues",
        sa.Column(
            "parent_issue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_issues_parent_issue_id", "issues", ["parent_issue_id"])


def downgrade() -> None:
    op.drop_index("ix_issues_parent_issue_id", "issues")
    op.drop_column("issues", "parent_issue_id")
    op.add_column("issues", sa.Column("days_planned", sa.Integer(), nullable=True))
    op.add_column("issues", sa.Column("stage", sa.String(length=100), nullable=True))
