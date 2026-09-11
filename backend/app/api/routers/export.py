from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import CurrentUser, ExportServiceDep

router = APIRouter(prefix="/projects", tags=["export"])


@router.get("/{project_id}/export")
async def export_project(
    project_id: int,
    service: ExportServiceDep,
    current_user: CurrentUser,
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> Response:
    filename, media_type, content = await service.export(
        project_id, current_user.id, format
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
