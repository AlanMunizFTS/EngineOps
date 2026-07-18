"""Bootstrap the first admin user - idempotent (safe to re-run).

Creates the user if it doesn't exist yet, and grants the seeded "admin" role
(from migration 0001) if it doesn't already hold it. There is no other way to get
an admin: `POST /auth/register` always creates a user with zero roles, and
role-based enforcement isn't built until Phase 7 - but the role still needs to
exist on someone before that lands.

Usage:
    docker compose exec api python utils/create_admin.py \
        --email admin@example.com --password "change-me"

Or locally (after `pip install -e ".[dev]"`):
    cd api && python utils/create_admin.py --email admin@example.com --password "change-me"
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import RoleORM, UserORM, UserRoleORM
from ops_platform.core.security import hash_password
from ops_platform.db.session import get_db_session

ADMIN_ROLE_NAME = "admin"


async def _ensure_admin(session: AsyncSession, email: str, password: str, full_name: str) -> None:
    user = (
        await session.execute(select(UserORM).where(UserORM.email == email))
    ).scalar_one_or_none()

    if user is None:
        user = UserORM(email=email, hashed_password=hash_password(password), full_name=full_name)
        session.add(user)
        await session.flush()
        print(f"Created user {email}")
    else:
        print(f"User {email} already exists")

    admin_role = (
        await session.execute(select(RoleORM).where(RoleORM.name == ADMIN_ROLE_NAME))
    ).scalar_one_or_none()
    if admin_role is None:
        raise RuntimeError(
            f'Role "{ADMIN_ROLE_NAME}" not found - run `alembic upgrade head` first '
            "(seeded by migration 0001)."
        )

    existing_link = (
        await session.execute(
            select(UserRoleORM).where(
                UserRoleORM.user_id == user.id, UserRoleORM.role_id == admin_role.id
            )
        )
    ).scalar_one_or_none()
    if existing_link is None:
        session.add(UserRoleORM(user_id=user.id, role_id=admin_role.id))
        print(f"Granted admin role to {email}")
    else:
        print(f"{email} already has the admin role")

    await session.commit()


async def create_admin(email: str, password: str, full_name: str) -> None:
    async for session in get_db_session():
        await _ensure_admin(session, email, password, full_name)
        return


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create (or promote) the first admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default="Admin")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    asyncio.run(create_admin(args.email, args.password, args.full_name))


if __name__ == "__main__":
    main()
