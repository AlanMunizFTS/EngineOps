from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import UserORM
from ops_platform.domain.entities import Role, User
from ops_platform.domain.ports.user_repository import UserRepository


def _to_entity(orm_user: UserORM) -> User:
    return User(
        id=orm_user.id,
        email=orm_user.email,
        hashed_password=orm_user.hashed_password,
        full_name=orm_user.full_name,
        is_active=orm_user.is_active,
        created_at=orm_user.created_at,
        roles=[Role(id=r.id, name=r.name, description=r.description) for r in orm_user.roles],
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserORM).where(UserORM.email == email))
        orm_user = result.scalar_one_or_none()
        return _to_entity(orm_user) if orm_user else None

    async def create(self, email: str, hashed_password: str, full_name: str) -> User:
        orm_user = UserORM(email=email, hashed_password=hashed_password, full_name=full_name)
        self._session.add(orm_user)
        await self._session.commit()
        await self._session.refresh(orm_user)
        return _to_entity(orm_user)
