from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ops_platform.api.deps import get_current_user, get_user_repository
from ops_platform.core.security import create_access_token, hash_password, verify_password
from ops_platform.domain.entities import User
from ops_platform.domain.ports.user_repository import UserRepository
from ops_platform.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        roles=[role.name for role in user.roles],
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    if await user_repository.get_by_email(payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = await user_repository.create(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    return _to_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokenResponse:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
    )

    user = await user_repository.get_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    return TokenResponse(access_token=create_access_token(subject=user.email))


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return _to_user_response(current_user)
