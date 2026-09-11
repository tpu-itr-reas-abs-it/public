from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, ProjectNotFoundError
from app.models.enums import MemberRole
from app.models.project import Project
from app.repositories.project import ProjectRepository

ROLE_WEIGHT = {
    MemberRole.viewer: 0,
    MemberRole.responsible: 1,
    MemberRole.owner: 2,
}


class AccessService:
    def __init__(
        self, session: AsyncSession, project_repo: Optional[ProjectRepository] = None
    ) -> None:
        self.session = session
        self.projects = project_repo or ProjectRepository(session)

    async def role_of(self, project: Project, user_id: int) -> Optional[MemberRole]:
        if project.owner_id == user_id:
            return MemberRole.owner
        member = await self.projects.get_member(project.id, user_id)
        return member.role if member else None

    async def get_project_for(
        self, project_id: int, user_id: int, required: MemberRole = MemberRole.viewer
    ) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(details={"project_id": project_id})
        role = await self.role_of(project, user_id)
        if role is None:
            raise ProjectNotFoundError(details={"project_id": project_id})
        if ROLE_WEIGHT[role] < ROLE_WEIGHT[required]:
            raise PermissionDeniedError(
                f"Требуется роль не ниже '{required.value}', текущая — '{role.value}'",
                details={"project_id": project_id, "role": role.value},
            )
        return project

    async def ensure_role(
        self, project: Project, user_id: int, required: MemberRole
    ) -> MemberRole:
        role = await self.role_of(project, user_id)
        if role is None:
            raise ProjectNotFoundError(details={"project_id": project.id})
        if ROLE_WEIGHT[role] < ROLE_WEIGHT[required]:
            raise PermissionDeniedError(
                f"Требуется роль не ниже '{required.value}', текущая — '{role.value}'",
                details={"project_id": project.id, "role": role.value},
            )
        return role
