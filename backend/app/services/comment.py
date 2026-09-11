from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TaskNotFoundError
from app.models.enums import MemberRole, NotificationType
from app.repositories.comment import CommentRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page
from app.services.access import AccessService
from app.services.mappers import comment_read
from app.services.notification import NotificationService
from app.ws import events


class CommentService:
    def __init__(
        self,
        session: AsyncSession,
        comment_repo: Optional[CommentRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
        user_repo: Optional[UserRepository] = None,
        access: Optional[AccessService] = None,
        notifications: Optional[NotificationService] = None,
    ) -> None:
        self.session = session
        self.comments = comment_repo or CommentRepository(session)
        self.tasks = task_repo or TaskRepository(session)
        self.projects = project_repo or ProjectRepository(session)
        self.users = user_repo or UserRepository(session)
        self.access = access or AccessService(session, self.projects)
        self.notifications = notifications or NotificationService(session)

    async def list_for_task(
        self, task_id: int, user_id: int, limit: int, offset: int
    ) -> Page[CommentRead]:
        task = await self.tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(details={"task_id": task_id})
        await self.access.get_project_for(task.project_id, user_id)
        rows, total = await self.comments.list_for_task(task_id, limit, offset)
        return Page.build(
            [comment_read(comment, author) for comment, author in rows],
            total,
            limit,
            offset,
        )

    async def create(
        self, task_id: int, user_id: int, data: CommentCreate
    ) -> CommentRead:
        task = await self.tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(details={"task_id": task_id})
        await self.access.get_project_for(task.project_id, user_id, MemberRole.viewer)

        comment = await self.comments.create(
            task_id=task_id, user_id=user_id, text=data.text.strip()
        )
        author = await self.users.get(user_id)

        if task.assignee_id and task.assignee_id != user_id:
            await self.notifications.notify(
                user_id=task.assignee_id,
                project_id=task.project_id,
                task_id=task_id,
                type_=NotificationType.task_commented,
                message=f"Новый комментарий к задаче «{task.title}»",
            )

        await self.session.commit()
        await self.session.refresh(comment)
        await events.publish(
            task.project_id,
            events.COMMENT_CREATED,
            {"task_id": task_id, "comment_id": comment.id},
            user_id,
        )
        return comment_read(comment, author)
