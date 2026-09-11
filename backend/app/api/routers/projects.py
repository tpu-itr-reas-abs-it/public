from typing import List, Optional

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, Pagination, ProjectServiceDep
from app.schemas.common import Page
from app.schemas.project import (
    MemberCreate,
    MemberRead,
    MemberUpdate,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectSummary,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectSummary])
async def list_projects(
    service: ProjectServiceDep,
    current_user: CurrentUser,
    pagination: Pagination,
    search: Optional[str] = Query(default=None, max_length=255),
) -> Page[ProjectSummary]:
    items, total = await service.list_for_user(
        current_user.id, pagination.limit, pagination.offset, search
    )
    return Page.build(items, total, pagination.limit, pagination.offset)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, service: ProjectServiceDep, current_user: CurrentUser
) -> ProjectRead:
    project = await service.create(payload, current_user.id)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int, service: ProjectServiceDep, current_user: CurrentUser
) -> ProjectDetail:
    project = await service.get(project_id, current_user.id)
    members = await service.list_members(project_id, current_user.id)
    return ProjectDetail(
        **ProjectRead.model_validate(project).model_dump(), members=members
    )


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    service: ProjectServiceDep,
    current_user: CurrentUser,
) -> ProjectRead:
    project = await service.update(project_id, current_user.id, payload)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int, service: ProjectServiceDep, current_user: CurrentUser
) -> Response:
    await service.delete(project_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/members", response_model=List[MemberRead])
async def list_members(
    project_id: int, service: ProjectServiceDep, current_user: CurrentUser
) -> List[MemberRead]:
    return await service.list_members(project_id, current_user.id)


@router.post(
    "/{project_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    project_id: int,
    payload: MemberCreate,
    service: ProjectServiceDep,
    current_user: CurrentUser,
) -> MemberRead:
    return await service.add_member(project_id, current_user.id, payload)


@router.patch("/{project_id}/members/{member_id}", response_model=MemberRead)
async def update_member(
    project_id: int,
    member_id: int,
    payload: MemberUpdate,
    service: ProjectServiceDep,
    current_user: CurrentUser,
) -> MemberRead:
    return await service.update_member_role(
        project_id, member_id, current_user.id, payload.role
    )


@router.delete(
    "/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    project_id: int,
    member_id: int,
    service: ProjectServiceDep,
    current_user: CurrentUser,
) -> Response:
    await service.remove_member(project_id, member_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
