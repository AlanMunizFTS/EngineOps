from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Machine


class MachineRepository(ABC):
    """Port for machine persistence. A machine may exist before, during, or as an
    output of the project that owns it - creation has no precondition beyond the
    project existing."""

    @abstractmethod
    async def create(
        self, project_id: UUID, name: str, machine_type: str | None, location: str | None
    ) -> Machine: ...

    @abstractmethod
    async def get(self, machine_id: UUID) -> Machine | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[Machine]: ...
