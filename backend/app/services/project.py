from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidDateRangeError,
    MemberAlreadyExistsError,
    NotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
    ValidationError,
)
from app.models.enums import MemberRole, ProjectStatus, TaskStatus
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.schemas.project import (
    MemberCreate,
    MemberRead,
    ProjectCreate,
    ProjectSummary,
    ProjectUpdate,
)
from app.services import cache
from app.services.access import AccessService
from app.services.mappers import member_read
from app.services.status import weighted_progress
from app.ws import events


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        project_repo: Optional[ProjectRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        user_repo: Optional[UserRepository] = None,
        access: Optional[AccessService] = None,
    ) -> None:
        self.session = session
        self.projects = project_repo or ProjectRepository(session)
        self.tasks = task_repo or TaskRepository(session)
        self.users = user_repo or UserRepository(session)
        self.access = access or AccessService(session, self.projects)

    async def create(self, data: ProjectCreate, owner_id: int) -> Project:
        if data.end_date < data.start_date:
            raise InvalidDateRangeError()
        project = await self.projects.create(
            name=data.name.strip(),
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            owner_id=owner_id,
            status=ProjectStatus.active,
        )
        await self.projects.add_member(project.id, owner_id, MemberRole.owner)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get(self, project_id: int, user_id: int) -> Project:
        return await self.access.get_project_for(project_id, user_id)

    async def update(
        self, project_id: int, user_id: int, data: ProjectUpdate
    ) -> Project:
        project = await self.access.get_project_for(
            project_id, user_id, MemberRole.owner
        )
        values = data.model_dump(exclude_unset=True)
        new_start = values.get("start_date", project.start_date)
        new_end = values.get("end_date", project.end_date)
        if new_end < new_start:
            raise InvalidDateRangeError()
        if "name" in values and values["name"]:
            values["name"] = values["name"].strip()
        await self.projects.update(project, values)
        await self.session.commit()
        await self.session.refresh(project)
        await cache.invalidate_project(project_id)
        await events.publish(
            project_id, events.PROJECT_UPDATED, {"project_id": project_id}, user_id
        )
        return project

    async def delete(self, project_id: int, user_id: int) -> None:
        project = await self.access.get_project_for(
            project_id, user_id, MemberRole.owner
        )
        if project.owner_id != user_id:
            raise PermissionDeniedError("Удалить проект может только владелец")
        await self.projects.delete(project)
        await self.session.commit()
        await cache.invalidate_project(project_id)

    async def list_for_user(
        self, user_id: int, limit: int, offset: int, search: Optional[str] = None
    ) -> Tuple[List[ProjectSummary], int]:
        projects, total = await self.projects.list_for_user(
            user_id, limit, offset, search
        )
        if not projects:
            return [], total

        project_ids = [project.id for project in projects]
        summaries = {project.id: self._empty_summary(project) for project in projects}

        all_tasks = await self.tasks.all_for_projects(project_ids)
        roles = await self.projects.roles_for_user(user_id, project_ids)
        today = date.today()

        grouped: dict = {project_id: [] for project_id in project_ids}
        for task in all_tasks:
            grouped[task.project_id].append(task)

        for project in projects:
            summary = summaries[project.id]
            tasks = grouped.get(project.id, [])
            summary.task_count = len(tasks)
            summary.done_count = sum(
                1 for task in tasks if task.status == TaskStatus.done
            )
            summary.overdue_count = sum(
                1
                for task in tasks
                if task.end_date < today
                and task.status not in (TaskStatus.done, TaskStatus.cancelled)
            )
            summary.progress_percent = weighted_progress(
                (task.duration_days, task.progress_percent, task.status)
                for task in tasks
            )
            summary.my_role = (
                MemberRole.owner
                if project.owner_id == user_id
                else roles.get(project.id)
            )

        return [summaries[project.id] for project in projects], total

    @staticmethod
    def _empty_summary(project: Project) -> ProjectSummary:
        return ProjectSummary(
            id=project.id,
            name=project.name,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            owner_id=project.owner_id,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def list_members(self, project_id: int, user_id: int) -> List[MemberRead]:
        await self.access.get_project_for(project_id, user_id)
        rows = await self.projects.list_members(project_id)
        return [member_read(member, member_user) for member, member_user in rows]

    async def add_member(
        self, project_id: int, user_id: int, data: MemberCreate
    ) -> MemberRead:
        await self.access.get_project_for(project_id, user_id, MemberRole.owner)

        if data.user_id is not None:
            target = await self.users.get(data.user_id)
        else:
            target = await self.users.get_by_email(str(data.email).strip().lower())
        if target is None:
            raise UserNotFoundError(
                details={"user_id": data.user_id, "email": data.email}
            )

        if await self.projects.get_member(project_id, target.id) is not None:
            raise MemberAlreadyExistsError(details={"user_id": target.id})

        member = await self.projects.add_member(project_id, target.id, data.role)
        await self.session.commit()
        await self.session.refresh(member)
        await events.publish(
            project_id, events.MEMBER_ADDED, {"user_id": target.id}, user_id
        )
        return member_read(member, target)

    async def update_member_role(
        self, project_id: int, member_id: int, user_id: int, role: MemberRole
    ) -> MemberRead:
        project = await self.access.get_project_for(
            project_id, user_id, MemberRole.owner
        )
        member = await self.projects.get_member_by_id(member_id)
        if member is None or member.project_id != project_id:
            raise NotFoundError("Участник не найден", details={"member_id": member_id})
        if member.user_id == project.owner_id and role != MemberRole.owner:
            raise ValidationError("Нельзя понизить владельца проекта")
        await self.projects.update(member, {"role": role})
        await self.session.commit()
        target = await self.users.get(member.user_id)
        return member_read(member, target)

    async def remove_member(
        self, project_id: int, member_id: int, user_id: int
    ) -> None:
        project = await self.access.get_project_for(
            project_id, user_id, MemberRole.owner
        )
        member = await self.projects.get_member_by_id(member_id)
        if member is None or member.project_id != project_id:
            raise NotFoundError("Участник не найден", details={"member_id": member_id})
        if member.user_id == project.owner_id:
            raise ValidationError("Нельзя исключить владельца проекта")
        removed_user_id = member.user_id
        await self.projects.delete(member)
        await self.session.commit()
        await events.publish(
            project_id, events.MEMBER_REMOVED, {"user_id": removed_user_id}, user_id
        )

    async def member_user_ids(self, project_id: int) -> List[int]:
        return await self.projects.member_user_ids(project_id)

    async def assert_assignee_allowed(
        self, project_id: int, assignee_id: Optional[int]
    ) -> None:
        if assignee_id is None:
            return
        project = await self.projects.get(project_id)
        if project is not None and project.owner_id == assignee_id:
            return
        if await self.projects.get_member(project_id, assignee_id) is None:
            raise ValidationError(
                "Ответственный должен быть участником проекта",
                details={"assignee_id": assignee_id},
            )
