from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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
    created_by: UUID
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
    actor_id: UUID
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


class IssueStatus(StrEnum):
    """Also the fixed vocabulary for kanban_columns.maps_to_status - see
    docs/architecture/adr/0004-issue-hierarchy-linking.md."""

    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class IssuePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class IssueType(StrEnum):
    BUG = "bug"
    TASK = "task"
    IMPROVEMENT = "improvement"
    INCIDENT = "incident"


class MilestoneStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


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
    due_date: date | None
    status: MilestoneStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Issue:
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: IssueStatus
    priority: IssuePriority
    issue_type: IssueType
    milestone_id: UUID | None
    assignee_id: UUID | None
    created_by: UUID
    created_at: datetime
    closed_at: datetime | None
    labels: list[Label] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class IssueComment:
    id: UUID
    issue_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
    edited_at: datetime | None


@dataclass(frozen=True, slots=True)
class KanbanColumn:
    id: UUID
    board_id: UUID
    name: str
    order_index: int
    maps_to_status: IssueStatus


@dataclass(frozen=True, slots=True)
class KanbanBoard:
    """One board per project, seeded automatically on project creation with 5
    fixed columns mirroring `IssueStatus` - customizable columns are a later
    polish item (see docs/architecture/adr/0004-issue-hierarchy-linking.md)."""

    id: UUID
    project_id: UUID
    name: str
    columns: list[KanbanColumn] = field(default_factory=list)
