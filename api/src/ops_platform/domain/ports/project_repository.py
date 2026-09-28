from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Project, ProjectMember, ProjectMemberDetail, ProjectRole


class ProjectRepository(ABC):
    """Port for project + project_members persistence."""

    @abstractmethod
    async def create(self, name: str, description: str | None, created_by: UUID) -> Project: ...

    @abstractmethod
    async def get(self, project_id: UUID) -> Project | None: ...

    @abstractmethod
    async def list_all(self) -> list[Project]: ...

    @abstractmethod
    async def add_member(
        self, project_id: UUID, user_id: UUID, project_role: ProjectRole
    ) -> ProjectMember: ...

    @abstractmethod
    async def list_members(self, project_id: UUID) -> list[ProjectMember]: ...

    @abstractmethod
    async def list_members_with_users(self, project_id: UUID) -> list[ProjectMemberDetail]:
        """Same as list_members, joined with each member's email/full_name -
        the Contributors panel needs a human-readable name, not a bare user_id."""
        ...

    @abstractmethod
    async def remove_member(self, project_id: UUID, user_id: UUID) -> None: ...
