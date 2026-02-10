from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.config import settings


class UTCJSONResponse(JSONResponse):
    """Custom JSON response that adds 'Z' suffix to naive datetime ISO strings."""

    def render(self, content: Any) -> bytes:
        return super().render(self._process_datetimes(content))

    def _process_datetimes(self, obj: Any) -> Any:
        """Recursively process to add 'Z' suffix to datetime strings."""
        if isinstance(obj, dict):
            return {k: self._process_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._process_datetimes(item) for item in obj]
        elif isinstance(obj, datetime):
            iso = obj.isoformat()
            if obj.tzinfo is None:
                return iso + "Z"
            return iso
        elif isinstance(obj, str):
            # Handle ISO datetime strings that Pydantic already serialized
            # Pattern: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SS.ffffff
            if (
                len(obj) >= 19
                and obj[4:5] == "-"
                and obj[7:8] == "-"
                and obj[10:11] == "T"
                and not obj.endswith("Z")
                and "+" not in obj[19:]
                and "-" not in obj[19:]
            ):
                return obj + "Z"
        return obj


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.init_db import init_database
    await init_database()
    yield


# Create the actual API application
api_app = FastAPI(
    title="Sundial",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    default_response_class=UTCJSONResponse,
)

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
from api.routes.auth import router as auth_router
from api.routes.notes import router as notes_router
from api.routes.tasks import router as tasks_router
from api.routes.projects import router as projects_router
from api.routes.calendar import router as calendar_router
from api.routes.search import router as search_router
from api.routes.dashboard import router as dashboard_router
from api.routes.ai import router as ai_router
from api.routes.tags import router as tags_router
from api.routes.settings import router as settings_router
from api.routes.workspace import router as workspace_router

api_app.include_router(auth_router, prefix="/api")
api_app.include_router(notes_router, prefix="/api")
api_app.include_router(tasks_router, prefix="/api")
api_app.include_router(projects_router, prefix="/api")
api_app.include_router(calendar_router, prefix="/api")
api_app.include_router(search_router, prefix="/api")
api_app.include_router(dashboard_router, prefix="/api")
api_app.include_router(ai_router, prefix="/api")
api_app.include_router(tags_router, prefix="/api")
api_app.include_router(settings_router, prefix="/api")
api_app.include_router(workspace_router, prefix="/api")

# Mount MCP server (Starlette sub-app for SSE transport)
from api.mcp.routes import mcp_app
api_app.mount("/mcp", mcp_app)


# WebSocket endpoint
from api.utils.websocket import manager


@api_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = websocket.query_params.get("client_id")
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Static file serving for SPA frontend
_ui_build = Path(__file__).resolve().parent.parent / "ui" / "build"
if _ui_build.is_dir():
    @api_app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _ui_build / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_ui_build / "index.html"))


# Mount api_app at BASE_PATH if configured, otherwise use it directly as the root app
if settings.BASE_PATH:
    app = FastAPI(lifespan=lifespan)
    app.mount(settings.BASE_PATH, api_app)
else:
    app = api_app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
