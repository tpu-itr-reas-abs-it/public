from datetime import date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.repositories.notification import NotificationRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.common import Page
from app.schemas.notification import NotificationRead
from app.services.mappers import notification_read
from app.services.status import overdue_info
from app.ws import events


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        notification_repo: Optional[NotificationRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
    ) -> None:
        self.session = session
        self.notifications = notification_repo or NotificationRepository(session)
        self.tasks = task_repo or TaskRepository(session)
        self.projects = project_repo or ProjectRepository(session)

    async def notify(
        self,
        *,
        user_id: int,
        project_id: Optional[int],
        task_id: Optional[int],
        type_: NotificationType,
        message: str,
    ) -> bool:
        created = await self.notifications.upsert(
            user_id=user_id,
            task_id=task_id,
            project_id=project_id,
            type_=type_,
            message=message,
        )
        if created and project_id is not None:
            await events.publish(
                project_id,
                events.NOTIFICATION_CREATED,
                {"user_id": user_id, "task_id": task_id, "type": type_.value},
            )
        return created

    async def list_for_user(
        self, user_id: int, limit: int, offset: int, only_unread: bool
    ) -> Page[NotificationRead]:
        items, total = await self.notifications.list_for_user(
            user_id, limit=limit, offset=offset, only_unread=only_unread
        )
        return Page.build(
            [notification_read(item) for item in items], total, limit, offset
        )

    async def unread_count(self, user_id: int) -> int:
        return await self.notifications.unread_count(user_id)

    async def mark_read(self, user_id: int, ids: Optional[List[int]]) -> int:
        updated = await self.notifications.mark_read(user_id, ids)
        await self.session.commit()
        return updated

    async def scan_overdue(self, today: Optional[date] = None) -> int:
        today = today or date.today()
        created = 0
        for task in await self.tasks.overdue_tasks(today):
            is_overdue, days = overdue_info(task.status, task.end_date, today)
            if not is_overdue:
                continue
            recipients = set(await self.projects.member_user_ids(task.project_id))
            project = await self.projects.get(task.project_id)
            if project is not None:
                recipients.add(project.owner_id)
            targets = (
                {task.assignee_id}
                if task.assignee_id
                else ({project.owner_id} if project else set())
            )
            for user_id in targets & recipients or targets:
                if user_id is None:
                    continue
                if await self.notify(
                    user_id=user_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    type_=NotificationType.task_overdue,
                    message=(
                        f"Задача «{task.title}» просрочена на {days} дн. "
                        f"(срок: {task.end_date.isoformat()})"
                    ),
                ):
                    created += 1
        await self.session.commit()
        return created
