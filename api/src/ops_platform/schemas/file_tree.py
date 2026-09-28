from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ops_platform.domain.entities import FileTreeNodeType

_MAX_CONTENT_LENGTH = 200_000


class FileTreeNodeCreateRequest(BaseModel):
    parent_id: UUID | None = None
    node_type: FileTreeNodeType
    name: str = Field(min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    content: str | None = Field(default=None, max_length=_MAX_CONTENT_LENGTH)

    @model_validator(mode="after")
    def _fields_match_node_type(self) -> "FileTreeNodeCreateRequest":
        if self.node_type == FileTreeNodeType.LINK:
            if not self.url:
                raise ValueError("url is required for a link node")
            if self.content is not None:
                raise ValueError("content must not be set for a link node")
        elif self.node_type == FileTreeNodeType.FOLDER:
            if self.url:
                raise ValueError("url must not be set for a folder node")
            if self.content is not None:
                raise ValueError("content must not be set for a folder node")
        elif self.node_type == FileTreeNodeType.FILE and self.url:
            raise ValueError("url must not be set for a file node")
        return self


class FileTreeNodeUpdateRequest(BaseModel):
    content: str = Field(max_length=_MAX_CONTENT_LENGTH)


class FileTreeNodeResponse(BaseModel):
    id: UUID
    project_id: UUID
    parent_id: UUID | None
    node_type: FileTreeNodeType
    name: str
    url: str | None
    content: str | None
    created_by: UUID | None
    created_at: datetime
