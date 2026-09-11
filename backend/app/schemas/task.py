from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DerivedTaskState, TaskStatus
from app.schemas.common import ORMModel
from app.schemas.user import UserPublic


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    start_date: date
    end_date: date
    status: TaskStatus = TaskStatus.planned
    assignee_id: Optional[int] = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    predecessor_ids: List[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_dates(self) -> "TaskCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date не может быть раньше start_date")
        return self


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[TaskStatus] = None
    assignee_id: Optional[int] = None
    progress_percent: Optional[int] = Field(default=None, ge=0, le=100)
    cascade: bool = False


class TaskRead(ORMModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    start_date: date
    end_date: date
    duration_days: int
    status: TaskStatus
    state: DerivedTaskState
    is_overdue: bool
    days_overdue: int
    assignee_id: Optional[int]
    assignee: Optional[UserPublic] = None
    progress_percent: int
    created_at: datetime
    updated_at: datetime


class TaskWithLinks(TaskRead):
    predecessor_ids: List[int] = []
    successor_ids: List[int] = []


class TaskFilter(BaseModel):
    status: Optional[List[TaskStatus]] = None
    state: Optional[List[DerivedTaskState]] = None
    assignee_id: Optional[int] = None
    search: Optional[str] = Field(default=None, max_length=255)
    start_from: Optional[date] = None
    end_to: Optional[date] = None
    order_by: str = Field(default="start_date")
    order_dir: str = Field(default="asc")


class TaskShiftRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    shift_days: Optional[int] = None
    cascade: bool = True

    @model_validator(mode="after")
    def check_payload(self) -> "TaskShiftRequest":
        if (
            self.shift_days is None
            and self.start_date is None
            and self.end_date is None
        ):
            raise ValueError("нужно указать shift_days либо start_date/end_date")
        if self.shift_days is not None and (self.start_date or self.end_date):
            raise ValueError("shift_days нельзя сочетать с явными датами")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date не может быть раньше start_date")
        return self


class AffectedTask(BaseModel):
    task_id: int
    title: str
    old_start_date: date
    old_end_date: date
    new_start_date: date
    new_end_date: date
    shift_days: int
    is_critical: bool = False


class ImpactAnalysis(BaseModel):
    task_id: int
    affected_tasks: List[AffectedTask]
    affected_count: int
    project_end_date: date
    projected_end_date: date
    project_overrun_days: int
    breaks_deadline: bool
    applied: bool = False
