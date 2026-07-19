from uuid import UUID

from pydantic import BaseModel, Field


class LabelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(min_length=4, max_length=7, pattern=r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")


class LabelResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    color: str
