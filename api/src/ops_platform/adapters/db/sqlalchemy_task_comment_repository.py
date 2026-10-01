from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_tasks import TaskCommentORM
from ops_platform.domain.entities import TaskComment
from ops_platform.domain.ports.task_comment_repository import TaskCommentRepository


def _to_entity(row: TaskCommentORM) -> TaskComment:
    return TaskComment(
        id=row.id,
        task_id=row.task_id,
        author_id=row.author_id,
        body=row.body,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyTaskCommentRepository(TaskCommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task_id: UUID, author_id: UUID, body: str) -> TaskComment:
        row = TaskCommentORM(task_id=task_id, author_id=author_id, body=body)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)

    async def get(self, comment_id: UUID) -> TaskComment | None:
        row = await self._session.get(TaskCommentORM, comment_id)
        return _to_entity(row) if row else None

    async def list_for_task(self, task_id: UUID) -> list[TaskComment]:
        result = await self._session.execute(
            select(TaskCommentORM)
            .where(TaskCommentORM.task_id == task_id)
            .order_by(TaskCommentORM.created_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def update_body(self, comment_id: UUID, body: str) -> TaskComment:
        row = await self._session.get(TaskCommentORM, comment_id)
        if row is None:
            raise ValueError(f"task comment {comment_id} not found")
        row.body = body
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_entity(row)
