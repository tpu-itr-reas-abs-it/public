from typing import List

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DependencyServiceDep
from app.schemas.dependency import DependencyRead

router = APIRouter(tags=["dependencies"])


@router.get("/projects/{project_id}/dependencies", response_model=List[DependencyRead])
async def list_dependencies(
    project_id: int, service: DependencyServiceDep, current_user: CurrentUser
) -> List[DependencyRead]:
    return await service.list_for_project(project_id, current_user.id)


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dependency(
    dependency_id: int, service: DependencyServiceDep, current_user: CurrentUser
) -> Response:
    await service.delete(dependency_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
