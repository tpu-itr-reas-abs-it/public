from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import DependencyType
from app.schemas.common import ORMModel


class DependencyCreate(BaseModel):
    predecessor_id: int
    type: DependencyType = DependencyType.finish_to_start
    lag_days: int = Field(default=0, ge=0, le=365)
    reschedule: bool = False


class DependencyRead(ORMModel):
    id: int
    project_id: int
    predecessor_id: int
    successor_id: int
    type: DependencyType
    lag_days: int
    created_at: datetime


class DependencyLink(BaseModel):
    id: int
    source: int
    target: int
    type: DependencyType
    lag_days: int
    is_critical: bool = False
    violated: bool = False
    violation_days: int = 0
    note: Optional[str] = None
