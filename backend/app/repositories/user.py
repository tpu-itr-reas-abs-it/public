from typing import Iterable, List, Optional, Sequence

from sqlalchemy import or_, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(self, user_ids: Iterable[int]) -> List[User]:
        ids = [uid for uid in set(user_ids) if uid is not None]
        if not ids:
            return []
        result = await self.session.execute(select(User).where(User.id.in_(ids)))
        return list(result.scalars().all())

    async def search(self, query: str, limit: int = 20) -> Sequence[User]:
        pattern = f"%{query.lower()}%"
        stmt = (
            select(User)
            .where(
                or_(
                    User.email.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )
            .order_by(User.full_name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
