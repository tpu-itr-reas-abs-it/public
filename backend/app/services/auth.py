from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationError,
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair


class AuthService:
    def __init__(
        self, session: AsyncSession, user_repo: Optional[UserRepository] = None
    ) -> None:
        self.session = session
        self.users = user_repo or UserRepository(session)

    @staticmethod
    def _issue(user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def register(
        self, email: str, password: str, full_name: str
    ) -> Tuple[User, TokenPair]:
        normalized = email.strip().lower()
        if await self.users.get_by_email(normalized) is not None:
            raise EmailAlreadyExistsError(details={"email": normalized})
        user = await self.users.create(
            email=normalized,
            hashed_password=hash_password(password),
            full_name=full_name.strip(),
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user, self._issue(user)

    async def login(self, email: str, password: str) -> Tuple[User, TokenPair]:
        user = await self.users.get_by_email(email.strip().lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError()
        if not user.is_active:
            raise AuthenticationError("Учётная запись отключена")
        return user, self._issue(user)

    async def refresh(self, refresh_token: str) -> Tuple[User, TokenPair]:
        user_id = decode_token(refresh_token, "refresh")
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Пользователь недоступен")
        return user, self._issue(user)

    async def get_user(self, user_id: int) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise UserNotFoundError(details={"user_id": user_id})
        return user
