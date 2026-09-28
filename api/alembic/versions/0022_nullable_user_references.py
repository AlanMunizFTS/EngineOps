"""nullable user references: projects.created_by, issues.created_by,
issue_comments.author_id, audit_log.actor_id

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-23

Per docs/architecture/adr/0015-admin-panel-and-deletable-users.md: deleting a
user must not be blocked by everything they ever created/authored/acted on.
`file_tree_nodes.created_by` and `issues.assignee_id` already use
`ON DELETE SET NULL` for exactly this reason - this migration extends the
same pattern to the four columns that were still `NO ACTION` (blocking).
"""

from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHANGES = [
    ("projects", "created_by", "projects_created_by_fkey"),
    ("issues", "created_by", "issues_created_by_fkey"),
    ("issue_comments", "author_id", "issue_comments_author_id_fkey"),
    ("audit_log", "actor_id", "audit_log_actor_id_fkey"),
]


def upgrade() -> None:
    for table, column, constraint_name in _CHANGES:
        op.alter_column(
            table, column, existing_type=PG_UUID(as_uuid=True), nullable=True
        )
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name, table, "users", [column], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    for table, column, constraint_name in _CHANGES:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(constraint_name, table, "users", [column], ["id"])
        op.alter_column(
            table, column, existing_type=PG_UUID(as_uuid=True), nullable=False
        )
