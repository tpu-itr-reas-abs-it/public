from typing import Any, Dict, Generic, List, Optional, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def build(
        cls, items: Sequence[T], total: int, limit: int, offset: int
    ) -> "Page[T]":
        return cls(items=list(items), total=total, limit=limit, offset=offset)


class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorPayload


class MessageResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None
