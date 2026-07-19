from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fakes import (
    FakeAreaRepository,
    FakeAuditLog,
    FakeImplementationRepository,
    FakeMachineRepository,
    FakeProjectRepository,
    FakeSession,
)
from fastapi.testclient import TestClient

from ops_platform.api.deps import (
    get_area_repository,
    get_audit_log_repository,
    get_audit_recorder,
    get_implementation_repository,
    get_machine_repository,
    get_project_repository,
    get_user_repository,
)
from ops_platform.core.security import create_access_token, hash_password
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import User
from ops_platform.domain.ports.user_repository import UserRepository
from ops_platform.main import create_app


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    async def create(self, email: str, hashed_password: str, full_name: str) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        self._users[email] = user
        return user


async def _fake_db_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


@pytest.fixture
def fake_user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def fake_project_repository() -> FakeProjectRepository:
    return FakeProjectRepository()


@pytest.fixture
def fake_area_repository() -> FakeAreaRepository:
    return FakeAreaRepository()


@pytest.fixture
def fake_machine_repository() -> FakeMachineRepository:
    return FakeMachineRepository()


@pytest.fixture
def fake_implementation_repository() -> FakeImplementationRepository:
    return FakeImplementationRepository()


@pytest.fixture
def fake_audit_log(fake_project_repository: FakeProjectRepository) -> FakeAuditLog:
    return FakeAuditLog(fake_project_repository)


@pytest.fixture
def current_user(fake_user_repository: FakeUserRepository) -> User:
    user = User(
        id=uuid.uuid4(),
        email="pm@example.com",
        hashed_password=hash_password("irrelevant-for-these-tests"),
        full_name="PM Test",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    fake_user_repository._users[user.email] = user
    return user


@pytest.fixture
def auth_headers(current_user: User) -> dict[str, str]:
    token = create_access_token(subject=current_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(
    fake_user_repository: FakeUserRepository,
    fake_project_repository: FakeProjectRepository,
    fake_area_repository: FakeAreaRepository,
    fake_machine_repository: FakeMachineRepository,
    fake_implementation_repository: FakeImplementationRepository,
    fake_audit_log: FakeAuditLog,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: fake_user_repository
    app.dependency_overrides[get_project_repository] = lambda: fake_project_repository
    app.dependency_overrides[get_area_repository] = lambda: fake_area_repository
    app.dependency_overrides[get_machine_repository] = lambda: fake_machine_repository
    app.dependency_overrides[get_implementation_repository] = (
        lambda: fake_implementation_repository
    )
    app.dependency_overrides[get_audit_recorder] = lambda: fake_audit_log
    app.dependency_overrides[get_audit_log_repository] = lambda: fake_audit_log
    app.dependency_overrides[get_db_session] = _fake_db_session
    return TestClient(app)
