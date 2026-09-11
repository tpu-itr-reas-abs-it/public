import logging
from datetime import date
from typing import Any, Dict

from app.db.session import SessionLocal
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


async def scan_overdue_tasks(ctx: Dict[str, Any]) -> int:
    async with SessionLocal() as session:
        created = await NotificationService(session).scan_overdue(date.today())
    logger.info("overdue scan finished, notifications created: %s", created)
    return created
