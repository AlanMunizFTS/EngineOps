from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ops_platform.domain.entities import IssuePriority, IssueStatus, IssueType
from ops_platform.schemas.labels import LabelResponse


class HierarchyLinkFields(BaseModel):
    """Shared by create/update requests - see docs/architecture/adr/0004-issue-
    hierarchy-linking.md: an issue links to at most one of plant/machine/
    implementation, or none (project-wide)."""

    plant_id: UUID | None = None
    machine_id: UUID | None = None
    implementation_id: UUID | None = None

    @model_validator(mode="after")
    def _at_most_one_link(self) -> Self:
        links = (self.plant_id, self.machine_id, self.implementation_id)
        if sum(link is not None for link in links) > 1:
            raise ValueError(
                "an issue may link to at most one of plant_id/machine_id/implementation_id"
            )
        return self


class IssueCreateRequest(HierarchyLinkFields):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    issue_type: IssueType = IssueType.TASK
    priority: IssuePriority = IssuePriority.MEDIUM
    milestone_id: UUID | None = None
    assignee_id: UUID | None = None


class IssueUpdateRequest(HierarchyLinkFields):
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
    plant_id: UUID | None
    machine_id: UUID | None
    implementation_id: UUID | None
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
