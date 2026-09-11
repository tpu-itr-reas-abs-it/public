import enum


class TaskStatus(str, enum.Enum):
    planned = "planned"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class DerivedTaskState(str, enum.Enum):
    upcoming = "upcoming"
    in_progress = "in_progress"
    done = "done"
    overdue = "overdue"
    cancelled = "cancelled"


class ProjectStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    archived = "archived"


class MemberRole(str, enum.Enum):
    owner = "owner"
    responsible = "responsible"
    viewer = "viewer"


class DependencyType(str, enum.Enum):
    finish_to_start = "finish_to_start"


class NotificationType(str, enum.Enum):
    task_overdue = "task_overdue"
    task_assigned = "task_assigned"
    task_due_soon = "task_due_soon"
    project_at_risk = "project_at_risk"
    task_commented = "task_commented"
