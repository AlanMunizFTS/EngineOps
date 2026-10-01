"""rebuild project tracking around milestones, tasks, and subtasks

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-30

This is an intentionally destructive reset of project data.  Authentication
is the only state carried across the reset: ``users``, ``roles``, and
``user_roles`` are neither deleted from nor recreated.  Project-owned rows
may reference users, but those rows are disposable and are removed by
deleting their owning projects before the old issue schema is replaced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_VALUES = ["backlog", "todo", "in_progress", "in_review", "done"]
_PRIORITY_VALUES = ["low", "medium", "high", "urgent"]
_TYPE_VALUES = ["task", "bug", "improvement", "incident"]
_MILESTONE_STATUS_VALUES = ["open", "closed"]


def _enum(name: str, values: list[str]) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def _reset_project_data() -> None:
    """Clear the disposable project graph without touching authentication."""
    op.execute("DELETE FROM projects")


def upgrade() -> None:
    # projects cascades into project_members, audit_log, labels, issues,
    # kanban, file-tree and material/piece data.  References point *to* users;
    # no auth row is part of this cascade.
    _reset_project_data()

    op.drop_table("issue_comments")
    op.drop_table("issue_labels")
    op.drop_table("issues")

    # PostgreSQL will not drop issue_status while an ARRAY column uses it.
    op.drop_column("kanban_columns", "maps_to_statuses")
    sa.Enum(name="issue_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="issue_priority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="issue_status").drop(op.get_bind(), checkfirst=True)

    for name, values in (
        ("task_status", _STATUS_VALUES),
        ("task_priority", _PRIORITY_VALUES),
        ("task_type", _TYPE_VALUES),
        ("milestone_status", _MILESTONE_STATUS_VALUES),
    ):
        postgresql.ENUM(*values, name=name).create(op.get_bind(), checkfirst=True)

    task_status = _enum("task_status", _STATUS_VALUES)
    task_priority = _enum("task_priority", _PRIORITY_VALUES)
    task_type = _enum("task_type", _TYPE_VALUES)
    milestone_status = _enum("milestone_status", _MILESTONE_STATUS_VALUES)

    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", milestone_status, nullable=False, server_default="open"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("milestones.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, nullable=False, server_default="backlog"),
        sa.Column("priority", task_priority, nullable=False, server_default="medium"),
        sa.Column("task_type", task_type, nullable=False, server_default="task"),
        sa.Column(
            "assignee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "parent_task_id IS NULL OR milestone_id IS NULL",
            name="ck_subtask_no_milestone",
        ),
        sa.CheckConstraint(
            "parent_task_id IS NULL OR parent_task_id <> id",
            name="ck_task_not_self_parent",
        ),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_milestone_id", "tasks", ["milestone_id"])
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"])

    op.create_table(
        "task_labels",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "label_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("labels.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])

    op.add_column(
        "kanban_columns",
        sa.Column("maps_to_statuses", postgresql.ARRAY(task_status), nullable=False),
    )


def downgrade() -> None:
    # New project/task data is deliberately not translated back into issues.
    # Clearing projects also makes the non-null Kanban enum swap deterministic.
    _reset_project_data()

    op.drop_column("kanban_columns", "maps_to_statuses")
    op.drop_table("task_comments")
    op.drop_table("task_labels")
    op.drop_table("tasks")
    op.drop_table("milestones")

    for name in ("milestone_status", "task_type", "task_priority", "task_status"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)

    for name, values in (
        ("issue_status", _STATUS_VALUES),
        ("issue_priority", _PRIORITY_VALUES),
        ("issue_type", ["bug", "task", "improvement", "incident"]),
    ):
        postgresql.ENUM(*values, name=name).create(op.get_bind(), checkfirst=True)

    issue_status = _enum("issue_status", _STATUS_VALUES)
    issue_priority = _enum("issue_priority", _PRIORITY_VALUES)
    issue_type = _enum("issue_type", ["bug", "task", "improvement", "incident"])

    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", issue_status, nullable=False, server_default="backlog"),
        sa.Column("priority", issue_priority, nullable=False, server_default="medium"),
        sa.Column("issue_type", issue_type, nullable=False, server_default="task"),
        sa.Column(
            "assignee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_issue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_issues_project_id", "issues", ["project_id"])
    op.create_index("ix_issues_parent_issue_id", "issues", ["parent_issue_id"])

    op.create_table(
        "issue_labels",
        sa.Column(
            "issue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "label_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("labels.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "issue_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "issue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_issue_comments_issue_id", "issue_comments", ["issue_id"])

    op.add_column(
        "kanban_columns",
        sa.Column("maps_to_statuses", postgresql.ARRAY(issue_status), nullable=False),
    )
