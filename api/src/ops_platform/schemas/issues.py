from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import IssuePriority, IssueStatus, IssueType
from ops_platform.domain.scheduling import ScheduleStatus, Urgency
from ops_platform.schemas.labels import LabelResponse


class IssueCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    issue_type: IssueType = IssueType.TASK
    priority: IssuePriority = IssuePriority.MEDIUM
    assignee_id: UUID | None = None
    parent_issue_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None


class IssueUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    issue_type: IssueType
    priority: IssuePriority
    assignee_id: UUID | None = None
    parent_issue_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    closed_at: date | None = None


class IssueStatusUpdateRequest(BaseModel):
    status: IssueStatus


class IssueLabelAttachRequest(BaseModel):
    label_id: UUID


class IssueResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: IssueStatus
    priority: IssuePriority
    issue_type: IssueType
    assignee_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    closed_at: datetime | None
    # The business-timezone (UTC-6) calendar day `closed_at` falls on - not
    # just `closed_at`'s date in UTC, which is a day ahead for roughly six
    # hours every evening (18:00-23:59 UTC-6). Callers displaying/editing a
    # "closed on" date must use this field, not slice `closed_at` themselves.
    closed_at_date: date | None
    parent_issue_id: UUID | None
    parent_assigned_at: datetime | None
    start_date: date | None
    due_date: date | None
    days_planned: int | None
    days_taken: int | None
    urgency: Urgency | None
    priority_score: int | None
    schedule_status: ScheduleStatus | None
    labels: list[LabelResponse]


class IssueCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)


class IssueCommentUpdateRequest(BaseModel):
    body: str = Field(min_length=1)


class IssueCommentResponse(BaseModel):
    id: UUID
    issue_id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime
    edited_at: datetime | None
