from uuid import UUID

from pydantic import BaseModel

from ops_platform.domain.entities import IssueStatus


class KanbanColumnResponse(BaseModel):
    id: UUID
    board_id: UUID
    name: str
    order_index: int
    maps_to_status: IssueStatus


class KanbanBoardResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    columns: list[KanbanColumnResponse]
