from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidDateRangeError,
    TaskCycleError,
    TaskNotFoundError,
    ValidationError,
)
from app.models.enums import MemberRole, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.repositories.dependency import DependencyRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.schemas.common import Page
from app.schemas.task import (
    AffectedTask,
    ImpactAnalysis,
    TaskCreate,
    TaskFilter,
    TaskRead,
    TaskShiftRequest,
    TaskUpdate,
    TaskWithLinks,
)
from app.services import cache, scheduling
from app.services.access import AccessService
from app.services.mappers import task_read
from app.services.scheduling import DepEdge, TaskNode
from app.ws import events


class TaskService:
    def __init__(
        self,
        session: AsyncSession,
        task_repo: Optional[TaskRepository] = None,
        dependency_repo: Optional[DependencyRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
        user_repo: Optional[UserRepository] = None,
        access: Optional[AccessService] = None,
    ) -> None:
        self.session = session
        self.tasks = task_repo or TaskRepository(session)
        self.dependencies = dependency_repo or DependencyRepository(session)
        self.projects = project_repo or ProjectRepository(session)
        self.users = user_repo or UserRepository(session)
        self.access = access or AccessService(session, self.projects)

    async def _graph(self, project_id: int) -> Tuple[List[TaskNode], List[DepEdge]]:
        tasks = await self.tasks.all_for_project(project_id)
        deps = await self.dependencies.list_by_project(project_id)
        nodes = [
            TaskNode(id=task.id, start_date=task.start_date, end_date=task.end_date)
            for task in tasks
        ]
        edges = [
            DepEdge(
                predecessor_id=dep.predecessor_id,
                successor_id=dep.successor_id,
                lag_days=dep.lag_days,
                id=dep.id,
            )
            for dep in deps
        ]
        return nodes, edges

    async def _get_task_checked(
        self, task_id: int, user_id: int, required: MemberRole = MemberRole.viewer
    ) -> Tuple[Task, Project]:
        task = await self.tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(details={"task_id": task_id})
        project = await self.access.get_project_for(task.project_id, user_id, required)
        return task, project

    async def _assert_assignee(
        self, project_id: int, assignee_id: Optional[int]
    ) -> None:
        if assignee_id is None:
            return
        project = await self.projects.get(project_id)
        if project is not None and project.owner_id == assignee_id:
            return
        if await self.projects.get_member(project_id, assignee_id) is None:
            raise ValidationError(
                "Ответственный должен быть участником проекта",
                details={"assignee_id": assignee_id},
            )

    async def list_tasks(
        self,
        project_id: int,
        user_id: int,
        filters: TaskFilter,
        limit: int,
        offset: int,
    ) -> Page[TaskRead]:
        await self.access.get_project_for(project_id, user_id)
        rows, total = await self.tasks.list_by_project(
            project_id,
            limit=limit,
            offset=offset,
            statuses=filters.status,
            assignee_id=filters.assignee_id,
            search=filters.search,
            start_from=filters.start_from,
            end_to=filters.end_to,
            order_by=filters.order_by,
            order_dir=filters.order_dir,
        )
        today = date.today()
        items = [task_read(task, assignee, today) for task, assignee in rows]

        if filters.state:
            wanted = set(filters.state)
            items = [item for item in items if item.state in wanted]
            total = len(items)
        return Page.build(items, total, limit, offset)

    async def get_task(self, task_id: int, user_id: int) -> TaskWithLinks:
        task, _ = await self._get_task_checked(task_id, user_id)
        row = await self.tasks.get_with_assignee(task_id)
        assignee = row[1] if row else None
        links = await self.dependencies.list_for_task(task_id)
        base = task_read(task, assignee, date.today())
        return TaskWithLinks(
            **base.model_dump(),
            predecessor_ids=[
                dep.predecessor_id for dep in links if dep.successor_id == task_id
            ],
            successor_ids=[
                dep.successor_id for dep in links if dep.predecessor_id == task_id
            ],
        )

    async def create_task(
        self, project_id: int, user_id: int, data: TaskCreate
    ) -> TaskRead:
        await self.access.get_project_for(project_id, user_id, MemberRole.responsible)
        if data.end_date < data.start_date:
            raise InvalidDateRangeError()
        await self._assert_assignee(project_id, data.assignee_id)

        task = await self.tasks.create(
            project_id=project_id,
            title=data.title.strip(),
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
            assignee_id=data.assignee_id,
            progress_percent=data.progress_percent,
        )

        if data.predecessor_ids:
            await self._link_predecessors(project_id, task.id, data.predecessor_ids)

        await self.session.commit()
        await self.session.refresh(task)
        await cache.invalidate_project(project_id)
        await events.publish(
            project_id, events.TASK_CREATED, {"task_id": task.id}, user_id
        )

        assignee = await self.users.get(task.assignee_id) if task.assignee_id else None
        return task_read(task, assignee, date.today())

    async def _link_predecessors(
        self, project_id: int, task_id: int, predecessor_ids: Sequence[int]
    ) -> None:
        existing_ids = await self.tasks.ids_for_project(project_id)
        _, edges = await self._graph(project_id)
        node_ids = set(existing_ids) | {task_id}

        for predecessor_id in dict.fromkeys(predecessor_ids):
            if predecessor_id == task_id:
                continue
            if predecessor_id not in existing_ids:
                raise ValidationError(
                    "Предшественник должен быть задачей того же проекта",
                    details={"predecessor_id": predecessor_id},
                )
            candidate = DepEdge(predecessor_id=predecessor_id, successor_id=task_id)
            if scheduling.would_create_cycle(node_ids, edges, candidate):
                raise TaskCycleError(
                    details={"predecessor_id": predecessor_id, "successor_id": task_id}
                )
            await self.dependencies.create(
                project_id=project_id,
                predecessor_id=predecessor_id,
                successor_id=task_id,
            )
            edges.append(candidate)

    async def update_task(
        self, task_id: int, user_id: int, data: TaskUpdate
    ) -> Tuple[TaskRead, Optional[ImpactAnalysis]]:
        task, project = await self._get_task_checked(
            task_id, user_id, MemberRole.responsible
        )
        values = data.model_dump(exclude_unset=True, exclude={"cascade"})

        new_start = values.get("start_date", task.start_date)
        new_end = values.get("end_date", task.end_date)
        if new_end < new_start:
            raise InvalidDateRangeError()
        if "assignee_id" in values:
            await self._assert_assignee(task.project_id, values["assignee_id"])
        if "title" in values and values["title"]:
            values["title"] = values["title"].strip()
        if values.get("status") == TaskStatus.done:
            values.setdefault("progress_percent", 100)

        dates_changed = new_start != task.start_date or new_end != task.end_date

        impact: Optional[ImpactAnalysis] = None
        if dates_changed:
            impact = await self._analyse(project, task, new_start, new_end)

        await self.tasks.update(task, values)

        if dates_changed and data.cascade and impact and impact.affected_tasks:
            shifts: Dict[int, Tuple[date, date]] = {
                affected.task_id: (affected.new_start_date, affected.new_end_date)
                for affected in impact.affected_tasks
            }
            await self.tasks.apply_shifts(shifts)
            impact.applied = True

        await self.session.commit()
        await self.session.refresh(task)
        await cache.invalidate_project(task.project_id)
        await events.publish(
            task.project_id,
            (
                events.TASKS_RESCHEDULED
                if (impact and impact.applied)
                else events.TASK_UPDATED
            ),
            {
                "task_id": task.id,
                "affected_task_ids": (
                    [a.task_id for a in impact.affected_tasks] if impact else []
                ),
            },
            user_id,
        )

        assignee = await self.users.get(task.assignee_id) if task.assignee_id else None
        return task_read(task, assignee, date.today()), impact

    async def delete_task(self, task_id: int, user_id: int) -> None:
        task, _ = await self._get_task_checked(task_id, user_id, MemberRole.responsible)
        project_id = task.project_id
        await self.tasks.delete(task)
        await self.session.commit()
        await cache.invalidate_project(project_id)
        await events.publish(
            project_id, events.TASK_DELETED, {"task_id": task_id}, user_id
        )

    async def _analyse(
        self,
        project: Project,
        task: Task,
        new_start: date,
        new_end: date,
        apply_marker: bool = False,
    ) -> ImpactAnalysis:
        nodes, edges = await self._graph(project.id)
        changed = {task.id: (new_start, new_end)}

        shifted = scheduling.cascade_shift(nodes, edges, changed)
        projected = scheduling.projected_finish(nodes, changed, shifted) or new_end

        updated_nodes = self._apply_to_nodes(nodes, changed, shifted)
        schedule = scheduling.compute_schedule(updated_nodes, edges, project.start_date)
        critical = set(schedule.critical_path)

        titles = {
            row.id: row.title for row in await self.tasks.all_for_project(project.id)
        }
        affected = [
            AffectedTask(
                task_id=item.task_id,
                title=titles.get(item.task_id, ""),
                old_start_date=item.old_start,
                old_end_date=item.old_end,
                new_start_date=item.new_start,
                new_end_date=item.new_end,
                shift_days=item.shift_days,
                is_critical=item.task_id in critical,
            )
            for item in shifted
        ]
        overrun = max((projected - project.end_date).days, 0)
        return ImpactAnalysis(
            task_id=task.id,
            affected_tasks=affected,
            affected_count=len(affected),
            project_end_date=project.end_date,
            projected_end_date=projected,
            project_overrun_days=overrun,
            breaks_deadline=overrun > 0,
            applied=apply_marker,
        )

    @staticmethod
    def _apply_to_nodes(
        nodes: Sequence[TaskNode],
        changed: Dict[int, Tuple[date, date]],
        shifted: Sequence[scheduling.ShiftedTask],
    ) -> List[TaskNode]:
        overrides: Dict[int, Tuple[date, date]] = dict(changed)
        for item in shifted:
            overrides[item.task_id] = (item.new_start, item.new_end)
        return [
            TaskNode(
                id=node.id,
                start_date=overrides.get(node.id, (node.start_date, node.end_date))[0],
                end_date=overrides.get(node.id, (node.start_date, node.end_date))[1],
            )
            for node in nodes
        ]

    async def preview_impact(
        self,
        task_id: int,
        user_id: int,
        start_date: Optional[date],
        end_date: Optional[date],
        shift_days: Optional[int],
    ) -> ImpactAnalysis:
        task, project = await self._get_task_checked(task_id, user_id)
        new_start, new_end = self._resolve_dates(task, start_date, end_date, shift_days)
        return await self._analyse(project, task, new_start, new_end)

    async def shift_task(
        self, task_id: int, user_id: int, data: TaskShiftRequest
    ) -> ImpactAnalysis:
        task, project = await self._get_task_checked(
            task_id, user_id, MemberRole.responsible
        )
        new_start, new_end = self._resolve_dates(
            task, data.start_date, data.end_date, data.shift_days
        )
        impact = await self._analyse(project, task, new_start, new_end)

        await self.tasks.update(task, {"start_date": new_start, "end_date": new_end})
        if data.cascade and impact.affected_tasks:
            await self.tasks.apply_shifts(
                {
                    affected.task_id: (affected.new_start_date, affected.new_end_date)
                    for affected in impact.affected_tasks
                }
            )
            impact.applied = True

        await self.session.commit()
        await cache.invalidate_project(project.id)
        await events.publish(
            project.id,
            events.TASKS_RESCHEDULED,
            {
                "task_id": task_id,
                "affected_task_ids": [a.task_id for a in impact.affected_tasks],
            },
            user_id,
        )
        return impact

    @staticmethod
    def _resolve_dates(
        task: Task,
        start_date: Optional[date],
        end_date: Optional[date],
        shift_days: Optional[int],
    ) -> Tuple[date, date]:
        if shift_days is not None:
            delta = timedelta(days=shift_days)
            return task.start_date + delta, task.end_date + delta
        new_start = start_date or task.start_date
        if end_date is not None:
            new_end = end_date
        elif start_date is not None:
            new_end = new_start + timedelta(days=task.duration_days - 1)
        else:
            new_end = task.end_date
        if new_end < new_start:
            raise InvalidDateRangeError()
        return new_start, new_end

    async def my_tasks(
        self, user_id: int, limit: int, offset: int, only_open: bool = True
    ) -> Page[TaskRead]:
        projects, _ = await self.projects.list_for_user(user_id, limit=500, offset=0)
        today = date.today()
        items: List[TaskRead] = []
        tasks = await self.tasks.all_for_projects([project.id for project in projects])
        user = await self.users.get(user_id)
        for task in tasks:
            if task.assignee_id != user_id:
                continue
            if only_open and task.status in (TaskStatus.done, TaskStatus.cancelled):
                continue
            items.append(task_read(task, user, today))
        items.sort(key=lambda item: (item.end_date, item.id))
        total = len(items)
        return Page.build(items[offset : offset + limit], total, limit, offset)
