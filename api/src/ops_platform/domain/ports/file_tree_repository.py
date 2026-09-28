from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import FileTreeNode, FileTreeNodeType


class FileTreeRepository(ABC):
    """Port for a project's file tree - folders, links, and text files."""

    @abstractmethod
    async def create_node(
        self,
        project_id: UUID,
        parent_id: UUID | None,
        node_type: FileTreeNodeType,
        name: str,
        url: str | None,
        content: str | None,
        created_by: UUID | None,
    ) -> FileTreeNode: ...

    @abstractmethod
    async def get(self, node_id: UUID) -> FileTreeNode | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[FileTreeNode]: ...

    @abstractmethod
    async def update_content(self, node_id: UUID, content: str) -> FileTreeNode:
        """Update a `file` node's content. Callers are responsible for checking
        `node_type == FileTreeNodeType.FILE` before calling this."""
        ...

    @abstractmethod
    async def delete(self, node_id: UUID) -> None: ...
