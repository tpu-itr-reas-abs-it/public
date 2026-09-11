from datetime import datetime

from pydantic import EmailStr

from app.schemas.common import ORMModel


class UserPublic(ORMModel):
    id: int
    email: EmailStr
    full_name: str


class UserRead(UserPublic):
    is_active: bool
    created_at: datetime
