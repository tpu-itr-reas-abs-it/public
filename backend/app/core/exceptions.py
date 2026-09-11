from typing import Any, Dict, Optional


class DomainError(Exception):
    code: str = "domain_error"
    status_code: int = 400
    message: str = "Domain error"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404
    message = "Resource not found"


class UserNotFoundError(NotFoundError):
    code = "user_not_found"
    message = "Пользователь не найден"


class ProjectNotFoundError(NotFoundError):
    code = "project_not_found"
    message = "Проект не найден"


class TaskNotFoundError(NotFoundError):
    code = "task_not_found"
    message = "Задача не найдена"


class DependencyNotFoundError(NotFoundError):
    code = "dependency_not_found"
    message = "Зависимость не найдена"


class CommentNotFoundError(NotFoundError):
    code = "comment_not_found"
    message = "Комментарий не найден"


class NotificationNotFoundError(NotFoundError):
    code = "notification_not_found"
    message = "Уведомление не найдено"


class AuthenticationError(DomainError):
    code = "authentication_error"
    status_code = 401
    message = "Неверный email или пароль"


class InvalidTokenError(DomainError):
    code = "invalid_token"
    status_code = 401
    message = "Токен недействителен или истёк"


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = 403
    message = "Недостаточно прав для выполнения операции"


class ConflictError(DomainError):
    code = "conflict"
    status_code = 409
    message = "Конфликт состояния"


class EmailAlreadyExistsError(ConflictError):
    code = "email_already_exists"
    message = "Пользователь с таким email уже существует"


class MemberAlreadyExistsError(ConflictError):
    code = "member_already_exists"
    message = "Пользователь уже участник проекта"


class DependencyAlreadyExistsError(ConflictError):
    code = "dependency_already_exists"
    message = "Такая зависимость уже существует"


class TaskCycleError(ConflictError):
    code = "task_cycle"
    message = "Зависимость создаёт цикл в графе задач"


class ValidationError(DomainError):
    code = "validation_error"
    status_code = 422
    message = "Некорректные данные"


class InvalidDateRangeError(ValidationError):
    code = "invalid_date_range"
    message = "Дата окончания не может быть раньше даты начала"


class CrossProjectDependencyError(ValidationError):
    code = "cross_project_dependency"
    message = "Зависимость возможна только между задачами одного проекта"


class SelfDependencyError(ValidationError):
    code = "self_dependency"
    message = "Задача не может зависеть сама от себя"
