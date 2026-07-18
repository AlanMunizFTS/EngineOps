from __future__ import annotations

from abc import ABC, abstractmethod

from ops_platform.domain.entities import User


class UserRepository(ABC):
    """Port for user persistence. Adapters implement this against a concrete store."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def create(self, email: str, hashed_password: str, full_name: str) -> User: ...
