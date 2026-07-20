from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import ProjectRole


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_by: UUID
    created_at: datetime


class ProjectMemberAddRequest(BaseModel):
    user_id: UUID
    project_role: ProjectRole = ProjectRole.CONTRIBUTOR


class ProjectMemberResponse(BaseModel):
    project_id: UUID
    user_id: UUID
    project_role: ProjectRole
    added_at: datetime


class ProjectMemberDetailResponse(BaseModel):
    project_id: UUID
    user_id: UUID
    project_role: ProjectRole
    added_at: datetime
    email: str
    full_name: str


