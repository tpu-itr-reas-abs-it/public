from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.models.enums import DerivedTaskState, TaskStatus
from app.schemas.dependency import DependencyLink
from app.schemas.user import UserPublic


class GanttBar(BaseModel):
    id: int
    title: str
    start_date: date
    end_date: date
    duration_days: int
    status: TaskStatus
    state: DerivedTaskState
    progress_percent: int
    assignee: Optional[UserPublic] = None
    is_critical: bool = False
    slack_days: int = 0
    earliest_start: date
    earliest_finish: date
    latest_start: date
    latest_finish: date
    predecessor_ids: List[int] = []
    successor_ids: List[int] = []
    depth: int = 0


class GanttTimeline(BaseModel):
    project_start: date
    project_end: date
    chart_start: date
    chart_end: date
    total_days: int
    today: date


class GanttResponse(BaseModel):
    project_id: int
    project_name: str
    timeline: GanttTimeline
    tasks: List[GanttBar]
    links: List[DependencyLink]
    critical_path: List[int]
    generated_at: str


class BoardColumn(BaseModel):
    state: DerivedTaskState
    title: str
    task_ids: List[int]
    count: int


class BoardResponse(BaseModel):
    project_id: int
    columns: List[BoardColumn]
    tasks: Dict[int, GanttBar]


class CalendarDay(BaseModel):
    day: date
    task_ids: List[int]
    starting: List[int]
    ending: List[int]


class CalendarResponse(BaseModel):
    project_id: int
    days: List[CalendarDay]


class WorkloadItem(BaseModel):
    user: Optional[UserPublic]
    task_count: int
    done_count: int
    overdue_count: int
    total_days: int


class WorkloadResponse(BaseModel):
    project_id: int
    items: List[WorkloadItem]
