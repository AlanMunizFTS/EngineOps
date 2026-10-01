from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Role:
    id: UUID
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    hashed_password: str
    full_name: str
    is_active: bool
    created_at: datetime
    roles: list[Role] = field(default_factory=list)


class ProjectRole(StrEnum):
    """Project-scoped role, distinct from the global roles in `user_roles`."""

    OWNER = "owner"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


@dataclass(frozen=True, slots=True)
class Project:
    id: UUID
    name: str
    description: str | None
    created_by: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectMember:
    project_id: UUID
    user_id: UUID
    project_role: ProjectRole
    added_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectMemberDetail:
    """A ProjectMember plus the user's email/full_name - the read-model behind
    the project detail page's Contributors panel."""

    member: ProjectMember
    email: str
    full_name: str


@dataclass(frozen=True, slots=True)
class AuditLogEntry:
    id: UUID
    project_id: UUID
    actor_id: UUID | None
    entity_type: str
    entity_id: UUID
    action: str
    diff: dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ActivityEntry:
    """An AuditLogEntry plus its project's name - the read-model behind the
    cross-project home dashboard feed (audit_log filtered by a single project_id is
    the per-project timeline; unfiltered and joined with project name is this)."""

    entry: AuditLogEntry
    project_name: str


class FileTreeNodeType(StrEnum):
    FOLDER = "folder"
    LINK = "link"
    FILE = "file"


@dataclass(frozen=True, slots=True)
class FileTreeNode:
    """A folder, a link, or a text file within a project's file tree - a
    lightweight org structure, not a real filesystem. Links always carry a
    `url`; files carry editable text `content`; folders carry neither.
    `created_by` is nullable because SCOPE.md is auto-seeded on project
    creation (and backfilled for pre-existing projects) with no human actor."""

    id: UUID
    project_id: UUID
    parent_id: UUID | None
    node_type: FileTreeNodeType
    name: str
    url: str | None
    content: str | None
    created_by: UUID | None
    created_at: datetime


class TaskStatus(StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(StrEnum):
    BUG = "bug"
    TASK = "task"
    IMPROVEMENT = "improvement"
    INCIDENT = "incident"


@dataclass(frozen=True, slots=True)
class Label:
    id: UUID
    project_id: UUID
    name: str
    color: str


@dataclass(frozen=True, slots=True)
class Milestone:
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: MilestoneStatus
    due_date: date | None
    created_at: datetime
    updated_at: datetime
    total_tasks: int = 0
    completed_tasks: int = 0

    @property
    def progress_percentage(self) -> float:
        return 0.0 if self.total_tasks == 0 else self.completed_tasks / self.total_tasks * 100


class MilestoneStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class Task:
    """Executable work. ``parent_task_id`` is the sole hierarchy discriminator.

    A null parent identifies a top-level Task; a non-null parent identifies a
    direct Subtask. The application service prevents deeper nesting.
    """

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType
    assignee_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    milestone_id: UUID | None = None
    parent_task_id: UUID | None = None
    parent_assigned_at: datetime | None = None
    start_date: date | None = None
    due_date: date | None = None
    labels: list[Label] = field(default_factory=list)
    subtasks_total: int = 0
    subtasks_completed: int = 0

    @property
    def is_subtask(self) -> bool:
        return self.parent_task_id is not None

    @property
    def is_top_level(self) -> bool:
        return self.parent_task_id is None


@dataclass(frozen=True, slots=True)
class TaskComment:
    id: UUID
    task_id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KanbanColumn:
    """`maps_to_statuses` drives card membership - a column shows every task
    whose `status` is in this list. Empty means the column never shows any
    card (allowed, e.g. as a placeholder while setting up a new board). A
    column mapping to more than one status aggregates them into one visual
    lane; dragging a card into it sets the task's status to the first entry
    - see docs/architecture/adr/0010-dynamic-kanban-boards.md."""

    id: UUID
    board_id: UUID
    name: str
    order_index: int
    maps_to_statuses: list[TaskStatus] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KanbanBoard:
    """A project can have any number of boards, each an independent,
    freely-named view with its own columns - see
    docs/architecture/adr/0010-dynamic-kanban-boards.md (supersedes the fixed
    single-board design from ADR 0004). `create_default_board` still seeds one
    board with 5 status-mapped columns automatically on project creation."""

    id: UUID
    project_id: UUID
    name: str
    columns: list[KanbanColumn] = field(default_factory=list)


class PieceStatus(StrEnum):
    OK = "ok"
    NOK = "nok"


@dataclass(frozen=True, slots=True)
class PartNumber:
    id: UUID
    project_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class PieceCondition:
    id: UUID
    project_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class PieceLocation:
    id: UUID
    project_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class MeasurementType:
    """A reusable numeric measurement definition (e.g. "Split Width", mm).
    `condition_id`/`part_number_id`/`status` independently scope which pieces
    it applies to - all null means it applies to every piece regardless of
    status/condition/part number (e.g. external diameter). Any combination is
    valid: e.g. a specific part number regardless of status/condition, a
    condition regardless of part number, or a part number scoped to just OK
    or just NOK pieces."""

    id: UUID
    project_id: UUID
    name: str
    unit: str
    condition_id: UUID | None
    part_number_id: UUID | None
    status: PieceStatus | None


@dataclass(frozen=True, slots=True)
class PieceMeasurement:
    id: UUID
    piece_id: UUID
    measurement_type_id: UUID
    value: Decimal


@dataclass(frozen=True, slots=True)
class Piece:
    """A single inspected piece, stamped with a unique `tracking_number`
    (uppercase hex, zero-padded to 6 chars) at registration so it can be
    followed through the process. Conditions are a general tag set, not
    exclusive to NOK pieces - see docs plan for Material/Piece traceability."""

    id: UUID
    project_id: UUID
    tracking_number: str
    part_number_id: UUID
    overall_status: PieceStatus
    location_id: UUID | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    conditions: list[PieceCondition] = field(default_factory=list)
    measurements: list[PieceMeasurement] = field(default_factory=list)
