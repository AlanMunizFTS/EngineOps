from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLogEntryResponse(BaseModel):
    id: UUID
    project_id: UUID
    actor_id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    diff: dict[str, Any]
    occurred_at: datetime
