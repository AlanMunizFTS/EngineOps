from uuid import UUID

from pydantic import BaseModel, Field


class ChecklistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class ChecklistUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class ChecklistItemCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class ChecklistItemUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class ChecklistItemCompletionRequest(BaseModel):
    completed: bool


class ChecklistItemResponse(BaseModel):
    id: UUID
    checklist_id: UUID
    content: str
    position: int


class ProjectChecklistResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    items: list[ChecklistItemResponse]


class TaskChecklistItemResponse(ChecklistItemResponse):
    completed: bool


class TaskChecklistResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    items: list[TaskChecklistItemResponse]
