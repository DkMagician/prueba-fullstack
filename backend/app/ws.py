import asyncio
from typing import Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class WSManager:
    def __init__(self) -> None:
        self._active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        # Si no aceptas, Starlette te devuelve 403 Forbidden
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()

        async with self._lock:
            self._active.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._active.discard(websocket)

    async def broadcast_text(self, message: str) -> None:
        async with self._lock:
            sockets = list(self._active)

        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._active.discard(ws)


ws_manager = WSManager()
