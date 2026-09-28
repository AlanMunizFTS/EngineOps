from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import RoleORM, UserORM
from ops_platform.domain.entities import Role, User
from ops_platform.domain.ports.user_repository import UserRepository

ADMIN_ROLE_NAME = "admin"


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

    async def get_by_id(self, user_id: UUID) -> User | None:
        orm_user = await self._session.get(UserORM, user_id)
        return _to_entity(orm_user) if orm_user else None

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserORM).order_by(UserORM.email))
        return [_to_entity(orm_user) for orm_user in result.scalars().all()]

    async def create(
        self, email: str, hashed_password: str, full_name: str, *, is_admin: bool = False
    ) -> User:
        orm_user = UserORM(email=email, hashed_password=hashed_password, full_name=full_name)
        if is_admin:
            orm_user.roles.append(await self._get_or_create_admin_role())
        self._session.add(orm_user)
        await self._session.commit()
        await self._session.refresh(orm_user, attribute_names=["roles"])
        return _to_entity(orm_user)

    async def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        hashed_password: str | None = None,
        full_name: str | None = None,
        is_active: bool | None = None,
        roles: list[str] | None = None,
    ) -> User | None:
        orm_user = await self._session.get(UserORM, user_id)
        if orm_user is None:
            return None
        if email is not None:
            orm_user.email = email
        if hashed_password is not None:
            orm_user.hashed_password = hashed_password
        if full_name is not None:
            orm_user.full_name = full_name
        if is_active is not None:
            orm_user.is_active = is_active
        if roles is not None:
            result = await self._session.execute(select(RoleORM).where(RoleORM.name.in_(roles)))
            matched_roles = result.scalars().all()
            if {role.name for role in matched_roles} != set(roles):
                raise ValueError("Unknown role")
            orm_user.roles = matched_roles
        await self._session.commit()
        await self._session.refresh(orm_user, attribute_names=["roles"])
        return _to_entity(orm_user)

    async def delete(self, user_id: UUID) -> None:
        orm_user = await self._session.get(UserORM, user_id)
        if orm_user is None:
            return
        await self._session.delete(orm_user)
        await self._session.commit()

    async def _get_or_create_admin_role(self) -> RoleORM:
        result = await self._session.execute(
            select(RoleORM).where(RoleORM.name == ADMIN_ROLE_NAME)
        )
        role = result.scalar_one_or_none()
        if role is None:
            role = RoleORM(name=ADMIN_ROLE_NAME, description="Full administrative access")
            self._session.add(role)
            await self._session.flush()
        return role
