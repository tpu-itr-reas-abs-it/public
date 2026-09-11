from typing import List, Optional, Sequence

from sqlalchemy import delete, or_, select

from app.models.task import TaskDependency
from app.repositories.base import BaseRepository


class DependencyRepository(BaseRepository[TaskDependency]):
    model = TaskDependency

    async def list_by_project(self, project_id: int) -> List[TaskDependency]:
        stmt = (
            select(TaskDependency)
            .where(TaskDependency.project_id == project_id)
            .order_by(TaskDependency.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_task(self, task_id: int) -> List[TaskDependency]:
        stmt = select(TaskDependency).where(
            or_(
                TaskDependency.predecessor_id == task_id,
                TaskDependency.successor_id == task_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_pair(
        self, predecessor_id: int, successor_id: int
    ) -> Optional[TaskDependency]:
        stmt = select(TaskDependency).where(
            TaskDependency.predecessor_id == predecessor_id,
            TaskDependency.successor_id == successor_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_for_tasks(self, task_ids: Sequence[int]) -> None:
        if not task_ids:
            return
        ids = list(task_ids)
        await self.session.execute(
            delete(TaskDependency).where(
                or_(
                    TaskDependency.predecessor_id.in_(ids),
                    TaskDependency.successor_id.in_(ids),
                )
            )
        )
