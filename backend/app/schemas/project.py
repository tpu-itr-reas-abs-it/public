from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import MemberRole, ProjectStatus
from app.schemas.common import ORMModel
from app.schemas.user import UserPublic


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_dates(self) -> "ProjectCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date не может быть раньше start_date")
        return self


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None


class ProjectRead(ORMModel):
    id: int
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    owner_id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectSummary(ProjectRead):
    task_count: int = 0
    done_count: int = 0
    overdue_count: int = 0
    progress_percent: int = 0
    my_role: Optional[MemberRole] = None


class MemberCreate(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: MemberRole = MemberRole.responsible

    @model_validator(mode="after")
    def check_identity(self) -> "MemberCreate":
        if self.user_id is None and not self.email:
            raise ValueError("нужно указать user_id или email")
        return self


class MemberUpdate(BaseModel):
    role: MemberRole


class MemberRead(ORMModel):
    id: int
    project_id: int
    user_id: int
    role: MemberRole
    created_at: datetime
    user: Optional[UserPublic] = None


class ProjectDetail(ProjectRead):
    members: List[MemberRead] = []
