import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.exceptions import DomainError
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.repositories.user import UserRepository
from app.services.access import AccessService
from app.ws.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["realtime"])

WS_POLICY_VIOLATION = 1008


@router.websocket("/projects/{project_id}")
async def project_channel(
    websocket: WebSocket,
    project_id: int,
    token: str = Query(..., description="access-токен"),
) -> None:
    """Подписка на события проекта.

    События приходят в виде
    {"type": "task.updated", "project_id": 1, "payload": {...}, "ts": "..."}.
    """
    try:
        user_id = decode_token(token, "access")
    except DomainError:
        await websocket.close(code=WS_POLICY_VIOLATION, reason="invalid token")
        return

    async with SessionLocal() as session:
        user = await UserRepository(session).get(user_id)
        if user is None or not user.is_active:
            await websocket.close(code=WS_POLICY_VIOLATION, reason="user unavailable")
            return
        try:
            await AccessService(session).get_project_for(project_id, user_id)
        except DomainError:
            await websocket.close(code=WS_POLICY_VIOLATION, reason="no access")
            return

    await manager.connect(project_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "project_id": project_id,
                "payload": {"user_id": user_id},
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("ws error (project %s): %s", project_id, exc)
    finally:
        await manager.disconnect(project_id, websocket)
        if websocket.client_state is not WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except RuntimeError:
                pass
