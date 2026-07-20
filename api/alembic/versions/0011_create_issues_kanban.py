"""create labels, milestones, issues, issue_labels, issue_comments, kanban_boards/columns

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-19

See docs/architecture/adr/0004-issue-hierarchy-linking.md: `issues` links to at
most one of plant_id/machine_id/implementation_id (CHECK constraint), and
`kanban_columns` seeds 5 fixed columns per project rather than being
customizable in this phase.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ISSUE_STATUS_VALUES = ["backlog", "todo", "in_progress", "in_review", "done"]


def upgrade() -> None:
    op.create_table(
        "labels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_labels_project_id_name"),
    )
    op.create_index("ix_labels_project_id", "labels", ["project_id"])

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
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("open", "closed", name="milestone_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])

    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "machine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("machines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "implementation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("implementations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(*_ISSUE_STATUS_VALUES, name="issue_status"),
            nullable=False,
            server_default="backlog",
        ),
        sa.Column(
            "priority",
            postgresql.ENUM("low", "medium", "high", "urgent", name="issue_priority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "issue_type",
            postgresql.ENUM("bug", "task", "improvement", "incident", name="issue_type"),
            nullable=False,
            server_default="task",
        ),
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("milestones.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assignee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(plant_id IS NOT NULL)::int + (machine_id IS NOT NULL)::int "
            "+ (implementation_id IS NOT NULL)::int <= 1",
            name="ck_issues_single_hierarchy_link",
        ),
    )
    op.create_index("ix_issues_project_id", "issues", ["project_id"])

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
            sa.ForeignKey("users.id"),
            nullable=False,
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

    op.create_table(
        "kanban_boards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "kanban_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "board_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kanban_boards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "maps_to_status",
            postgresql.ENUM(*_ISSUE_STATUS_VALUES, name="issue_status", create_type=False),
            nullable=False,
        ),
    )
    op.create_index("ix_kanban_columns_board_id", "kanban_columns", ["board_id"])


def downgrade() -> None:
    op.drop_table("kanban_columns")
    op.drop_table("kanban_boards")
    op.drop_table("issue_comments")
    op.drop_table("issue_labels")
    op.drop_table("issues")
    op.drop_table("milestones")
    op.drop_table("labels")

    sa.Enum(name="issue_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="issue_priority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="issue_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="milestone_status").drop(op.get_bind(), checkfirst=True)
