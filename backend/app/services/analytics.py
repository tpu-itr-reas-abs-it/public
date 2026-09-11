from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DerivedTaskState, TaskStatus
from app.models.project import Project
from app.repositories.dependency import DependencyRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.dependency import DependencyLink
from app.schemas.gantt import (
    BoardColumn,
    BoardResponse,
    CalendarDay,
    CalendarResponse,
    GanttBar,
    GanttResponse,
    GanttTimeline,
    WorkloadItem,
    WorkloadResponse,
)
from app.schemas.stats import CriticalPathResponse, ProjectStats, RiskAssessment
from app.services import cache, scheduling
from app.services.access import AccessService
from app.services.mappers import user_public
from app.services.scheduling import DepEdge, ScheduleResult, TaskNode
from app.services.status import derive_state, risk_level, weighted_progress

BOARD_COLUMNS: List[Tuple[DerivedTaskState, str]] = [
    (DerivedTaskState.upcoming, "Предстоят"),
    (DerivedTaskState.in_progress, "Выполняются"),
    (DerivedTaskState.overdue, "Просрочены"),
    (DerivedTaskState.done, "Выполнены"),
    (DerivedTaskState.cancelled, "Отменены"),
]


class AnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        task_repo: Optional[TaskRepository] = None,
        dependency_repo: Optional[DependencyRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
        access: Optional[AccessService] = None,
    ) -> None:
        self.session = session
        self.tasks = task_repo or TaskRepository(session)
        self.dependencies = dependency_repo or DependencyRepository(session)
        self.projects = project_repo or ProjectRepository(session)
        self.access = access or AccessService(session, self.projects)

    async def gantt(self, project_id: int, user_id: int) -> GanttResponse:
        project = await self.access.get_project_for(project_id, user_id)
        key = cache.project_key(project_id, "gantt")
        cached = await cache.get_json(key)
        if cached is not None:
            return GanttResponse.model_validate(cached)

        response = await self._build_gantt(project)
        await cache.set_json(key, response.model_dump(mode="json"))
        return response

    async def _build_gantt(self, project: Project) -> GanttResponse:
        rows = await self.tasks.all_with_assignees(project.id)
        deps = await self.dependencies.list_by_project(project.id)
        today = date.today()

        nodes = [TaskNode(task.id, task.start_date, task.end_date) for task, _ in rows]
        edges = [
            DepEdge(dep.predecessor_id, dep.successor_id, dep.lag_days, dep.id)
            for dep in deps
        ]
        schedule = scheduling.compute_schedule(nodes, edges, project.start_date)
        critical_ids = set(schedule.critical_path)
        critical_pairs = scheduling.critical_edges(schedule, edges)
        violations = {
            (violation.edge.predecessor_id, violation.edge.successor_id): violation
            for violation in scheduling.find_violations(nodes, edges)
        }

        predecessors: Dict[int, List[int]] = {task.id: [] for task, _ in rows}
        successors: Dict[int, List[int]] = {task.id: [] for task, _ in rows}
        for dep in deps:
            successors.setdefault(dep.predecessor_id, []).append(dep.successor_id)
            predecessors.setdefault(dep.successor_id, []).append(dep.predecessor_id)

        bars: List[GanttBar] = []
        for task, assignee in rows:
            item = schedule.tasks.get(task.id)
            bars.append(
                GanttBar(
                    id=task.id,
                    title=task.title,
                    start_date=task.start_date,
                    end_date=task.end_date,
                    duration_days=task.duration_days,
                    status=task.status,
                    state=derive_state(
                        task.status, task.start_date, task.end_date, today
                    ),
                    progress_percent=task.progress_percent,
                    assignee=user_public(assignee),
                    is_critical=task.id in critical_ids,
                    slack_days=item.slack_days if item else 0,
                    earliest_start=item.earliest_start if item else task.start_date,
                    earliest_finish=item.earliest_finish if item else task.end_date,
                    latest_start=item.latest_start if item else task.start_date,
                    latest_finish=item.latest_finish if item else task.end_date,
                    predecessor_ids=sorted(predecessors.get(task.id, [])),
                    successor_ids=sorted(successors.get(task.id, [])),
                    depth=item.depth if item else 0,
                )
            )

        links: List[DependencyLink] = []
        for dep in deps:
            pair = (dep.predecessor_id, dep.successor_id)
            violation = violations.get(pair)
            links.append(
                DependencyLink(
                    id=dep.id,
                    source=dep.predecessor_id,
                    target=dep.successor_id,
                    type=dep.type,
                    lag_days=dep.lag_days,
                    is_critical=pair in critical_pairs,
                    violated=violation is not None,
                    violation_days=violation.days if violation else 0,
                    note=(
                        f"Задача должна начинаться не раньше "
                        f"{violation.required_start.isoformat()}"
                        if violation
                        else None
                    ),
                )
            )

        chart_start = min([project.start_date] + [task.start_date for task, _ in rows])
        chart_end = max([project.end_date] + [task.end_date for task, _ in rows])

        return GanttResponse(
            project_id=project.id,
            project_name=project.name,
            timeline=GanttTimeline(
                project_start=project.start_date,
                project_end=project.end_date,
                chart_start=chart_start,
                chart_end=chart_end,
                total_days=(chart_end - chart_start).days + 1,
                today=today,
            ),
            tasks=bars,
            links=links,
            critical_path=schedule.critical_path,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    async def board(self, project_id: int, user_id: int) -> BoardResponse:
        gantt = await self.gantt(project_id, user_id)
        by_state: Dict[DerivedTaskState, List[int]] = {
            state: [] for state, _ in BOARD_COLUMNS
        }
        for bar in gantt.tasks:
            by_state.setdefault(bar.state, []).append(bar.id)
        return BoardResponse(
            project_id=project_id,
            columns=[
                BoardColumn(
                    state=state,
                    title=title,
                    task_ids=by_state.get(state, []),
                    count=len(by_state.get(state, [])),
                )
                for state, title in BOARD_COLUMNS
            ],
            tasks={bar.id: bar for bar in gantt.tasks},
        )

    async def calendar(
        self,
        project_id: int,
        user_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> CalendarResponse:
        gantt = await self.gantt(project_id, user_id)
        start = date_from or gantt.timeline.chart_start
        end = date_to or gantt.timeline.chart_end
        if end < start:
            start, end = end, start
        end = min(end, start + timedelta(days=365))

        days: List[CalendarDay] = []
        current = start
        while current <= end:
            active = [
                bar.id
                for bar in gantt.tasks
                if bar.start_date <= current <= bar.end_date
            ]
            days.append(
                CalendarDay(
                    day=current,
                    task_ids=active,
                    starting=[
                        bar.id for bar in gantt.tasks if bar.start_date == current
                    ],
                    ending=[bar.id for bar in gantt.tasks if bar.end_date == current],
                )
            )
            current += timedelta(days=1)
        return CalendarResponse(project_id=project_id, days=days)

    async def workload(self, project_id: int, user_id: int) -> WorkloadResponse:
        await self.access.get_project_for(project_id, user_id)
        rows = await self.tasks.all_with_assignees(project_id)
        today = date.today()
        buckets: Dict[Optional[int], WorkloadItem] = {}
        for task, assignee in rows:
            key = task.assignee_id
            if key not in buckets:
                buckets[key] = WorkloadItem(
                    user=user_public(assignee),
                    task_count=0,
                    done_count=0,
                    overdue_count=0,
                    total_days=0,
                )
            item = buckets[key]
            item.task_count += 1
            item.total_days += task.duration_days
            if task.status == TaskStatus.done:
                item.done_count += 1
            elif task.end_date < today and task.status != TaskStatus.cancelled:
                item.overdue_count += 1
        return WorkloadResponse(
            project_id=project_id,
            items=sorted(
                buckets.values(), key=lambda item: item.task_count, reverse=True
            ),
        )

    async def stats(self, project_id: int, user_id: int) -> ProjectStats:
        project = await self.access.get_project_for(project_id, user_id)
        key = cache.project_key(project_id, "stats")
        cached = await cache.get_json(key)
        if cached is not None:
            return ProjectStats.model_validate(cached)

        tasks = await self.tasks.all_for_project(project_id)
        deps = await self.dependencies.list_by_project(project_id)
        today = date.today()

        status_counts = {status: 0 for status in TaskStatus}
        state_counts = {state: 0 for state in DerivedTaskState}
        for task in tasks:
            status_counts[task.status] += 1
            state_counts[
                derive_state(task.status, task.start_date, task.end_date, today)
            ] += 1

        schedule = self._schedule_for(tasks, deps, project.start_date)
        projected_end = schedule.project_finish or project.end_date
        overdue_count = state_counts[DerivedTaskState.overdue]
        overrun = max((projected_end - project.end_date).days, 0)

        reasons: List[str] = []
        if overdue_count:
            reasons.append(f"Просроченных задач: {overdue_count}")
        if overrun > 0:
            reasons.append(
                f"Расчётное окончание {projected_end.isoformat()} позже дедлайна "
                f"{project.end_date.isoformat()} на {overrun} дн."
            )
        if not reasons:
            reasons.append("Проект укладывается в срок")

        stats = ProjectStats(
            project_id=project_id,
            task_count=len(tasks),
            progress_percent=weighted_progress(
                (task.duration_days, task.progress_percent, task.status)
                for task in tasks
            ),
            status_counts=status_counts,
            state_counts=state_counts,
            done_count=status_counts[TaskStatus.done],
            in_progress_count=state_counts[DerivedTaskState.in_progress],
            overdue_count=overdue_count,
            upcoming_count=state_counts[DerivedTaskState.upcoming],
            critical_path_length=len(schedule.critical_path),
            critical_path_days=schedule.critical_path_days,
            days_left=(project.end_date - today).days,
            risk=RiskAssessment(
                level=risk_level(overrun, overdue_count),
                breaks_deadline=overrun > 0,
                projected_end_date=projected_end,
                deadline=project.end_date,
                overrun_days=overrun,
                overdue_task_count=overdue_count,
                reasons=reasons,
            ),
        )
        await cache.set_json(key, stats.model_dump(mode="json"))
        return stats

    async def critical_path(
        self, project_id: int, user_id: int
    ) -> CriticalPathResponse:
        project = await self.access.get_project_for(project_id, user_id)
        tasks = await self.tasks.all_for_project(project_id)
        deps = await self.dependencies.list_by_project(project_id)
        schedule = self._schedule_for(tasks, deps, project.start_date)
        by_id = {task.id: task for task in tasks}
        path = schedule.critical_path
        return CriticalPathResponse(
            project_id=project_id,
            task_ids=path,
            total_days=schedule.critical_path_days,
            start_date=by_id[path[0]].start_date if path else None,
            end_date=by_id[path[-1]].end_date if path else None,
        )

    @staticmethod
    def _schedule_for(tasks, deps, project_start: date) -> ScheduleResult:
        nodes = [TaskNode(task.id, task.start_date, task.end_date) for task in tasks]
        edges = [
            DepEdge(dep.predecessor_id, dep.successor_id, dep.lag_days, dep.id)
            for dep in deps
        ]
        return scheduling.compute_schedule(nodes, edges, project_start)
