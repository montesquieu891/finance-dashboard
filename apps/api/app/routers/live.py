from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.live_monitor import live_monitor_service

router = APIRouter(tags=["live"])


@router.websocket("/ws/prices")
async def websocket_live_prices(
    websocket: WebSocket,
    api_key: str = Query(alias="api_key"),
    basket_id: uuid.UUID | None = Query(default=None),
) -> None:
    if api_key != settings.api_key:
        await websocket.close(code=1008)
        return

    await live_monitor_service.connect(websocket, basket_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await live_monitor_service.disconnect(websocket, basket_id)
