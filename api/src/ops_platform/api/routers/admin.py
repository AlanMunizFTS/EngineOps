from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ops_platform.api.deps import get_current_admin_user, get_user_repository
from ops_platform.core.security import hash_password
from ops_platform.domain.entities import User
from ops_platform.domain.ports.user_repository import UserRepository
from ops_platform.schemas.auth import AdminCreateUserRequest, AdminUpdateUserRequest, UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        roles=[role.name for role in user.roles],
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: Annotated[User, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[UserResponse]:
    users = await user_repository.list_all()
    return [_to_user_response(user) for user in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminCreateUserRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
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
        is_admin=payload.is_admin,
    )
    return _to_user_response(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin: Annotated[User, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )
    if await user_repository.get_by_id(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await user_repository.delete(user_id)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: AdminUpdateUserRequest,
    admin: Annotated[User, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.email is not None:
        existing = await user_repository.get_by_email(payload.email)
        if existing is not None and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

    if user_id == admin.id and (
        (payload.email is not None and payload.email != admin.email)
        or payload.is_active is False
        or (payload.roles is not None and "admin" not in payload.roles)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own email, deactivate your account, or remove admin role",
        )

    try:
        updated = await user_repository.update(
            user_id,
            email=str(payload.email) if payload.email is not None else None,
            hashed_password=hash_password(payload.password) if payload.password else None,
            full_name=payload.full_name,
            is_active=payload.is_active,
            roles=payload.roles,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_user_response(updated)
