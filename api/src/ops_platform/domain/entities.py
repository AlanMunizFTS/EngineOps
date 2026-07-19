from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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


class ImplementationStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DECOMMISSIONED = "decommissioned"


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
class AreaType:
    id: UUID
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class AreaStatus:
    id: UUID
    area_type_id: UUID
    name: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class ProjectArea:
    """A project's independent progress track for one area (Procurement, Electrical, ...).

    Each project has one row per seeded AreaType, each with its own status - there is
    deliberately no single project-wide `status` field, since areas progress
    non-linearly and in parallel (see docs/architecture/adr/0001).
    """

    id: UUID
    project_id: UUID
    area_type: AreaType
    status: AreaStatus
    updated_by: UUID | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Machine:
    id: UUID
    project_id: UUID
    name: str
    machine_type: str | None
    location: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Implementation:
    id: UUID
    machine_id: UUID
    label: str
    status: ImplementationStatus
    superseded_by: UUID | None
    created_at: datetime


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
