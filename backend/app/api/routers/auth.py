from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> TokenPair:
    _, tokens = await service.register(
        payload.email, payload.password, payload.full_name
    )
    return tokens


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenPair:
    _, tokens = await service.login(payload.email, payload.password)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenPair:
    _, tokens = await service.refresh(payload.refresh_token)
    return tokens


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
