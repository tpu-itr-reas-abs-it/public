from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import AnalyticsServiceDep, CurrentUser
from app.schemas.gantt import (
    BoardResponse,
    CalendarResponse,
    GanttResponse,
    WorkloadResponse,
)
from app.schemas.stats import CriticalPathResponse, ProjectStats

router = APIRouter(prefix="/projects", tags=["analytics"])


@router.get("/{project_id}/gantt", response_model=GanttResponse)
async def gantt(
    project_id: int, service: AnalyticsServiceDep, current_user: CurrentUser
) -> GanttResponse:
    return await service.gantt(project_id, current_user.id)


@router.get("/{project_id}/critical-path", response_model=CriticalPathResponse)
async def critical_path(
    project_id: int, service: AnalyticsServiceDep, current_user: CurrentUser
) -> CriticalPathResponse:
    return await service.critical_path(project_id, current_user.id)


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def stats(
    project_id: int, service: AnalyticsServiceDep, current_user: CurrentUser
) -> ProjectStats:
    return await service.stats(project_id, current_user.id)


@router.get("/{project_id}/board", response_model=BoardResponse)
async def board(
    project_id: int, service: AnalyticsServiceDep, current_user: CurrentUser
) -> BoardResponse:
    return await service.board(project_id, current_user.id)


@router.get("/{project_id}/calendar", response_model=CalendarResponse)
async def calendar(
    project_id: int,
    service: AnalyticsServiceDep,
    current_user: CurrentUser,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
) -> CalendarResponse:
    return await service.calendar(project_id, current_user.id, date_from, date_to)


@router.get("/{project_id}/workload", response_model=WorkloadResponse)
async def workload(
    project_id: int, service: AnalyticsServiceDep, current_user: CurrentUser
) -> WorkloadResponse:
    return await service.workload(project_id, current_user.id)
