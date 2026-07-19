from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Machine


class MachineRepository(ABC):
    """Port for machine persistence. A machine belongs to a plant (not directly to
    a project - see Plant) and may exist before, during, or as an output of the
    project that owns it - creation has no precondition beyond the plant existing."""

    @abstractmethod
    async def create(
        self, plant_id: UUID, name: str, machine_type: str | None, location: str | None
    ) -> Machine: ...

    @abstractmethod
    async def get(self, machine_id: UUID) -> Machine | None: ...

    @abstractmethod
    async def list_for_plant(self, plant_id: UUID) -> list[Machine]: ...

    @abstractmethod
    async def update_phase(self, machine_id: UUID, status_id: UUID | None) -> Machine:
        """Set (or clear) this machine's phase override - see
        docs/architecture/adr/0003-phase-inheritance.md."""
        ...
