from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import User


class UserRepository(ABC):
    """Port for user persistence. Adapters implement this against a concrete store."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...

    @abstractmethod
    async def create(
        self, email: str, hashed_password: str, full_name: str, *, is_admin: bool = False
    ) -> User:
        """`is_admin` links the new user to the global "admin" Role (creating
        it if it doesn't exist yet) - the same `roles`/`user_roles` mechanism
        already used for `UserResponse.roles`, just not previously acted on
        by any authorization check."""
        ...

    @abstractmethod
    async def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        hashed_password: str | None = None,
        full_name: str | None = None,
        is_active: bool | None = None,
        roles: list[str] | None = None,
    ) -> User | None: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None: ...
