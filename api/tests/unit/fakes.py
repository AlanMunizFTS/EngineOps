"""In-memory fakes for the Phase 1 repository ports, used by unit tests to exercise
routers without a real Postgres connection (mirrors the FakeUserRepository pattern
already used in test_auth.py)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ops_platform.domain.entities import (
    ActivityEntry,
    AuditLogEntry,
    FileTreeNode,
    FileTreeNodeType,
    Project,
    ProjectMember,
    ProjectMemberDetail,
    ProjectRole,
    Role,
    User,
)
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.file_tree_repository import FileTreeRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.domain.ports.user_repository import UserRepository


class FakeSession:
    """Stands in for AsyncSession - routers only ever call `.commit()` on it directly."""

    async def commit(self) -> None:
        return None


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
        if roles is not None:
            role_ids = {role.name: role.id for role in user.roles}
            updated_roles = [
                Role(
                    id=role_ids.get(name, uuid.uuid5(uuid.NAMESPACE_DNS, name)),
                    name=name,
                )
                for name in roles
            ]
        else:
            updated_roles = user.roles
        updated = replace(
            user,
            email=email if email is not None else user.email,
            hashed_password=(
                hashed_password if hashed_password is not None else user.hashed_password
            ),
            full_name=full_name if full_name is not None else user.full_name,
            is_active=is_active if is_active is not None else user.is_active,
            roles=updated_roles,
        )
        self._users.pop(user.email)
        self._users[updated.email] = updated
        return updated

    async def delete(self, user_id: UUID) -> None:
        email = next((e for e, u in self._users.items() if u.id == user_id), None)
        if email is not None:
            del self._users[email]


class FakeProjectRepository(ProjectRepository):
    """Takes the user repository fake to resolve email/full_name for
    list_members_with_users, mirroring the SQL adapter's join against users."""

    def __init__(self, user_repository: FakeUserRepository) -> None:
        self._user_repository = user_repository
        self._projects: dict[UUID, Project] = {}
        self._members: dict[UUID, list[ProjectMember]] = {}

    async def create(self, name: str, description: str | None, created_by: UUID) -> Project:
        project = Project(
            id=uuid.uuid4(),
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._projects[project.id] = project
        self._members[project.id] = []
        return project

    async def get(self, project_id: UUID) -> Project | None:
        return self._projects.get(project_id)

    async def list_all(self) -> list[Project]:
        return list(self._projects.values())

    async def delete(self, project_id: UUID) -> None:
        self._projects.pop(project_id, None)
        self._members.pop(project_id, None)

    async def add_member(
        self, project_id: UUID, user_id: UUID, project_role: ProjectRole
    ) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            project_role=project_role,
            added_at=datetime.now(UTC),
        )
        self._members.setdefault(project_id, []).append(member)
        return member

    async def list_members(self, project_id: UUID) -> list[ProjectMember]:
        return self._members.get(project_id, [])

    async def list_members_with_users(self, project_id: UUID) -> list[ProjectMemberDetail]:
        details = []
        for member in self._members.get(project_id, []):
            user = next(
                (u for u in self._user_repository._users.values() if u.id == member.user_id),
                None,
            )
            details.append(
                ProjectMemberDetail(
                    member=member,
                    email=user.email if user else "",
                    full_name=user.full_name if user else "",
                )
            )
        return details

    async def remove_member(self, project_id: UUID, user_id: UUID) -> None:
        members = self._members.get(project_id, [])
        self._members[project_id] = [m for m in members if m.user_id != user_id]


class FakeFileTreeRepository(FileTreeRepository):
    def __init__(self) -> None:
        self._nodes: dict[UUID, FileTreeNode] = {}

    async def create_node(
        self,
        project_id: UUID,
        parent_id: UUID | None,
        node_type: FileTreeNodeType,
        name: str,
        url: str | None,
        content: str | None,
        created_by: UUID | None,
    ) -> FileTreeNode:
        node = FileTreeNode(
            id=uuid.uuid4(),
            project_id=project_id,
            parent_id=parent_id,
            node_type=node_type,
            name=name,
            url=url,
            content=content,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._nodes[node.id] = node
        return node

    async def get(self, node_id: UUID) -> FileTreeNode | None:
        return self._nodes.get(node_id)

    async def list_for_project(self, project_id: UUID) -> list[FileTreeNode]:
        return [node for node in self._nodes.values() if node.project_id == project_id]

    async def update_content(self, node_id: UUID, content: str) -> FileTreeNode:
        node = self._nodes.get(node_id)
        if node is None:
            raise ValueError(f"file_tree_node {node_id} not found")
        updated = replace(node, content=content)
        self._nodes[node_id] = updated
        return updated

    async def delete(self, node_id: UUID) -> None:
        """Mirrors the real table's ON DELETE CASCADE on parent_id."""
        children = [node.id for node in self._nodes.values() if node.parent_id == node_id]
        for child_id in children:
            await self.delete(child_id)
        self._nodes.pop(node_id, None)


class FakeAuditLog(AuditRecorder, AuditLogRepository):
    """Implements both the write-side hook and the read-side repository, so tests can
    record via the router and immediately assert on what landed. Takes the project
    repository fake to resolve project names for the cross-project activity feed,
    mirroring the SQL adapter's join against `projects`."""

    def __init__(self, project_repository: FakeProjectRepository) -> None:
        self.entries: list[AuditLogEntry] = []
        self._project_repository = project_repository

    async def record(
        self,
        *,
        project_id: UUID,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        diff: dict[str, Any],
    ) -> None:
        self.entries.append(
            AuditLogEntry(
                id=uuid.uuid4(),
                project_id=project_id,
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                diff=diff,
                occurred_at=datetime.now(UTC),
            )
        )

    async def list_for_project(self, project_id: UUID) -> list[AuditLogEntry]:
        return [entry for entry in self.entries if entry.project_id == project_id]

    async def list_for_entity(self, entity_type: str, entity_id: UUID) -> list[AuditLogEntry]:
        return [
            entry
            for entry in self.entries
            if entry.entity_type == entity_type and entry.entity_id == entity_id
        ]

    async def list_recent(self, limit: int) -> list[ActivityEntry]:
        ordered = sorted(self.entries, key=lambda entry: entry.occurred_at, reverse=True)
        result = []
        for entry in ordered[:limit]:
            project = self._project_repository._projects.get(entry.project_id)
            result.append(ActivityEntry(entry=entry, project_name=project.name if project else ""))
        return result
