from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.models.enums import DerivedTaskState, TaskStatus


class RiskAssessment(BaseModel):
    level: str  # ok | warning | critical
    breaks_deadline: bool
    projected_end_date: date
    deadline: date
    overrun_days: int
    overdue_task_count: int
    reasons: List[str] = []


class ProjectStats(BaseModel):
    project_id: int
    task_count: int
    progress_percent: int
    status_counts: Dict[TaskStatus, int]
    state_counts: Dict[DerivedTaskState, int]
    done_count: int
    in_progress_count: int
    overdue_count: int
    upcoming_count: int
    critical_path_length: int
    critical_path_days: int
    days_left: int
    risk: RiskAssessment


class CriticalPathResponse(BaseModel):
    project_id: int
    task_ids: List[int]
    total_days: int
    start_date: Optional[date]
    end_date: Optional[date]
