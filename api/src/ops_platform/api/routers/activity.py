from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ops_platform.api.deps import get_audit_log_repository
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.schemas.audit import ActivityEntryResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityEntryResponse])
async def list_recent_activity(
    audit_log_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ActivityEntryResponse]:
    activity = await audit_log_repo.list_recent(limit)
    return [
        ActivityEntryResponse(
            id=item.entry.id,
            project_id=item.entry.project_id,
            project_name=item.project_name,
            actor_id=item.entry.actor_id,
            entity_type=item.entry.entity_type,
            entity_id=item.entry.entity_id,
            action=item.entry.action,
            diff=item.entry.diff,
            occurred_at=item.entry.occurred_at,
        )
        for item in activity
    ]
