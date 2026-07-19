from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import IssueComment


class IssueCommentRepository(ABC):
    """Port for issue comment threads. @mentions are stored as plain text within
    `body` for now - no parsing/notification delivery yet (kickoff spec Phase 2)."""

    @abstractmethod
    async def create(self, issue_id: UUID, author_id: UUID, body: str) -> IssueComment: ...

    @abstractmethod
    async def get(self, comment_id: UUID) -> IssueComment | None: ...

    @abstractmethod
    async def list_for_issue(self, issue_id: UUID) -> list[IssueComment]: ...

    @abstractmethod
    async def update_body(self, comment_id: UUID, body: str) -> IssueComment:
        """Sets `body` and stamps `edited_at`."""
        ...
