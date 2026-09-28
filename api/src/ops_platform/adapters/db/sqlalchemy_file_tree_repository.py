from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_filetree import FileTreeNodeORM
from ops_platform.domain.entities import FileTreeNode, FileTreeNodeType
from ops_platform.domain.ports.file_tree_repository import FileTreeRepository


def _to_entity(orm_node: FileTreeNodeORM) -> FileTreeNode:
    return FileTreeNode(
        id=orm_node.id,
        project_id=orm_node.project_id,
        parent_id=orm_node.parent_id,
        node_type=orm_node.node_type,
        name=orm_node.name,
        url=orm_node.url,
        content=orm_node.content,
        created_by=orm_node.created_by,
        created_at=orm_node.created_at,
    )


class SqlAlchemyFileTreeRepository(FileTreeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_node(
        self,
        project_id: UUID,
        parent_id: UUID | None,
        node_type: FileTreeNodeType,
        name: str,
        url: str | None,
        content: str | None,
        created_by: UUID | None,
    ) -> FileTreeNode:
        orm_node = FileTreeNodeORM(
            project_id=project_id,
            parent_id=parent_id,
            node_type=node_type,
            name=name,
            url=url,
            content=content,
            created_by=created_by,
        )
        self._session.add(orm_node)
        await self._session.flush()
        await self._session.refresh(orm_node)
        return _to_entity(orm_node)

    async def get(self, node_id: UUID) -> FileTreeNode | None:
        orm_node = await self._session.get(FileTreeNodeORM, node_id)
        return _to_entity(orm_node) if orm_node else None

    async def list_for_project(self, project_id: UUID) -> list[FileTreeNode]:
        result = await self._session.execute(
            select(FileTreeNodeORM)
            .where(FileTreeNodeORM.project_id == project_id)
            .order_by(FileTreeNodeORM.node_type, FileTreeNodeORM.name)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def update_content(self, node_id: UUID, content: str) -> FileTreeNode:
        orm_node = await self._session.get(FileTreeNodeORM, node_id)
        if orm_node is None:
            raise ValueError(f"file_tree_node {node_id} not found")

        orm_node.content = content
        await self._session.flush()
        await self._session.refresh(orm_node)
        return _to_entity(orm_node)

    async def delete(self, node_id: UUID) -> None:
        orm_node = await self._session.get(FileTreeNodeORM, node_id)
        if orm_node is not None:
            await self._session.delete(orm_node)
            await self._session.flush()
