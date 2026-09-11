from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.enums import NotificationType
from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        only_unread: bool = False,
    ) -> Tuple[List[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if only_unread:
            stmt = stmt.where(Notification.is_read.is_(False))
        total = await self.count(stmt)
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def unread_count(self, user_id: int) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def upsert(
        self,
        *,
        user_id: int,
        task_id: Optional[int],
        project_id: Optional[int],
        type_: NotificationType,
        message: str,
    ) -> bool:
        stmt = (
            pg_insert(Notification)
            .values(
                user_id=user_id,
                task_id=task_id,
                project_id=project_id,
                type=type_,
                message=message,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    Notification.user_id,
                    Notification.task_id,
                    Notification.type,
                ]
            )
            .returning(Notification.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def mark_read(self, user_id: int, ids: Optional[Sequence[int]]) -> int:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        if ids:
            stmt = stmt.where(Notification.id.in_(list(ids)))
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
