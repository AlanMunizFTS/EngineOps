from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import MilestoneStatus


class MilestoneCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: MilestoneStatus = MilestoneStatus.OPEN
    due_date: date | None = None


class MilestoneUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: MilestoneStatus | None = None
    due_date: date | None = None


class MilestoneResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: MilestoneStatus
    due_date: date | None
    created_at: datetime
    updated_at: datetime
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
