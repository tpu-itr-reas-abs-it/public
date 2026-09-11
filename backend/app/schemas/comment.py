from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.user import UserPublic


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class CommentRead(ORMModel):
    id: int
    task_id: int
    user_id: int
    text: str
    created_at: datetime
    author: UserPublic | None = None
