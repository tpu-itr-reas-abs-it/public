from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, NotificationServiceDep, Pagination
from app.schemas.common import MessageResponse, Page
from app.schemas.notification import NotificationMarkRead, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    service: NotificationServiceDep,
    current_user: CurrentUser,
    pagination: Pagination,
    only_unread: bool = Query(default=False),
) -> Page[NotificationRead]:
    return await service.list_for_user(
        current_user.id, pagination.limit, pagination.offset, only_unread
    )


@router.get("/unread-count", response_model=MessageResponse)
async def unread_count(
    service: NotificationServiceDep, current_user: CurrentUser
) -> MessageResponse:
    count = await service.unread_count(current_user.id)
    return MessageResponse(message="ok", data={"unread": count})


@router.post("/read", response_model=MessageResponse)
async def mark_read(
    payload: NotificationMarkRead,
    service: NotificationServiceDep,
    current_user: CurrentUser,
) -> MessageResponse:
    updated = await service.mark_read(current_user.id, payload.ids)
    return MessageResponse(message="ok", data={"updated": updated})
