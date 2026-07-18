import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from ops_platform.api.deps import get_user_repository
from ops_platform.core.security import hash_password
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


@pytest.fixture
def fake_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def client(fake_repository: FakeUserRepository) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: fake_repository
    return TestClient(app)


def test_register_creates_user(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "supersecret", "full_name": "Jane Doe"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jane@example.com"
    assert body["roles"] == []


def test_register_rejects_duplicate_email(
    client: TestClient, fake_repository: FakeUserRepository
) -> None:
    client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "supersecret", "full_name": "Jane Doe"},
    )
    response = client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "anotherpass", "full_name": "Jane Doe"},
    )
    assert response.status_code == 409


def test_login_returns_token_for_valid_credentials(
    client: TestClient, fake_repository: FakeUserRepository
) -> None:
    fake_repository._users["jane@example.com"] = User(
        id=uuid.uuid4(),
        email="jane@example.com",
        hashed_password=hash_password("supersecret"),
        full_name="Jane Doe",
        is_active=True,
        created_at=datetime.now(UTC),
    )

    response = client.post(
        "/auth/login", json={"email": "jane@example.com", "password": "supersecret"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_rejects_invalid_password(
    client: TestClient, fake_repository: FakeUserRepository
) -> None:
    fake_repository._users["jane@example.com"] = User(
        id=uuid.uuid4(),
        email="jane@example.com",
        hashed_password=hash_password("supersecret"),
        full_name="Jane Doe",
        is_active=True,
        created_at=datetime.now(UTC),
    )

    response = client.post(
        "/auth/login", json={"email": "jane@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401
