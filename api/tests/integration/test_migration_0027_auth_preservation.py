"""Destructive migration test for the Task hierarchy rebuild.

Set ``MIGRATION_TEST_DATABASE_URL`` to an otherwise disposable PostgreSQL
database whose name contains ``test``.  The test resets its schema.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.engine import make_url

API_ROOT = Path(__file__).resolve().parents[2]


def _migration_database_url() -> str:
    raw_url = os.getenv("MIGRATION_TEST_DATABASE_URL", "")
    if not raw_url:
        pytest.skip("MIGRATION_TEST_DATABASE_URL is not configured")

    url = make_url(raw_url)
    if not url.database or "test" not in url.database.lower():
        pytest.fail("MIGRATION_TEST_DATABASE_URL must name an explicit test database")
    return raw_url


def _alembic(revision: str, database_url: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=API_ROOT,
        env=environment,
        check=True,
    )


def _asyncpg_dsn(database_url: str) -> str:
    url = make_url(database_url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


async def _auth_snapshot(connection: asyncpg.Connection) -> tuple[list[tuple], ...]:
    users = await connection.fetch(
        """SELECT id, email, hashed_password, full_name, is_active, created_at
           FROM users ORDER BY id"""
    )
    roles = await connection.fetch("SELECT id, name, description FROM roles ORDER BY id")
    assignments = await connection.fetch(
        "SELECT user_id, role_id FROM user_roles ORDER BY user_id, role_id"
    )
    return (
        tuple(tuple(row.values()) for row in users),
        tuple(tuple(row.values()) for row in roles),
        tuple(tuple(row.values()) for row in assignments),
    )


@pytest.mark.asyncio
async def test_0027_preserves_auth_across_upgrade_downgrade_upgrade() -> None:
    database_url = _migration_database_url()
    dsn = _asyncpg_dsn(database_url)

    # Start from a known historical schema.  This database is guarded above as
    # test-only because both directions intentionally discard project data.
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=API_ROOT,
        env=environment,
        check=True,
    )
    _alembic("0026", database_url)

    connection = await asyncpg.connect(dsn)
    try:
        admin_role_id = uuid.uuid4()
        regular_role_id = uuid.uuid4()
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()
        project_id = uuid.uuid4()
        await connection.execute("DELETE FROM user_roles")
        await connection.execute("DELETE FROM users")
        await connection.execute("DELETE FROM roles")
        await connection.executemany(
            "INSERT INTO roles (id, name, description) VALUES ($1, $2, $3)",
            [
                (admin_role_id, "admin", "Administrator"),
                (regular_role_id, "regular", "Regular user"),
            ],
        )
        await connection.executemany(
            """INSERT INTO users
                   (id, email, hashed_password, full_name, is_active)
               VALUES ($1, $2, $3, $4, $5)""",
            [
                (user_a_id, "a@example.com", "$2b$auth-hash-a", "User A", True),
                (user_b_id, "b@example.com", "$2b$auth-hash-b", "User B", False),
            ],
        )
        await connection.executemany(
            "INSERT INTO user_roles (user_id, role_id) VALUES ($1, $2)",
            [
                (user_a_id, admin_role_id),
                (user_a_id, regular_role_id),
                (user_b_id, regular_role_id),
            ],
        )
        # Exercise disposable rows that point into auth. Their deletion must
        # not flow backwards into users or global role assignments.
        await connection.execute(
            """INSERT INTO projects (id, name, description, created_by)
               VALUES ($1, $2, $3, $4)""",
            project_id,
            "Disposable project",
            "Removed by 0027",
            user_a_id,
        )
        await connection.execute(
            """INSERT INTO project_members (project_id, user_id, project_role)
               VALUES ($1, $2, 'owner')""",
            project_id,
            user_b_id,
        )
        await connection.execute(
            """INSERT INTO issues
                   (id, project_id, title, status, priority, issue_type,
                    assignee_id, created_by)
               VALUES ($1, $2, $3, 'todo', 'high', 'task', $4, $5)""",
            uuid.uuid4(),
            project_id,
            "Disposable issue",
            user_b_id,
            user_a_id,
        )
        before = await _auth_snapshot(connection)
    finally:
        await connection.close()

    _alembic("0027", database_url)
    connection = await asyncpg.connect(dsn)
    try:
        assert await _auth_snapshot(connection) == before
        assert await connection.fetchval("SELECT count(*) FROM projects") == 0
        assert await connection.fetchval("SELECT to_regclass('tasks')") == "tasks"
        assert await connection.fetchval("SELECT to_regclass('issues')") is None
    finally:
        await connection.close()

    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "0026"],
        cwd=API_ROOT,
        env=environment,
        check=True,
    )
    connection = await asyncpg.connect(dsn)
    try:
        assert await _auth_snapshot(connection) == before
        assert await connection.fetchval("SELECT to_regclass('issues')") == "issues"
        assert await connection.fetchval("SELECT to_regclass('tasks')") is None
    finally:
        await connection.close()

    _alembic("0027", database_url)
    connection = await asyncpg.connect(dsn)
    try:
        assert await _auth_snapshot(connection) == before
        cascade_project_id = uuid.uuid4()
        parent_task_id = uuid.uuid4()
        child_task_id = uuid.uuid4()
        await connection.execute(
            """INSERT INTO projects (id, name, description, created_by)
               VALUES ($1, $2, $3, $4)""",
            cascade_project_id,
            "Cascade project",
            "Verifies Task self-reference cleanup",
            user_a_id,
        )
        await connection.execute(
            """INSERT INTO tasks
                   (id, project_id, title, status, priority, task_type, created_by)
               VALUES ($1, $2, $3, 'todo', 'medium', 'task', $4)""",
            parent_task_id,
            cascade_project_id,
            "Parent Task",
            user_a_id,
        )
        await connection.execute(
            """INSERT INTO tasks
                   (id, project_id, parent_task_id, title, status, priority, task_type,
                    created_by)
               VALUES ($1, $2, $3, $4, 'todo', 'medium', 'task', $5)""",
            child_task_id,
            cascade_project_id,
            parent_task_id,
            "Subtask",
            user_a_id,
        )
        await connection.execute("DELETE FROM projects WHERE id = $1", cascade_project_id)
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM tasks WHERE project_id = $1", cascade_project_id
            )
            == 0
        )
    finally:
        await connection.close()
