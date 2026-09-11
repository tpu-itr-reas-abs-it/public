from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.enums import NotificationType
from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    user_id: int
    project_id: Optional[int]
    task_id: Optional[int]
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime


class NotificationMarkRead(BaseModel):
    ids: Optional[List[int]] = None
