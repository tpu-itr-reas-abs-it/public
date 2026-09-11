from typing import List, Optional, Tuple

from sqlalchemy import select

from app.models.comment import Comment
from app.models.user import User
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_for_task(
        self, task_id: int, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Tuple[Comment, Optional[User]]], int]:
        stmt = (
            select(Comment, User)
            .outerjoin(User, User.id == Comment.user_id)
            .where(Comment.task_id == task_id)
        )
        total = await self.count(stmt)
        stmt = stmt.order_by(Comment.created_at.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()], total

    async def list_for_project(self, project_id: int) -> List[Comment]:
        from app.models.task import Task

        stmt = (
            select(Comment)
            .join(Task, Task.id == Comment.task_id)
            .where(Task.project_id == project_id)
            .order_by(Comment.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
