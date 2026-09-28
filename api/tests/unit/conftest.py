from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fakes import (
    FakeAuditLog,
    FakeFileTreeRepository,
    FakeProjectRepository,
    FakeSession,
    FakeUserRepository,
)
from fakes_issues import (
    FakeIssueCommentRepository,
    FakeIssueRepository,
    FakeKanbanRepository,
    FakeLabelRepository,
)
from fakes_pieces import FakePieceRepository
from fastapi.testclient import TestClient

from ops_platform.api.deps import (
    get_audit_log_repository,
    get_audit_recorder,
    get_file_tree_repository,
    get_issue_comment_repository,
    get_issue_repository,
    get_kanban_repository,
    get_label_repository,
    get_piece_repository,
    get_project_repository,
    get_user_repository,
)
from ops_platform.core.security import create_access_token, hash_password
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import Role, User
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
def fake_audit_log(fake_project_repository: FakeProjectRepository) -> FakeAuditLog:
    return FakeAuditLog(fake_project_repository)


@pytest.fixture
def fake_file_tree_repository() -> FakeFileTreeRepository:
    return FakeFileTreeRepository()


@pytest.fixture
def fake_label_repository() -> FakeLabelRepository:
    return FakeLabelRepository()


@pytest.fixture
def fake_issue_repository(fake_label_repository: FakeLabelRepository) -> FakeIssueRepository:
    return FakeIssueRepository(fake_label_repository)


@pytest.fixture
def fake_issue_comment_repository() -> FakeIssueCommentRepository:
    return FakeIssueCommentRepository()


@pytest.fixture
def fake_kanban_repository() -> FakeKanbanRepository:
    return FakeKanbanRepository()


@pytest.fixture
def fake_piece_repository() -> FakePieceRepository:
    return FakePieceRepository()


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
def admin_user(fake_user_repository: FakeUserRepository) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password("irrelevant-for-these-tests"),
        full_name="Admin Test",
        is_active=True,
        created_at=datetime.now(UTC),
        roles=[Role(id=uuid.uuid4(), name="admin", description=None)],
    )
    fake_user_repository._users[user.email] = user
    return user


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token(subject=admin_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(
    fake_user_repository: FakeUserRepository,
    fake_project_repository: FakeProjectRepository,
    fake_audit_log: FakeAuditLog,
    fake_file_tree_repository: FakeFileTreeRepository,
    fake_label_repository: FakeLabelRepository,
    fake_issue_repository: FakeIssueRepository,
    fake_issue_comment_repository: FakeIssueCommentRepository,
    fake_kanban_repository: FakeKanbanRepository,
    fake_piece_repository: FakePieceRepository,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: fake_user_repository
    app.dependency_overrides[get_project_repository] = lambda: fake_project_repository
    app.dependency_overrides[get_audit_recorder] = lambda: fake_audit_log
    app.dependency_overrides[get_audit_log_repository] = lambda: fake_audit_log
    app.dependency_overrides[get_file_tree_repository] = lambda: fake_file_tree_repository
    app.dependency_overrides[get_label_repository] = lambda: fake_label_repository
    app.dependency_overrides[get_issue_repository] = lambda: fake_issue_repository
    app.dependency_overrides[get_issue_comment_repository] = lambda: fake_issue_comment_repository
    app.dependency_overrides[get_kanban_repository] = lambda: fake_kanban_repository
    app.dependency_overrides[get_piece_repository] = lambda: fake_piece_repository
    app.dependency_overrides[get_db_session] = _fake_db_session
    return TestClient(app)
