from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import ActivityEntry, AuditLogEntry


class AuditLogRepository(ABC):
    """Read side of the audit_log - the project timeline is just this, filtered by
    project_id and ordered by occurred_at (kickoff spec §4: don't build a second
    feed table, that's a second source of truth)."""

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[AuditLogEntry]: ...

    @abstractmethod
    async def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[AuditLogEntry]:
        """A single entity's full change history (e.g. one task's status
        transitions) - same underlying table as `list_for_project`, filtered
        narrower. Ordered oldest first."""
        ...

    @abstractmethod
    async def list_recent(self, limit: int) -> list[ActivityEntry]:
        """Most recent entries across all projects, newest first - the home
        dashboard feed."""
        ...
