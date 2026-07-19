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
    FakePlantRepository,
    FakeProjectRepository,
    FakeSession,
    FakeUserRepository,
)
from fastapi.testclient import TestClient

from ops_platform.api.deps import (
    get_area_repository,
    get_audit_log_repository,
    get_audit_recorder,
    get_implementation_repository,
    get_machine_repository,
    get_plant_repository,
    get_project_repository,
    get_user_repository,
)
from ops_platform.core.security import create_access_token, hash_password
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import User
from ops_platform.main import create_app


async def _fake_db_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


@pytest.fixture
def fake_user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def fake_project_repository(fake_user_repository: FakeUserRepository) -> FakeProjectRepository:
    return FakeProjectRepository(fake_user_repository)


@pytest.fixture
def fake_area_repository() -> FakeAreaRepository:
    return FakeAreaRepository()


@pytest.fixture
def fake_plant_repository(fake_area_repository: FakeAreaRepository) -> FakePlantRepository:
    return FakePlantRepository(fake_area_repository)


@pytest.fixture
def fake_machine_repository(fake_area_repository: FakeAreaRepository) -> FakeMachineRepository:
    return FakeMachineRepository(fake_area_repository)


@pytest.fixture
def fake_implementation_repository(
    fake_area_repository: FakeAreaRepository,
) -> FakeImplementationRepository:
    return FakeImplementationRepository(fake_area_repository)


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
    fake_plant_repository: FakePlantRepository,
    fake_machine_repository: FakeMachineRepository,
    fake_implementation_repository: FakeImplementationRepository,
    fake_audit_log: FakeAuditLog,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: fake_user_repository
    app.dependency_overrides[get_project_repository] = lambda: fake_project_repository
    app.dependency_overrides[get_area_repository] = lambda: fake_area_repository
    app.dependency_overrides[get_plant_repository] = lambda: fake_plant_repository
    app.dependency_overrides[get_machine_repository] = lambda: fake_machine_repository
    app.dependency_overrides[get_implementation_repository] = (
        lambda: fake_implementation_repository
    )
    app.dependency_overrides[get_audit_recorder] = lambda: fake_audit_log
    app.dependency_overrides[get_audit_log_repository] = lambda: fake_audit_log
    app.dependency_overrides[get_db_session] = _fake_db_session
    return TestClient(app)
