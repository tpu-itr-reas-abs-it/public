from datetime import date
from typing import Iterable, Optional, Tuple

from app.models.enums import DerivedTaskState, TaskStatus


def derive_state(
    status: TaskStatus, start_date: date, end_date: date, today: date
) -> DerivedTaskState:
    if status == TaskStatus.done:
        return DerivedTaskState.done
    if status == TaskStatus.cancelled:
        return DerivedTaskState.cancelled
    if end_date < today:
        return DerivedTaskState.overdue
    if start_date > today:
        return DerivedTaskState.upcoming
    return DerivedTaskState.in_progress


def overdue_info(status: TaskStatus, end_date: date, today: date) -> Tuple[bool, int]:
    if status in (TaskStatus.done, TaskStatus.cancelled):
        return False, 0
    if end_date < today:
        return True, (today - end_date).days
    return False, 0


def is_due_soon(
    status: TaskStatus, end_date: date, today: date, horizon_days: int = 3
) -> bool:
    if status in (TaskStatus.done, TaskStatus.cancelled):
        return False
    delta = (end_date - today).days
    return 0 <= delta <= horizon_days


def weighted_progress(items: Iterable[Tuple[int, int, TaskStatus]]) -> int:
    total_weight = 0
    done_weight = 0.0
    for duration_days, progress_percent, status in items:
        if status == TaskStatus.cancelled:
            continue
        weight = max(duration_days, 1)
        effective = 100 if status == TaskStatus.done else progress_percent
        total_weight += weight
        done_weight += weight * effective / 100.0
    if total_weight == 0:
        return 0
    return int(round(done_weight / total_weight * 100))


def risk_level(overrun_days: int, overdue_count: int) -> str:
    if overrun_days > 0:
        return "critical"
    if overdue_count > 0:
        return "warning"
    return "ok"


def clamp_progress(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    return max(0, min(100, value))
