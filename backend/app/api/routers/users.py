from typing import List

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.repositories.user import UserRepository
from app.schemas.user import UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserPublic])
async def search_users(
    session: SessionDep,
    current_user: CurrentUser,
    q: str = Query(min_length=1, max_length=255, description="email или имя"),
    limit: int = Query(default=20, ge=1, le=50),
) -> List[UserPublic]:
    users = await UserRepository(session).search(q, limit)
    return [UserPublic.model_validate(user) for user in users]
