from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CrossProjectDependencyError,
    DependencyAlreadyExistsError,
    DependencyNotFoundError,
    SelfDependencyError,
    TaskCycleError,
    TaskNotFoundError,
)
from app.models.enums import MemberRole
from app.models.task import TaskDependency
from app.repositories.dependency import DependencyRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.dependency import DependencyCreate, DependencyRead
from app.schemas.task import ImpactAnalysis
from app.services import cache, scheduling
from app.services.access import AccessService
from app.services.mappers import dependency_read
from app.services.scheduling import DepEdge, TaskNode
from app.ws import events


class DependencyService:
    def __init__(
        self,
        session: AsyncSession,
        dependency_repo: Optional[DependencyRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
        access: Optional[AccessService] = None,
    ) -> None:
        self.session = session
        self.dependencies = dependency_repo or DependencyRepository(session)
        self.tasks = task_repo or TaskRepository(session)
        self.projects = project_repo or ProjectRepository(session)
        self.access = access or AccessService(session, self.projects)

    async def list_for_project(
        self, project_id: int, user_id: int
    ) -> List[DependencyRead]:
        await self.access.get_project_for(project_id, user_id)
        return [
            dependency_read(dep)
            for dep in await self.dependencies.list_by_project(project_id)
        ]

    async def create(
        self, successor_id: int, user_id: int, data: DependencyCreate
    ) -> Tuple[DependencyRead, Optional[ImpactAnalysis]]:
        successor = await self.tasks.get(successor_id)
        if successor is None:
            raise TaskNotFoundError(details={"task_id": successor_id})
        project = await self.access.get_project_for(
            successor.project_id, user_id, MemberRole.responsible
        )

        if data.predecessor_id == successor_id:
            raise SelfDependencyError()
        predecessor = await self.tasks.get(data.predecessor_id)
        if predecessor is None:
            raise TaskNotFoundError(details={"task_id": data.predecessor_id})
        if predecessor.project_id != successor.project_id:
            raise CrossProjectDependencyError(
                details={
                    "predecessor_project_id": predecessor.project_id,
                    "successor_project_id": successor.project_id,
                }
            )
        if (
            await self.dependencies.find_pair(data.predecessor_id, successor_id)
            is not None
        ):
            raise DependencyAlreadyExistsError(
                details={
                    "predecessor_id": data.predecessor_id,
                    "successor_id": successor_id,
                }
            )

        tasks = await self.tasks.all_for_project(project.id)
        existing = await self.dependencies.list_by_project(project.id)
        node_ids = [task.id for task in tasks]
        edges = [
            DepEdge(dep.predecessor_id, dep.successor_id, dep.lag_days, dep.id)
            for dep in existing
        ]
        candidate = DepEdge(
            predecessor_id=data.predecessor_id,
            successor_id=successor_id,
            lag_days=data.lag_days,
        )
        if scheduling.would_create_cycle(node_ids, edges, candidate):
            raise TaskCycleError(
                details={
                    "predecessor_id": data.predecessor_id,
                    "successor_id": successor_id,
                }
            )

        dependency = await self.dependencies.create(
            project_id=project.id,
            predecessor_id=data.predecessor_id,
            successor_id=successor_id,
            type=data.type,
            lag_days=data.lag_days,
        )

        impact: Optional[ImpactAnalysis] = None
        if data.reschedule:
            impact = await self._reschedule_after_link(
                project_id=project.id,
                project_end=project.end_date,
                tasks=tasks,
                edges=edges + [candidate],
                successor_id=successor_id,
            )

        await self.session.commit()
        await self.session.refresh(dependency)
        await cache.invalidate_project(project.id)
        await events.publish(
            project.id,
            events.DEPENDENCY_CREATED,
            {
                "dependency_id": dependency.id,
                "predecessor_id": data.predecessor_id,
                "successor_id": successor_id,
            },
            user_id,
        )
        return dependency_read(dependency), impact

    async def _reschedule_after_link(
        self,
        *,
        project_id: int,
        project_end: date,
        tasks,
        edges: List[DepEdge],
        successor_id: int,
    ) -> ImpactAnalysis:
        from app.schemas.task import AffectedTask

        nodes = [TaskNode(task.id, task.start_date, task.end_date) for task in tasks]
        by_id = {task.id: task for task in tasks}
        shifted = scheduling.cascade_shift(nodes, edges, {})
        if shifted:
            await self.tasks.apply_shifts(
                {item.task_id: (item.new_start, item.new_end) for item in shifted}
            )
        projected = scheduling.projected_finish(nodes, {}, shifted) or project_end
        overrun = max((projected - project_end).days, 0)
        return ImpactAnalysis(
            task_id=successor_id,
            affected_tasks=[
                AffectedTask(
                    task_id=item.task_id,
                    title=by_id[item.task_id].title if item.task_id in by_id else "",
                    old_start_date=item.old_start,
                    old_end_date=item.old_end,
                    new_start_date=item.new_start,
                    new_end_date=item.new_end,
                    shift_days=item.shift_days,
                )
                for item in shifted
            ],
            affected_count=len(shifted),
            project_end_date=project_end,
            projected_end_date=projected,
            project_overrun_days=overrun,
            breaks_deadline=overrun > 0,
            applied=True,
        )

    async def delete(self, dependency_id: int, user_id: int) -> None:
        dependency: Optional[TaskDependency] = await self.dependencies.get(
            dependency_id
        )
        if dependency is None:
            raise DependencyNotFoundError(details={"dependency_id": dependency_id})
        project = await self.access.get_project_for(
            dependency.project_id, user_id, MemberRole.responsible
        )
        await self.dependencies.delete(dependency)
        await self.session.commit()
        await cache.invalidate_project(project.id)
        await events.publish(
            project.id,
            events.DEPENDENCY_DELETED,
            {"dependency_id": dependency_id},
            user_id,
        )
