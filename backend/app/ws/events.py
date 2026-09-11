import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "puc:events:project:"
CHANNEL_PATTERN = f"{CHANNEL_PREFIX}*"


TASK_CREATED = "task.created"
TASK_UPDATED = "task.updated"
TASK_DELETED = "task.deleted"
TASKS_RESCHEDULED = "tasks.rescheduled"
DEPENDENCY_CREATED = "dependency.created"
DEPENDENCY_DELETED = "dependency.deleted"
PROJECT_UPDATED = "project.updated"
MEMBER_ADDED = "member.added"
MEMBER_REMOVED = "member.removed"
COMMENT_CREATED = "comment.created"
NOTIFICATION_CREATED = "notification.created"


def channel_for(project_id: int) -> str:
    return f"{CHANNEL_PREFIX}{project_id}"


def project_id_from_channel(channel: str) -> Optional[int]:
    if not channel.startswith(CHANNEL_PREFIX):
        return None
    try:
        return int(channel[len(CHANNEL_PREFIX) :])
    except ValueError:
        return None


async def publish(
    project_id: int,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    actor_id: Optional[int] = None,
) -> None:
    message = {
        "type": event_type,
        "project_id": project_id,
        "actor_id": actor_id,
        "payload": payload or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await get_redis().publish(
            channel_for(project_id),
            json.dumps(message, ensure_ascii=False, default=str),
        )
    except Exception as exc:
        logger.warning("event publish failed (%s): %s", event_type, exc)
