import uuid
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ops_platform.api.deps import get_user_repository
from ops_platform.core.security import create_access_token, hash_password
from ops_platform.domain.entities import Role, User
from ops_platform.domain.ports.user_repository import UserRepository
from ops_platform.main import create_app


class FakeUserRepository(UserRepository):
    _ADMIN_ROLE = Role(id=uuid.uuid4(), name="admin", description="Full administrative access")

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return next((u for u in self._users.values() if u.id == user_id), None)

    async def list_all(self) -> list[User]:
        return sorted(self._users.values(), key=lambda u: u.email)

    async def create(
        self, email: str, hashed_password: str, full_name: str, *, is_admin: bool = False
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            created_at=datetime.now(UTC),
            roles=[self._ADMIN_ROLE] if is_admin else [],
        )
        self._users[email] = user
        return user

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
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        updated = replace(
            user,
            email=email if email is not None else user.email,
            hashed_password=(
                hashed_password if hashed_password is not None else user.hashed_password
            ),
            full_name=full_name if full_name is not None else user.full_name,
            is_active=is_active if is_active is not None else user.is_active,
        )
        self._users.pop(user.email)
        self._users[updated.email] = updated
        return updated

    async def delete(self, user_id: UUID) -> None:
        email = next((e for e, u in self._users.items() if u.id == user_id), None)
        if email is not None:
            del self._users[email]


@pytest.fixture
def fake_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def client(fake_repository: FakeUserRepository) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: fake_repository
    return TestClient(app)


def _owner_headers(fake_repository: FakeUserRepository) -> dict[str, str]:
    owner = User(
        id=uuid.uuid4(),
        email="owner@example.com",
        hashed_password=hash_password("supersecret"),
        full_name="Account Owner",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    fake_repository._users[owner.email] = owner
    token = create_access_token(subject=owner.email)
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_user(
    client: TestClient,
    fake_repository: FakeUserRepository,
) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "supersecret", "full_name": "Jane Doe"},
        headers=_owner_headers(fake_repository),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jane@example.com"
    assert body["roles"] == []


def test_register_rejects_duplicate_email(
    client: TestClient, fake_repository: FakeUserRepository
) -> None:
    headers = _owner_headers(fake_repository)
    client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "supersecret", "full_name": "Jane Doe"},
        headers=headers,
    )
    response = client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "anotherpass", "full_name": "Jane Doe"},
        headers=headers,
    )
    assert response.status_code == 409


def test_register_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "jane@example.com", "password": "supersecret", "full_name": "Jane Doe"},
    )
    assert response.status_code == 401


def test_authenticated_user_can_create_account_without_roles(
    client: TestClient,
    fake_repository: FakeUserRepository,
) -> None:
    fake_repository._users["owner@example.com"] = User(
        id=uuid.uuid4(),
        email="owner@example.com",
        hashed_password=hash_password("supersecret"),
        full_name="Account Owner",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    token = create_access_token(subject="owner@example.com")

    response = client.post(
        "/auth/users",
        json={"email": "new@example.com", "password": "supersecret", "full_name": "New User"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["roles"] == []


def test_create_account_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/auth/users",
        json={"email": "new@example.com", "password": "supersecret", "full_name": "New User"},
    )

    assert response.status_code == 401


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


def test_inactive_user_cannot_login(
    client: TestClient,
    fake_repository: FakeUserRepository,
) -> None:
    fake_repository._users["inactive@example.com"] = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        hashed_password=hash_password("supersecret"),
        full_name="Inactive User",
        is_active=False,
        created_at=datetime.now(UTC),
    )

    response = client.post(
        "/auth/login", json={"email": "inactive@example.com", "password": "supersecret"}
    )

    assert response.status_code == 401


def test_inactive_user_cannot_use_existing_token(
    client: TestClient,
    fake_repository: FakeUserRepository,
) -> None:
    fake_repository._users["inactive@example.com"] = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        hashed_password=hash_password("supersecret"),
        full_name="Inactive User",
        is_active=False,
        created_at=datetime.now(UTC),
    )
    token = create_access_token(subject="inactive@example.com")

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_requires_valid_token(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401
