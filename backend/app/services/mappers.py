from datetime import date
from typing import Optional

from app.models.comment import Comment
from app.models.notification import Notification
from app.models.project import ProjectMember
from app.models.task import Task, TaskDependency
from app.models.user import User
from app.schemas.comment import CommentRead
from app.schemas.dependency import DependencyRead
from app.schemas.notification import NotificationRead
from app.schemas.project import MemberRead
from app.schemas.task import TaskRead
from app.schemas.user import UserPublic
from app.services.status import derive_state, overdue_info


def user_public(user: Optional[User]) -> Optional[UserPublic]:
    if user is None:
        return None
    return UserPublic(id=user.id, email=user.email, full_name=user.full_name)


def task_read(task: Task, assignee: Optional[User], today: date) -> TaskRead:
    is_overdue, days_overdue = overdue_info(task.status, task.end_date, today)
    return TaskRead(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        start_date=task.start_date,
        end_date=task.end_date,
        duration_days=task.duration_days,
        status=task.status,
        state=derive_state(task.status, task.start_date, task.end_date, today),
        is_overdue=is_overdue,
        days_overdue=days_overdue,
        assignee_id=task.assignee_id,
        assignee=user_public(assignee),
        progress_percent=task.progress_percent,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def dependency_read(dependency: TaskDependency) -> DependencyRead:
    return DependencyRead.model_validate(dependency)


def member_read(member: ProjectMember, user: Optional[User]) -> MemberRead:
    return MemberRead(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        role=member.role,
        created_at=member.created_at,
        user=user_public(user),
    )


def comment_read(comment: Comment, author: Optional[User]) -> CommentRead:
    return CommentRead(
        id=comment.id,
        task_id=comment.task_id,
        user_id=comment.user_id,
        text=comment.text,
        created_at=comment.created_at,
        author=user_public(author),
    )


def notification_read(notification: Notification) -> NotificationRead:
    return NotificationRead.model_validate(notification)
