from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import AuditLogORM
from ops_platform.domain.ports.audit_recorder import AuditRecorder


class SqlAlchemyAuditRecorder(AuditRecorder):
    """Adds the audit row to the session without committing - the caller (a router,
    orchestrating one or more repository writes) commits once, so the audit entry is
    part of the same transaction as the write it describes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        self._session.add(
            AuditLogORM(
                project_id=project_id,
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                diff_json=diff,
            )
        )
