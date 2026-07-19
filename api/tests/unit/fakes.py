"""In-memory fakes for the Phase 1 repository ports, used by unit tests to exercise
routers without a real Postgres connection (mirrors the FakeUserRepository pattern
already used in test_auth.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ops_platform.domain.entities import (
    ActivityEntry,
    AreaStatus,
    AreaType,
    AuditLogEntry,
    Project,
    ProjectArea,
    ProjectMember,
    ProjectMemberDetail,
    ProjectRole,
    User,
)
from ops_platform.domain.ports.area_repository import AreaRepository
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.domain.ports.user_repository import UserRepository


class FakeSession:
    """Stands in for AsyncSession - routers only ever call `.commit()` on it directly."""

    async def commit(self) -> None:
        return None


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    async def create(self, email: str, hashed_password: str, full_name: str) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        self._users[email] = user
        return user


class FakeProjectRepository(ProjectRepository):
    """Takes the user repository fake to resolve email/full_name for
    list_members_with_users, mirroring the SQL adapter's join against users."""

    def __init__(self, user_repository: FakeUserRepository) -> None:
        self._user_repository = user_repository
        self._projects: dict[UUID, Project] = {}
        self._members: dict[UUID, list[ProjectMember]] = {}

    async def create(self, name: str, description: str | None, created_by: UUID) -> Project:
        project = Project(
            id=uuid.uuid4(),
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._projects[project.id] = project
        self._members[project.id] = []
        return project

    async def get(self, project_id: UUID) -> Project | None:
        return self._projects.get(project_id)

    async def list_all(self) -> list[Project]:
        return list(self._projects.values())

    async def add_member(
        self, project_id: UUID, user_id: UUID, project_role: ProjectRole
    ) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            project_role=project_role,
            added_at=datetime.now(UTC),
        )
        self._members.setdefault(project_id, []).append(member)
        return member

    async def list_members(self, project_id: UUID) -> list[ProjectMember]:
        return self._members.get(project_id, [])

    async def list_members_with_users(self, project_id: UUID) -> list[ProjectMemberDetail]:
        details = []
        for member in self._members.get(project_id, []):
            user = next(
                (u for u in self._user_repository._users.values() if u.id == member.user_id),
                None,
            )
            details.append(
                ProjectMemberDetail(
                    member=member,
                    email=user.email if user else "",
                    full_name=user.full_name if user else "",
                )
            )
        return details


class FakeAreaRepository(AreaRepository):
    """Seeds a single "Scope & Charter" area type with two statuses - enough to
    exercise default-area creation and a status transition without the full catalog."""

    def __init__(self) -> None:
        self._area_type = AreaType(
            id=uuid.uuid4(), name="Scope & Charter", description="Defining scope"
        )
        self._statuses = [
            AreaStatus(
                id=uuid.uuid4(), area_type_id=self._area_type.id, name="Requested", sort_order=0
            ),
            AreaStatus(
                id=uuid.uuid4(), area_type_id=self._area_type.id, name="Analyzing", sort_order=1
            ),
        ]
        self._project_areas: dict[UUID, list[ProjectArea]] = {}

    async def list_area_types(self) -> list[AreaType]:
        return [self._area_type]

    async def list_statuses_for_type(self, area_type_id: UUID) -> list[AreaStatus]:
        return [status for status in self._statuses if status.area_type_id == area_type_id]

    async def create_default_areas(self, project_id: UUID) -> list[ProjectArea]:
        area = ProjectArea(
            id=uuid.uuid4(),
            project_id=project_id,
            area_type=self._area_type,
            status=self._statuses[0],
            updated_by=None,
            updated_at=datetime.now(UTC),
        )
        self._project_areas[project_id] = [area]
        return [area]

    async def list_for_project(self, project_id: UUID) -> list[ProjectArea]:
        return self._project_areas.get(project_id, [])

    async def update_status(
        self, project_area_id: UUID, status_id: UUID, updated_by: UUID
    ) -> ProjectArea:
        for areas in self._project_areas.values():
            for index, area in enumerate(areas):
                if area.id == project_area_id:
                    new_status = next(s for s in self._statuses if s.id == status_id)
                    updated = ProjectArea(
                        id=area.id,
                        project_id=area.project_id,
                        area_type=area.area_type,
                        status=new_status,
                        updated_by=updated_by,
                        updated_at=datetime.now(UTC),
                    )
                    areas[index] = updated
                    return updated
        raise ValueError(f"project_area {project_area_id} not found")


class FakeAuditLog(AuditRecorder, AuditLogRepository):
    """Implements both the write-side hook and the read-side repository, so tests can
    record via the router and immediately assert on what landed. Takes the project
    repository fake to resolve project names for the cross-project activity feed,
    mirroring the SQL adapter's join against `projects`."""

    def __init__(self, project_repository: FakeProjectRepository) -> None:
        self.entries: list[AuditLogEntry] = []
        self._project_repository = project_repository

    async def record(
        self,
        *,
        project_id: UUID,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        diff: dict[str, Any],
    ) -> None:
        self.entries.append(
            AuditLogEntry(
                id=uuid.uuid4(),
                project_id=project_id,
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                diff=diff,
                occurred_at=datetime.now(UTC),
            )
        )

    async def list_for_project(self, project_id: UUID) -> list[AuditLogEntry]:
        return [entry for entry in self.entries if entry.project_id == project_id]

    async def list_recent(self, limit: int) -> list[ActivityEntry]:
        ordered = sorted(self.entries, key=lambda entry: entry.occurred_at, reverse=True)
        result = []
        for entry in ordered[:limit]:
            project = self._project_repository._projects.get(entry.project_id)
            result.append(ActivityEntry(entry=entry, project_name=project.name if project else ""))
        return result
