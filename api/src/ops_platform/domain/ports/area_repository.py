from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import AreaStatus, AreaType, ProjectArea


class AreaRepository(ABC):
    """Port for the area catalog (area_types/area_statuses) and per-project area tracks."""

    @abstractmethod
    async def list_area_types(self) -> list[AreaType]: ...

    @abstractmethod
    async def list_statuses_for_type(self, area_type_id: UUID) -> list[AreaStatus]: ...

    @abstractmethod
    async def create_default_areas(self, project_id: UUID) -> list[ProjectArea]:
        """Attach one ProjectArea per seeded AreaType, each set to its default status."""
        ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[ProjectArea]: ...

    @abstractmethod
    async def update_status(
        self, project_area_id: UUID, status_id: UUID, updated_by: UUID
    ) -> ProjectArea: ...
