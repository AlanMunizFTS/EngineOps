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
    Implementation,
    ImplementationStatus,
    Machine,
    Project,
    ProjectArea,
    ProjectMember,
    ProjectRole,
)
from ops_platform.domain.ports.area_repository import AreaRepository
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.implementation_repository import ImplementationRepository
from ops_platform.domain.ports.machine_repository import MachineRepository
from ops_platform.domain.ports.project_repository import ProjectRepository


class FakeSession:
    """Stands in for AsyncSession - routers only ever call `.commit()` on it directly."""

    async def commit(self) -> None:
        return None


class FakeProjectRepository(ProjectRepository):
    def __init__(self) -> None:
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


class FakeMachineRepository(MachineRepository):
    def __init__(self) -> None:
        self._machines: dict[UUID, Machine] = {}

    async def create(
        self, project_id: UUID, name: str, machine_type: str | None, location: str | None
    ) -> Machine:
        machine = Machine(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            machine_type=machine_type,
            location=location,
            created_at=datetime.now(UTC),
        )
        self._machines[machine.id] = machine
        return machine

    async def get(self, machine_id: UUID) -> Machine | None:
        return self._machines.get(machine_id)

    async def list_for_project(self, project_id: UUID) -> list[Machine]:
        return [m for m in self._machines.values() if m.project_id == project_id]


class FakeImplementationRepository(ImplementationRepository):
    def __init__(self) -> None:
        self._implementations: dict[UUID, Implementation] = {}

    async def create(
        self, machine_id: UUID, label: str, status: ImplementationStatus
    ) -> Implementation:
        implementation = Implementation(
            id=uuid.uuid4(),
            machine_id=machine_id,
            label=label,
            status=status,
            superseded_by=None,
            created_at=datetime.now(UTC),
        )
        self._implementations[implementation.id] = implementation
        return implementation

    async def get(self, implementation_id: UUID) -> Implementation | None:
        return self._implementations.get(implementation_id)

    async def list_for_machine(self, machine_id: UUID) -> list[Implementation]:
        return [i for i in self._implementations.values() if i.machine_id == machine_id]

    async def supersede(self, implementation_id: UUID, superseded_by: UUID) -> Implementation:
        implementation = self._implementations[implementation_id]
        updated = Implementation(
            id=implementation.id,
            machine_id=implementation.machine_id,
            label=implementation.label,
            status=ImplementationStatus.SUPERSEDED,
            superseded_by=superseded_by,
            created_at=implementation.created_at,
        )
        self._implementations[implementation_id] = updated
        return updated


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
