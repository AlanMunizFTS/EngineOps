from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AuditRecorder(ABC):
    """Reusable write-side hook for the audit_log. Every repository that mutates
    project-scoped data takes one of these and calls `record()` in the same
    transaction as its write, instead of logging ad hoc per router (kickoff spec
    §4: "implement this as a reusable service-layer hook, not copy-pasted logging
    in every router")."""

    @abstractmethod
    async def record(
        self,
        *,
        project_id: UUID,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        diff: dict[str, Any],
    ) -> None: ...
