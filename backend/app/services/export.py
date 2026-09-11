import csv
import io
import json
from datetime import date
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.repositories.comment import CommentRepository
from app.repositories.dependency import DependencyRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.services.access import AccessService
from app.services.analytics import AnalyticsService
from app.services.mappers import user_public

SUPPORTED_FORMATS = ("json", "csv")

CSV_HEADERS = [
    "id",
    "title",
    "description",
    "start_date",
    "end_date",
    "duration_days",
    "status",
    "state",
    "progress_percent",
    "assignee",
    "is_critical",
    "slack_days",
    "predecessors",
]


class ExportService:
    def __init__(
        self,
        session: AsyncSession,
        analytics: Optional[AnalyticsService] = None,
        project_repo: Optional[ProjectRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        dependency_repo: Optional[DependencyRepository] = None,
        comment_repo: Optional[CommentRepository] = None,
        access: Optional[AccessService] = None,
    ) -> None:
        self.session = session
        self.projects = project_repo or ProjectRepository(session)
        self.tasks = task_repo or TaskRepository(session)
        self.dependencies = dependency_repo or DependencyRepository(session)
        self.comments = comment_repo or CommentRepository(session)
        self.access = access or AccessService(session, self.projects)
        self.analytics = analytics or AnalyticsService(
            session, self.tasks, self.dependencies, self.projects, self.access
        )

    async def export(
        self, project_id: int, user_id: int, fmt: str = "json"
    ) -> Tuple[str, str, str]:
        fmt = fmt.lower()
        if fmt not in SUPPORTED_FORMATS:
            raise ValidationError(
                f"Поддерживаемые форматы: {', '.join(SUPPORTED_FORMATS)}",
                details={"format": fmt},
            )
        project = await self.access.get_project_for(project_id, user_id)
        gantt = await self.analytics.gantt(project_id, user_id)
        stats = await self.analytics.stats(project_id, user_id)
        slug = f"project-{project_id}-{date.today().isoformat()}"

        if fmt == "csv":
            return f"{slug}.csv", "text/csv; charset=utf-8", self._to_csv(gantt)

        members = await self.projects.list_members(project_id)
        payload = {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "start_date": project.start_date.isoformat(),
                "end_date": project.end_date.isoformat(),
                "status": project.status.value,
                "owner_id": project.owner_id,
            },
            "members": [
                {
                    "user": user_public(user).model_dump() if user else None,
                    "role": member.role.value,
                }
                for member, user in members
            ],
            "tasks": [bar.model_dump(mode="json") for bar in gantt.tasks],
            "dependencies": [link.model_dump(mode="json") for link in gantt.links],
            "critical_path": gantt.critical_path,
            "stats": stats.model_dump(mode="json"),
            "exported_at": gantt.generated_at,
        }
        return (
            f"{slug}.json",
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

    @staticmethod
    def _to_csv(gantt) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(CSV_HEADERS)
        for bar in gantt.tasks:
            writer.writerow(
                [
                    bar.id,
                    bar.title,
                    "",
                    bar.start_date.isoformat(),
                    bar.end_date.isoformat(),
                    bar.duration_days,
                    bar.status.value,
                    bar.state.value,
                    bar.progress_percent,
                    bar.assignee.full_name if bar.assignee else "",
                    "да" if bar.is_critical else "нет",
                    bar.slack_days,
                    ",".join(str(pid) for pid in bar.predecessor_ids),
                ]
            )
        # чтобы Excel корректно открыл кириллицу
        return "﻿" + buffer.getvalue()
