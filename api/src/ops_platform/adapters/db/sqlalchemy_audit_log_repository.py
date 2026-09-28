from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import AuditLogORM, ProjectORM
from ops_platform.domain.entities import ActivityEntry, AuditLogEntry
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository


def _to_entity(orm_entry: AuditLogORM) -> AuditLogEntry:
    return AuditLogEntry(
        id=orm_entry.id,
        project_id=orm_entry.project_id,
        actor_id=orm_entry.actor_id,
        entity_type=orm_entry.entity_type,
        entity_id=orm_entry.entity_id,
        action=orm_entry.action,
        diff=orm_entry.diff_json or {},
        occurred_at=orm_entry.occurred_at,
    )


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_project(self, project_id: UUID) -> list[AuditLogEntry]:
        result = await self._session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.project_id == project_id)
            .order_by(AuditLogORM.occurred_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[AuditLogEntry]:
        result = await self._session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.entity_type == entity_type, AuditLogORM.entity_id == entity_id)
            .order_by(AuditLogORM.occurred_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def list_recent(self, limit: int) -> list[ActivityEntry]:
        result = await self._session.execute(
            select(AuditLogORM, ProjectORM.name)
            .join(ProjectORM, ProjectORM.id == AuditLogORM.project_id)
            .order_by(AuditLogORM.occurred_at.desc())
            .limit(limit)
        )
        return [
            ActivityEntry(entry=_to_entity(orm_entry), project_name=project_name)
            for orm_entry, project_name in result.all()
        ]
