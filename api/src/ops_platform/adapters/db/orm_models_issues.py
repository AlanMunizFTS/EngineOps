"""ORM models for the issue-tracking bounded context: labels, issues, issue
comments, and kanban boards/columns - split out from orm_models.py to keep
that module under the ~400-line limit (CLAUDE.md §3). Shares the same
`Base`/registry, so Alembic sees one combined metadata."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ops_platform.adapters.db.orm_models import Base, enum_values
from ops_platform.domain.entities import IssuePriority, IssueStatus, IssueType


class LabelORM(Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_labels_project_id_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)


class IssueORM(Base):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status", values_callable=enum_values),
        nullable=False,
        default=IssueStatus.BACKLOG,
    )
    priority: Mapped[IssuePriority] = mapped_column(
        Enum(IssuePriority, name="issue_priority", values_callable=enum_values),
        nullable=False,
        default=IssuePriority.MEDIUM,
    )
    issue_type: Mapped[IssueType] = mapped_column(
        Enum(IssueType, name="issue_type", values_callable=enum_values),
        nullable=False,
        default=IssueType.TASK,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
    )
    parent_assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date(), nullable=True)

    labels: Mapped[list[LabelORM]] = relationship(secondary="issue_labels", lazy="selectin")


class IssueLabelORM(Base):
    """3NF join table: an issue can carry multiple labels, a label applies to many issues."""

    __tablename__ = "issue_labels"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True
    )


class IssueCommentORM(Base):
    __tablename__ = "issue_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KanbanBoardORM(Base):
    """A project can have any number of boards - see
    docs/architecture/adr/0010-dynamic-kanban-boards.md."""

    __tablename__ = "kanban_boards"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    columns: Mapped[list["KanbanColumnORM"]] = relationship(
        order_by="KanbanColumnORM.order_index", lazy="selectin", cascade="all, delete-orphan"
    )


class KanbanColumnORM(Base):
    __tablename__ = "kanban_columns"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    board_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kanban_boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    maps_to_statuses: Mapped[list[IssueStatus]] = mapped_column(
        ARRAY(
            Enum(IssueStatus, name="issue_status", values_callable=enum_values, create_type=False)
        ),
        nullable=False,
        default=list,
    )
