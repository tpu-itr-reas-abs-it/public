from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Query, Response, status

from app.api.deps import (
    CommentServiceDep,
    CurrentUser,
    DependencyServiceDep,
    Pagination,
    TaskServiceDep,
)
from app.models.enums import DerivedTaskState, TaskStatus
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page
from app.schemas.dependency import DependencyCreate, DependencyRead
from app.schemas.task import (
    ImpactAnalysis,
    TaskCreate,
    TaskFilter,
    TaskRead,
    TaskShiftRequest,
    TaskUpdate,
    TaskWithLinks,
)

project_tasks_router = APIRouter(prefix="/projects", tags=["tasks"])


@project_tasks_router.get("/{project_id}/tasks", response_model=Page[TaskRead])
async def list_tasks(
    project_id: int,
    service: TaskServiceDep,
    current_user: CurrentUser,
    pagination: Pagination,
    status_filter: Optional[List[TaskStatus]] = Query(default=None, alias="status"),
    state: Optional[List[DerivedTaskState]] = Query(default=None),
    assignee_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=255),
    start_from: Optional[date] = Query(default=None),
    end_to: Optional[date] = Query(default=None),
    order_by: str = Query(default="start_date"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> Page[TaskRead]:
    filters = TaskFilter(
        status=status_filter,
        state=state,
        assignee_id=assignee_id,
        search=search,
        start_from=start_from,
        end_to=end_to,
        order_by=order_by,
        order_dir=order_dir,
    )
    return await service.list_tasks(
        project_id, current_user.id, filters, pagination.limit, pagination.offset
    )


@project_tasks_router.post(
    "/{project_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED
)
async def create_task(
    project_id: int,
    payload: TaskCreate,
    service: TaskServiceDep,
    current_user: CurrentUser,
) -> TaskRead:
    return await service.create_task(project_id, current_user.id, payload)


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/me", response_model=Page[TaskRead])
async def my_tasks(
    service: TaskServiceDep,
    current_user: CurrentUser,
    pagination: Pagination,
    only_open: bool = Query(default=True),
) -> Page[TaskRead]:
    return await service.my_tasks(
        current_user.id, pagination.limit, pagination.offset, only_open
    )


@router.get("/{task_id}", response_model=TaskWithLinks)
async def get_task(
    task_id: int, service: TaskServiceDep, current_user: CurrentUser
) -> TaskWithLinks:
    return await service.get_task(task_id, current_user.id)


class TaskUpdateResponse(TaskRead):
    impact: Optional[ImpactAnalysis] = None


@router.patch("/{task_id}", response_model=TaskUpdateResponse)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    service: TaskServiceDep,
    current_user: CurrentUser,
) -> TaskUpdateResponse:
    """Обновление задачи.

    Если сдвинулись сроки — в поле `impact` возвращается разбор последствий:
    какие задачи затронуты и не ломается ли дедлайн проекта. С `cascade=true`
    последователи сдвигаются автоматически.
    """
    task, impact = await service.update_task(task_id, current_user.id, payload)
    return TaskUpdateResponse(**task.model_dump(), impact=impact)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int, service: TaskServiceDep, current_user: CurrentUser
) -> Response:
    await service.delete_task(task_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{task_id}/impact", response_model=ImpactAnalysis)
async def preview_impact(
    task_id: int,
    service: TaskServiceDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    shift_days: Optional[int] = Query(default=None, ge=-3650, le=3650),
) -> ImpactAnalysis:
    """Сухой прогон сдвига: ничего не меняет, показывает последствия."""
    return await service.preview_impact(
        task_id, current_user.id, start_date, end_date, shift_days
    )


@router.post("/{task_id}/shift", response_model=ImpactAnalysis)
async def shift_task(
    task_id: int,
    payload: TaskShiftRequest,
    service: TaskServiceDep,
    current_user: CurrentUser,
) -> ImpactAnalysis:
    return await service.shift_task(task_id, current_user.id, payload)


class DependencyCreateResponse(DependencyRead):
    impact: Optional[ImpactAnalysis] = None


@router.post(
    "/{task_id}/dependencies",
    response_model=DependencyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dependency(
    task_id: int,
    payload: DependencyCreate,
    service: DependencyServiceDep,
    current_user: CurrentUser,
) -> DependencyCreateResponse:
    dependency, impact = await service.create(task_id, current_user.id, payload)
    return DependencyCreateResponse(**dependency.model_dump(), impact=impact)


@router.get("/{task_id}/comments", response_model=Page[CommentRead])
async def list_comments(
    task_id: int,
    service: CommentServiceDep,
    current_user: CurrentUser,
    pagination: Pagination,
) -> Page[CommentRead]:
    return await service.list_for_task(
        task_id, current_user.id, pagination.limit, pagination.offset
    )


@router.post(
    "/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_id: int,
    payload: CommentCreate,
    service: CommentServiceDep,
    current_user: CurrentUser,
) -> CommentRead:
    return await service.create(task_id, current_user.id, payload)
