from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Implementation, ImplementationStatus


class ImplementationRepository(ABC):
    """Port for implementation persistence. `project_id` is intentionally not stored
    here (kept 3NF per CLAUDE.md §5) - it's always derived via `machine.project_id`."""

    @abstractmethod
    async def create(
        self, machine_id: UUID, label: str, status: ImplementationStatus
    ) -> Implementation: ...

    @abstractmethod
    async def get(self, implementation_id: UUID) -> Implementation | None: ...

    @abstractmethod
    async def list_for_machine(self, machine_id: UUID) -> list[Implementation]: ...

    @abstractmethod
    async def supersede(self, implementation_id: UUID, superseded_by: UUID) -> Implementation:
        """Marks `implementation_id` as superseded by `superseded_by`."""
        ...

    @abstractmethod
    async def update_phase(
        self, implementation_id: UUID, status_id: UUID | None
    ) -> Implementation:
        """Set (or clear) this implementation's phase override - see
        docs/architecture/adr/0003-phase-inheritance.md."""
        ...
