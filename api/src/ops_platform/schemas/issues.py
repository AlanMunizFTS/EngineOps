from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import IssuePriority, IssueStatus, IssueType
from ops_platform.schemas.labels import LabelResponse


class IssueCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    issue_type: IssueType = IssueType.TASK
    priority: IssuePriority = IssuePriority.MEDIUM
    milestone_id: UUID | None = None
    assignee_id: UUID | None = None


class IssueUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    issue_type: IssueType
    priority: IssuePriority
    milestone_id: UUID | None = None
    assignee_id: UUID | None = None


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
    milestone_id: UUID | None
    assignee_id: UUID | None
    created_by: UUID
    created_at: datetime
    closed_at: datetime | None
    labels: list[LabelResponse]


class IssueCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)


class IssueCommentUpdateRequest(BaseModel):
    body: str = Field(min_length=1)


class IssueCommentResponse(BaseModel):
    id: UUID
    issue_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
    edited_at: datetime | None
