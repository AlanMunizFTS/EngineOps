from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Plant


class PlantRepository(ABC):
    """Port for plant persistence. A plant is a physical site a project's standard
    is deployed to - it always belongs to exactly one project."""

    @abstractmethod
    async def create(self, project_id: UUID, name: str, location: str | None) -> Plant: ...

    @abstractmethod
    async def get(self, plant_id: UUID) -> Plant | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[Plant]: ...

    @abstractmethod
    async def update_phase(self, plant_id: UUID, status_id: UUID | None) -> Plant:
        """Set (or, if status_id is None, clear) this plant's phase override -
        see docs/architecture/adr/0003-phase-inheritance.md."""
        ...
