from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import TaskPriority, TaskStatus, TaskType
from ops_platform.domain.scheduling import ScheduleStatus, Urgency
from ops_platform.schemas.labels import LabelResponse


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    task_type: TaskType = TaskType.TASK
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    milestone_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    task_type: TaskType | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None
    milestone_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    closed_at: date | None = None


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class TaskParentUpdateRequest(BaseModel):
    parent_task_id: UUID | None


class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    milestone_id: UUID | None
    parent_task_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType
    assignee_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    closed_at_date: date | None
    parent_assigned_at: datetime | None
    start_date: date | None
    due_date: date | None
    days_planned: int | None
    days_taken: int | None
    urgency: Urgency | None
    priority_score: int | None
    schedule_status: ScheduleStatus | None
    subtasks_total: int
    subtasks_completed: int
    labels: list[LabelResponse]


class TaskCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)


class TaskCommentUpdateRequest(BaseModel):
    body: str = Field(min_length=1)


class TaskCommentResponse(BaseModel):
    id: UUID
    task_id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime
    updated_at: datetime
