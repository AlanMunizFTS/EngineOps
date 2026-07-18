from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.sqlalchemy_user_repository import SqlAlchemyUserRepository
from ops_platform.core.security import decode_access_token
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import User
from ops_platform.domain.ports.user_repository import UserRepository

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        email = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    user = await user_repository.get_by_email(email)
    if user is None:
        raise credentials_error
    return user
