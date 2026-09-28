"""create file_tree_nodes

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-20

A project's file tree - folders and links only, no real file storage (see
docs/architecture/adr/0007-project-file-tree.md). `parent_id` self-references
the table with ON DELETE CASCADE so deleting a folder deletes its subtree.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Created explicitly rather than relying on op.create_table's inline-ENUM
    # auto-create - that auto-create hooks into SQLAlchemy's Table-level
    # `before_create` event, which doesn't reliably fire here because
    # `parent_id` self-references this same table inline (unlike every other
    # enum-bearing table in this schema). A fresh `alembic upgrade head` on an
    # empty database reproducibly fails with `type file_tree_node_type does
    # not exist` without this explicit create.
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


def downgrade() -> None:
    op.drop_table("file_tree_nodes")
    sa.Enum(name="file_tree_node_type").drop(op.get_bind(), checkfirst=True)
