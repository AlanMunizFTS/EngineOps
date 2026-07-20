from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.sqlalchemy_audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from ops_platform.adapters.db.sqlalchemy_audit_recorder import SqlAlchemyAuditRecorder
from ops_platform.adapters.db.sqlalchemy_issue_comment_repository import (
    SqlAlchemyIssueCommentRepository,
)
from ops_platform.adapters.db.sqlalchemy_issue_repository import SqlAlchemyIssueRepository
from ops_platform.adapters.db.sqlalchemy_kanban_repository import SqlAlchemyKanbanRepository
from ops_platform.adapters.db.sqlalchemy_label_repository import SqlAlchemyLabelRepository
from ops_platform.adapters.db.sqlalchemy_milestone_repository import (
    SqlAlchemyMilestoneRepository,
)
from ops_platform.adapters.db.sqlalchemy_project_repository import SqlAlchemyProjectRepository
from ops_platform.adapters.db.sqlalchemy_user_repository import SqlAlchemyUserRepository
from ops_platform.core.security import decode_access_token
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import User
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.issue_comment_repository import IssueCommentRepository
from ops_platform.domain.ports.issue_repository import IssueRepository
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.label_repository import LabelRepository
from ops_platform.domain.ports.milestone_repository import MilestoneRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.domain.ports.user_repository import UserRepository

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_project_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectRepository:
    return SqlAlchemyProjectRepository(session)


def get_label_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LabelRepository:
    return SqlAlchemyLabelRepository(session)


def get_milestone_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MilestoneRepository:
    return SqlAlchemyMilestoneRepository(session)


def get_issue_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueRepository:
    return SqlAlchemyIssueRepository(session)


def get_issue_comment_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueCommentRepository:
    return SqlAlchemyIssueCommentRepository(session)


def get_kanban_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KanbanRepository:
    return SqlAlchemyKanbanRepository(session)


def get_audit_recorder(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditRecorder:
    return SqlAlchemyAuditRecorder(session)


def get_audit_log_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditLogRepository:
    return SqlAlchemyAuditLogRepository(session)


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        email = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    user = await user_repository.get_by_email(email)
    if user is None:
        raise credentials_error
    return user
