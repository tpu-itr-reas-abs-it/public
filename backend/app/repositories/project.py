from typing import List, Optional, Sequence, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models.enums import MemberRole
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def _visible_stmt(self, user_id: int):
        return (
            select(Project)
            .outerjoin(
                ProjectMember,
                (ProjectMember.project_id == Project.id)
                & (ProjectMember.user_id == user_id),
            )
            .where(or_(Project.owner_id == user_id, ProjectMember.id.is_not(None)))
            .distinct()
        )

    async def list_for_user(
        self, user_id: int, limit: int, offset: int, search: Optional[str] = None
    ) -> Tuple[List[Project], int]:
        stmt = self._visible_stmt(user_id)
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(Project.name.ilike(pattern), Project.description.ilike(pattern))
            )
        total = await self.count(stmt)
        stmt = stmt.order_by(Project.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_visible(self, project_id: int, user_id: int) -> Optional[Project]:
        stmt = self._visible_stmt(user_id).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_member(
        self, project_id: int, user_id: int
    ) -> Optional[ProjectMember]:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_by_id(self, member_id: int) -> Optional[ProjectMember]:
        return await self.session.get(ProjectMember, member_id)

    async def list_members(
        self, project_id: int
    ) -> Sequence[Tuple[ProjectMember, User]]:
        stmt = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at)
        )
        result = await self.session.execute(stmt)
        return [(member, user) for member, user in result.all()]

    async def member_user_ids(self, project_id: int) -> List[int]:
        stmt = select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def roles_for_user(self, user_id: int, project_ids: Sequence[int]) -> dict:
        if not project_ids:
            return {}
        stmt = select(ProjectMember.project_id, ProjectMember.role).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id.in_(list(project_ids)),
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def add_member(
        self, project_id: int, user_id: int, role: MemberRole
    ) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def load_with_members(self, project_id: int) -> Optional[Project]:
        stmt = (
            select(Project)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
            .where(Project.id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
