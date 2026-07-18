from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import AuditLogEntry


class AuditLogRepository(ABC):
    """Read side of the audit_log - the project timeline is just this, filtered by
    project_id and ordered by occurred_at (kickoff spec §4: don't build a second
    feed table, that's a second source of truth)."""

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[AuditLogEntry]: ...
