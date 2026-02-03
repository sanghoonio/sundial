from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.init_db import init_database
    await init_database()
    yield


app = FastAPI(
    title="Sundial",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

app.add_middleware(
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

app.include_router(auth_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")

# Mount MCP server (Starlette sub-app for SSE transport)
from api.mcp.routes import mcp_app
app.mount("/mcp", mcp_app)


# WebSocket endpoint
from api.utils.websocket import manager


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Static file serving for SPA frontend
_ui_build = Path(__file__).resolve().parent.parent / "ui" / "build"
if _ui_build.is_dir():
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _ui_build / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_ui_build / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
