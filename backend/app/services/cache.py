import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

KEY_PREFIX = "puc"


def project_key(project_id: int, name: str) -> str:
    return f"{KEY_PREFIX}:project:{project_id}:{name}"


def project_pattern(project_id: int) -> str:
    return f"{KEY_PREFIX}:project:{project_id}:*"


async def get_json(key: str) -> Optional[Any]:
    try:
        raw = await get_redis().get(key)
    except Exception as exc:
        logger.warning("cache get failed for %s: %s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_json(key: str, value: Any, ttl: Optional[int] = None) -> None:
    try:
        await get_redis().set(
            key,
            json.dumps(value, ensure_ascii=False, default=str),
            ex=ttl or settings.cache_ttl_seconds,
        )
    except Exception as exc:
        logger.warning("cache set failed for %s: %s", key, exc)


async def invalidate_project(project_id: int) -> None:
    pattern = project_pattern(project_id)
    try:
        redis = get_redis()
        async for key in redis.scan_iter(match=pattern, count=100):
            await redis.delete(key)
    except Exception as exc:
        logger.warning("cache invalidation failed for %s: %s", pattern, exc)
