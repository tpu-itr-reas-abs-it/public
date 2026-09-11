from typing import Annotated, Optional

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.common import PaginationParams
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService
from app.services.comment import CommentService
from app.services.dependency import DependencyService
from app.services.export import ExportService
from app.services.notification import NotificationService
from app.services.project import ProjectService
from app.services.task import TaskService

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    session: SessionDep,
) -> User:
    if credentials is None or not credentials.credentials:
        raise InvalidTokenError("Требуется заголовок Authorization: Bearer <token>")
    user_id = decode_token(credentials.credentials, "access")
    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("Пользователь недоступен")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_pagination(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


def get_project_service(session: SessionDep) -> ProjectService:
    return ProjectService(session)


def get_task_service(session: SessionDep) -> TaskService:
    return TaskService(session)


def get_dependency_service(session: SessionDep) -> DependencyService:
    return DependencyService(session)


def get_analytics_service(session: SessionDep) -> AnalyticsService:
    return AnalyticsService(session)


def get_comment_service(session: SessionDep) -> CommentService:
    return CommentService(session)


def get_notification_service(session: SessionDep) -> NotificationService:
    return NotificationService(session)


def get_export_service(session: SessionDep) -> ExportService:
    return ExportService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
DependencyServiceDep = Annotated[DependencyService, Depends(get_dependency_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
NotificationServiceDep = Annotated[
    NotificationService, Depends(get_notification_service)
]
ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]
