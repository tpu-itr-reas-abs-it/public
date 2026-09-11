from fastapi import APIRouter

from app.api.routers import (
    analytics,
    auth,
    dependencies,
    export,
    health,
    notifications,
    projects,
    tasks,
    users,
    ws,
)


def build_api_router() -> APIRouter:
    api = APIRouter()
    api.include_router(auth.router)
    api.include_router(users.router)
    api.include_router(projects.router)
    api.include_router(tasks.project_tasks_router)
    api.include_router(tasks.router)
    api.include_router(dependencies.router)
    api.include_router(analytics.router)
    api.include_router(export.router)
    api.include_router(notifications.router)
    api.include_router(ws.router)
    return api


__all__ = ["build_api_router", "health"]
