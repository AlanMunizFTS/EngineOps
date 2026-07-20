from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import MilestoneStatus


class MilestoneCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: date | None = None


class MilestoneStatusUpdateRequest(BaseModel):
    status: MilestoneStatus


class MilestoneResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    due_date: date | None
    status: MilestoneStatus
    created_at: datetime


class MilestoneProgressResponse(MilestoneResponse):
    """MilestoneResponse plus the closed/total issue counts - GitHub's milestone
    progress bar equivalent. Computed in the router from IssueRepository, not
    stored (there is no `milestone_progress` table)."""

    total_issues: int
    closed_issues: int
    percent_complete: float
