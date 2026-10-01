from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import TaskComment


class TaskCommentRepository(ABC):
    @abstractmethod
    async def create(self, task_id: UUID, author_id: UUID, body: str) -> TaskComment: ...

    @abstractmethod
    async def get(self, comment_id: UUID) -> TaskComment | None: ...

    @abstractmethod
    async def list_for_task(self, task_id: UUID) -> list[TaskComment]: ...

    @abstractmethod
    async def update_body(self, comment_id: UUID, body: str) -> TaskComment: ...
