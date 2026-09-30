from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import ProjectMemberORM, ProjectORM, UserORM
from ops_platform.domain.entities import Project, ProjectMember, ProjectMemberDetail, ProjectRole
from ops_platform.domain.ports.project_repository import ProjectRepository


def _to_project(orm_project: ProjectORM) -> Project:
    return Project(
        id=orm_project.id,
        name=orm_project.name,
        description=orm_project.description,
        created_by=orm_project.created_by,
        created_at=orm_project.created_at,
    )


def _to_member(orm_member: ProjectMemberORM) -> ProjectMember:
    return ProjectMember(
        project_id=orm_member.project_id,
        user_id=orm_member.user_id,
        project_role=orm_member.project_role,
        added_at=orm_member.added_at,
    )


class SqlAlchemyProjectRepository(ProjectRepository):
    """Write methods flush but do not commit - the router commits once after
    orchestrating project + default membership + default areas as one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, description: str | None, created_by: UUID) -> Project:
        orm_project = ProjectORM(name=name, description=description, created_by=created_by)
        self._session.add(orm_project)
        await self._session.flush()
        await self._session.refresh(orm_project)
        return _to_project(orm_project)

    async def get(self, project_id: UUID) -> Project | None:
        orm_project = await self._session.get(ProjectORM, project_id)
        return _to_project(orm_project) if orm_project else None

    async def list_all(self) -> list[Project]:
        result = await self._session.execute(
            select(ProjectORM).order_by(ProjectORM.created_at.desc())
        )
        return [_to_project(row) for row in result.scalars().all()]

    async def delete(self, project_id: UUID) -> None:
        await self._session.execute(delete(ProjectORM).where(ProjectORM.id == project_id))
        await self._session.flush()

    async def add_member(
        self, project_id: UUID, user_id: UUID, project_role: ProjectRole
    ) -> ProjectMember:
        orm_member = ProjectMemberORM(
            project_id=project_id, user_id=user_id, project_role=project_role
        )
        self._session.add(orm_member)
        await self._session.flush()
        await self._session.refresh(orm_member)
        return _to_member(orm_member)

    async def list_members(self, project_id: UUID) -> list[ProjectMember]:
        result = await self._session.execute(
            select(ProjectMemberORM).where(ProjectMemberORM.project_id == project_id)
        )
        return [_to_member(row) for row in result.scalars().all()]

    async def list_members_with_users(self, project_id: UUID) -> list[ProjectMemberDetail]:
        result = await self._session.execute(
            select(ProjectMemberORM, UserORM.email, UserORM.full_name)
            .join(UserORM, UserORM.id == ProjectMemberORM.user_id)
            .where(ProjectMemberORM.project_id == project_id)
        )
        return [
            ProjectMemberDetail(member=_to_member(orm_member), email=email, full_name=full_name)
            for orm_member, email, full_name in result.all()
        ]

    async def remove_member(self, project_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(ProjectMemberORM).where(
                ProjectMemberORM.project_id == project_id,
                ProjectMemberORM.user_id == user_id,
            )
        )
        await self._session.flush()
