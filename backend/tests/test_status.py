from datetime import date

from app.models.enums import DerivedTaskState, TaskStatus
from app.services.status import (
    derive_state,
    overdue_info,
    risk_level,
    weighted_progress,
)

TODAY = date(2026, 6, 15)


def test_finished_task_is_never_overdue():
    state = derive_state(TaskStatus.done, date(2026, 5, 1), date(2026, 6, 1), TODAY)
    assert state is DerivedTaskState.done
    assert overdue_info(TaskStatus.done, date(2026, 6, 1), TODAY) == (False, 0)


def test_expired_open_task_is_overdue():
    state = derive_state(
        TaskStatus.in_progress, date(2026, 5, 1), date(2026, 6, 10), TODAY
    )
    assert state is DerivedTaskState.overdue
    assert overdue_info(TaskStatus.in_progress, date(2026, 6, 10), TODAY) == (True, 5)


def test_future_task_is_upcoming():
    state = derive_state(TaskStatus.planned, date(2026, 7, 1), date(2026, 7, 10), TODAY)
    assert state is DerivedTaskState.upcoming


def test_task_inside_its_window_is_in_progress():
    state = derive_state(
        TaskStatus.planned, date(2026, 6, 10), date(2026, 6, 20), TODAY
    )
    assert state is DerivedTaskState.in_progress


def test_cancelled_task_keeps_its_own_state():
    state = derive_state(
        TaskStatus.cancelled, date(2026, 5, 1), date(2026, 6, 1), TODAY
    )
    assert state is DerivedTaskState.cancelled


def test_progress_is_weighted_by_duration():
    items = [(10, 100, TaskStatus.done), (2, 0, TaskStatus.planned)]
    assert weighted_progress(items) == 83


def test_done_task_counts_as_100_percent_regardless_of_field():
    assert weighted_progress([(5, 20, TaskStatus.done)]) == 100


def test_cancelled_tasks_are_excluded_from_progress():
    items = [(5, 100, TaskStatus.done), (5, 0, TaskStatus.cancelled)]
    assert weighted_progress(items) == 100


def test_empty_project_has_zero_progress():
    assert weighted_progress([]) == 0


def test_risk_levels():
    assert risk_level(0, 0) == "ok"
    assert risk_level(0, 3) == "warning"
    assert risk_level(4, 0) == "critical"
