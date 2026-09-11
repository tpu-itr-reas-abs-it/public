from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: int) -> Optional[ModelT]:
        return await self.session.get(self.model, entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, stmt: Optional[Select] = None) -> int:
        base = stmt if stmt is not None else select(self.model)
        subq = base.order_by(None).limit(None).offset(None).subquery()
        result = await self.session.execute(select(func.count()).select_from(subq))
        return int(result.scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    async def create(self, **values: Any) -> ModelT:
        entity = self.model(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ModelT, values: Dict[str, Any]) -> ModelT:
        for key, value in values.items():
            setattr(entity, key, value)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, entity_id: int) -> None:
        await self.session.execute(delete(self.model).where(self.model.id == entity_id))

    async def bulk_add(self, entities: Sequence[ModelT]) -> None:
        self.session.add_all(list(entities))
        await self.session.flush()
