import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import WebSocket

from app.core.redis import get_redis
from app.ws import events

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._listener: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._listener is None or self._listener.done():
            self._listener = asyncio.create_task(
                self._listen(), name="ws-redis-listener"
            )

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            try:
                await self._listener
            except (asyncio.CancelledError, Exception):
                pass
            self._listener = None

    async def _listen(self) -> None:
        while True:
            try:
                pubsub = get_redis().pubsub()
                await pubsub.psubscribe(events.CHANNEL_PATTERN)
                logger.info("WS listener subscribed to %s", events.CHANNEL_PATTERN)
                async for message in pubsub.listen():
                    if message.get("type") != "pmessage":
                        continue
                    project_id = events.project_id_from_channel(message["channel"])
                    if project_id is None:
                        continue
                    try:
                        payload = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue
                    await self._fan_out(project_id, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("WS listener error, retry in 3s: %s", exc)
                await asyncio.sleep(3)

    async def connect(self, project_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[project_id].add(websocket)
        await self.start()

    async def disconnect(self, project_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[project_id].discard(websocket)
            if not self._connections[project_id]:
                self._connections.pop(project_id, None)

    async def _fan_out(self, project_id: int, payload: dict) -> None:
        async with self._lock:
            targets = list(self._connections.get(project_id, ()))
        dead = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            await self.disconnect(project_id, websocket)

    def local_connection_count(self) -> int:
        return sum(len(sockets) for sockets in self._connections.values())


manager = ConnectionManager()
