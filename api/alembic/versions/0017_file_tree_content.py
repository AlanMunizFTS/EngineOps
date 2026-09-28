"""add file nodes (editable text content) to the file tree; seed SCOPE.md

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-20

Every project always has a SCOPE.md file node at its tree root, rendered
where the README card used to be (see docs/architecture/adr/0008). Adds a
third `file` node type alongside folder/link, and a `content` text column.
`created_by` becomes nullable - the SCOPE.md backfill below has no real
actor to attribute it to.

`file_tree_nodes` was only added in 0016 (this same release) with no rows of
real consequence yet, so - consistent with 0009/0013/0014's precedent for
pre-production schema changes - this drops and recreates the table/enum
rather than an in-place ALTER TYPE ... ADD VALUE (which Postgres refuses to
let you use in the same transaction it was added in).

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCOPE_MD_NAME = "SCOPE.md"
_DEFAULT_SCOPE_MD_CONTENT = "# Scope\n\nNo scope defined yet."


def upgrade() -> None:
    op.drop_table("file_tree_nodes")
    sa.Enum(name="file_tree_node_type").drop(op.get_bind(), checkfirst=True)

    # Explicit create, not op.create_table's inline-ENUM auto-create - see
    # 0016's identical note; `parent_id` self-referencing this same table
    # inline suppresses SQLAlchemy's usual auto-create-before-create-table
    # hook.
    postgresql.ENUM("folder", "link", "file", name="file_tree_node_type").create(
        op.get_bind(), checkfirst=True
    )

    op.create_table(
        "file_tree_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("file_tree_nodes.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "node_type",
            postgresql.ENUM(
                "folder", "link", "file", name="file_tree_node_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_file_tree_nodes_project_id", "file_tree_nodes", ["project_id"])
    op.create_index("ix_file_tree_nodes_parent_id", "file_tree_nodes", ["parent_id"])

    conn = op.get_bind()
    projects_table = sa.table("projects", sa.column("id", postgresql.UUID(as_uuid=True)))
    nodes_table = sa.table(
        "file_tree_nodes",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("project_id", postgresql.UUID(as_uuid=True)),
        sa.column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.column(
            "node_type", postgresql.ENUM("folder", "link", "file", name="file_tree_node_type")
        ),
        sa.column("name", sa.String),
        sa.column("content", sa.Text),
        sa.column("created_by", postgresql.UUID(as_uuid=True)),
    )

    project_ids = [row.id for row in conn.execute(sa.select(projects_table.c.id))]
    if project_ids:
        conn.execute(
            nodes_table.insert(),
            [
                {
                    "id": uuid.uuid4(),
                    "project_id": project_id,
                    "parent_id": None,
                    "node_type": "file",
                    "name": _SCOPE_MD_NAME,
                    "content": _DEFAULT_SCOPE_MD_CONTENT,
                    "created_by": None,
                }
                for project_id in project_ids
            ],
        )


def downgrade() -> None:
    op.drop_table("file_tree_nodes")
    sa.Enum(name="file_tree_node_type").drop(op.get_bind(), checkfirst=True)

    postgresql.ENUM("folder", "link", name="file_tree_node_type").create(
        op.get_bind(), checkfirst=True
    )

    op.create_table(
        "file_tree_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("file_tree_nodes.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "node_type",
            postgresql.ENUM("folder", "link", name="file_tree_node_type", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_file_tree_nodes_project_id", "file_tree_nodes", ["project_id"])
    op.create_index("ix_file_tree_nodes_parent_id", "file_tree_nodes", ["parent_id"])
