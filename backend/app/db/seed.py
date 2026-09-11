import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import MemberRole, ProjectStatus, TaskStatus
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskDependency
from app.models.user import User

DEMO_PROJECT_NAME = "Запуск мобильного приложения"

DEMO_USERS = [
    ("owner@demo.ru", "Иван Петров", "demo12345"),
    ("analyst@demo.ru", "Мария Шишкина", "demo12345"),
    ("dev@demo.ru", "Алексей Абстрактный", "demo12345"),
    ("qa@demo.ru", "Ольга Ромашкина", "demo12345"),
]


async def seed() -> None:
    async with SessionLocal() as session:
        existing = await session.execute(
            select(Project).where(Project.name == DEMO_PROJECT_NAME)
        )
        if existing.scalars().first() is not None:
            print("Демо-проект уже существует")
            return

        users = []
        for email, full_name, password in DEMO_USERS:
            found = await session.execute(select(User).where(User.email == email))
            user = found.scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    full_name=full_name,
                    hashed_password=hash_password(password),
                )
                session.add(user)
            users.append(user)
        await session.flush()

        owner, analyst, developer, tester = users
        today = date.today()
        start = today - timedelta(days=21)

        project = Project(
            name=DEMO_PROJECT_NAME,
            description="Демо-проект",
            start_date=start,
            end_date=start + timedelta(days=60),
            owner_id=owner.id,
            status=ProjectStatus.active,
        )
        session.add(project)
        await session.flush()

        session.add_all(
            [
                ProjectMember(
                    project_id=project.id, user_id=owner.id, role=MemberRole.owner
                ),
                ProjectMember(
                    project_id=project.id,
                    user_id=analyst.id,
                    role=MemberRole.responsible,
                ),
                ProjectMember(
                    project_id=project.id,
                    user_id=developer.id,
                    role=MemberRole.responsible,
                ),
                ProjectMember(
                    project_id=project.id, user_id=tester.id, role=MemberRole.viewer
                ),
            ]
        )

        def make(
            title: str,
            offset: int,
            duration: int,
            status: TaskStatus,
            assignee: User,
            progress: int,
            description: str = "",
        ) -> Task:
            return Task(
                project_id=project.id,
                title=title,
                description=description,
                start_date=start + timedelta(days=offset),
                end_date=start + timedelta(days=offset + duration - 1),
                status=status,
                assignee_id=assignee.id,
                progress_percent=progress,
            )

        analysis = make(
            "Анализ требований",
            0,
            7,
            TaskStatus.done,
            analyst,
            100,
            "Сбор и формализация требований заказчика",
        )
        design = make(
            "Дизайн",
            7,
            10,
            TaskStatus.done,
            analyst,
            100,
            "Макеты экранов и дизайн-система",
        )
        backend = make(
            "Разработка backend", 17, 14, TaskStatus.in_progress, developer, 60
        )
        frontend = make(
            "Разработка frontend", 17, 12, TaskStatus.in_progress, developer, 40
        )
        integration = make(
            "Интеграция с платёжным шлюзом",
            14,
            (today - (start + timedelta(days=14))).days,
            TaskStatus.in_progress,
            developer,
            30,
            "Задача с истёкшим сроком",
        )
        integration.end_date = today - timedelta(days=2)
        testing = make("Тестирование", 31, 10, TaskStatus.planned, tester, 0)
        release = make("Релиз в сторы", 41, 3, TaskStatus.planned, owner, 0)

        tasks = [analysis, design, backend, frontend, integration, testing, release]
        session.add_all(tasks)
        await session.flush()

        links = [
            (analysis, design),
            (design, backend),
            (design, frontend),
            (backend, testing),
            (frontend, testing),
            (integration, testing),
            (testing, release),
        ]
        session.add_all(
            [
                TaskDependency(
                    project_id=project.id,
                    predecessor_id=predecessor.id,
                    successor_id=successor.id,
                )
                for predecessor, successor in links
            ]
        )

        await session.commit()
        print(f"Демо-проект создан: id={project.id}, задач: {len(tasks)}")
        print(f"Вход: {DEMO_USERS[0][0]} / {DEMO_USERS[0][2]}")


if __name__ == "__main__":
    asyncio.run(seed())
