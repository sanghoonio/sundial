import json

from fastapi import Request, WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[tuple[WebSocket, str | None]] = []

    async def connect(self, websocket: WebSocket, client_id: str | None = None):
        await websocket.accept()
        self.active_connections.append((websocket, client_id))

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [
            (ws, cid) for ws, cid in self.active_connections if ws is not websocket
        ]

    async def broadcast(self, event_type: str, data: dict, exclude_client_id: str | None = None):
        message = json.dumps({"type": event_type, "data": data})
        for ws, cid in self.active_connections:
            if exclude_client_id and cid == exclude_client_id:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                pass


def get_client_id(request: Request) -> str | None:
    return request.headers.get("x-client-id")


manager = ConnectionManager()
