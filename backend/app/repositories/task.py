from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import or_, select, update

from app.models.enums import TaskStatus
from app.models.task import Task
from app.models.user import User
from app.repositories.base import BaseRepository

_ORDER_FIELDS = {
    "start_date": Task.start_date,
    "end_date": Task.end_date,
    "title": Task.title,
    "status": Task.status,
    "progress_percent": Task.progress_percent,
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
}


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get_with_assignee(
        self, task_id: int
    ) -> Optional[Tuple[Task, Optional[User]]]:
        stmt = (
            select(Task, User)
            .outerjoin(User, User.id == Task.assignee_id)
            .where(Task.id == task_id)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        return (row[0], row[1]) if row else None

    async def list_by_project(
        self,
        project_id: int,
        *,
        limit: int = 200,
        offset: int = 0,
        statuses: Optional[Sequence[TaskStatus]] = None,
        assignee_id: Optional[int] = None,
        search: Optional[str] = None,
        start_from: Optional[date] = None,
        end_to: Optional[date] = None,
        order_by: str = "start_date",
        order_dir: str = "asc",
    ) -> Tuple[List[Tuple[Task, Optional[User]]], int]:
        stmt = (
            select(Task, User)
            .outerjoin(User, User.id == Task.assignee_id)
            .where(Task.project_id == project_id)
        )
        if statuses:
            stmt = stmt.where(Task.status.in_(list(statuses)))
        if assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )
        if start_from is not None:
            stmt = stmt.where(Task.end_date >= start_from)
        if end_to is not None:
            stmt = stmt.where(Task.start_date <= end_to)

        total = await self.count(stmt)

        column = _ORDER_FIELDS.get(order_by, Task.start_date)
        ordering = column.desc() if order_dir.lower() == "desc" else column.asc()
        stmt = stmt.order_by(ordering, Task.id.asc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()], total

    async def all_for_project(self, project_id: int) -> List[Task]:
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.start_date, Task.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def all_for_projects(self, project_ids: Sequence[int]) -> List[Task]:
        if not project_ids:
            return []
        stmt = select(Task).where(Task.project_id.in_(list(project_ids)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def all_with_assignees(
        self, project_id: int
    ) -> List[Tuple[Task, Optional[User]]]:
        stmt = (
            select(Task, User)
            .outerjoin(User, User.id == Task.assignee_id)
            .where(Task.project_id == project_id)
            .order_by(Task.start_date, Task.id)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def ids_for_project(self, project_id: int) -> List[int]:
        result = await self.session.execute(
            select(Task.id).where(Task.project_id == project_id)
        )
        return [row[0] for row in result.all()]

    async def apply_shifts(self, shifts: Dict[int, Tuple[date, date]]) -> None:
        for task_id, (start_date, end_date) in shifts.items():
            await self.session.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(start_date=start_date, end_date=end_date)
            )
        await self.session.flush()

    async def overdue_tasks(self, today: date) -> List[Task]:
        stmt = select(Task).where(
            Task.end_date < today,
            Task.status.not_in([TaskStatus.done, TaskStatus.cancelled]),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_in_project(self, task_id: int, project_id: int) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id, Task.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
