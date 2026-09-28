from uuid import UUID

from pydantic import BaseModel, Field

from ops_platform.domain.entities import IssueStatus


class KanbanColumnResponse(BaseModel):
    id: UUID
    board_id: UUID
    name: str
    order_index: int
    maps_to_statuses: list[IssueStatus]


class KanbanBoardResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    columns: list[KanbanColumnResponse]


class KanbanBoardCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class KanbanBoardRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class KanbanColumnCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    maps_to_statuses: list[IssueStatus] = Field(default_factory=list)


class KanbanColumnUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    maps_to_statuses: list[IssueStatus] = Field(default_factory=list)


class KanbanColumnReorderRequest(BaseModel):
    ordered_column_ids: list[UUID] = Field(min_length=1)
