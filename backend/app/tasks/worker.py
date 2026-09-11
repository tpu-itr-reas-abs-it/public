import logging

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.tasks.jobs import scan_overdue_tasks

logging.basicConfig(level=logging.INFO)


async def startup(ctx) -> None:
    logging.getLogger(__name__).info("ARQ worker started")


async def shutdown(ctx) -> None:
    logging.getLogger(__name__).info("ARQ worker stopped")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [scan_overdue_tasks]
    cron_jobs = [
        cron(scan_overdue_tasks, hour=6, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300
