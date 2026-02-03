"""FastAPI routes to serve MCP over SSE.

Mounts GET /mcp/sse (event stream) and POST /mcp/messages (tool calls).
Auth uses the existing Bearer token system via ASGI middleware.
"""

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport

from api.mcp.server import mcp_server
from api.config import settings

logger = logging.getLogger(__name__)

# SSE transport — the messages endpoint path must include BASE_PATH for subpath deployments
messages_path = f"{settings.BASE_PATH}/mcp/messages" if settings.BASE_PATH else "/mcp/messages"
sse_transport = SseServerTransport(messages_path)


async def _check_mcp_enabled(db) -> bool:
    """Check if MCP is enabled in settings."""
    from sqlalchemy import select
    from api.models.settings import UserSettings
    result = await db.execute(
        select(UserSettings).where(UserSettings.key == "mcp_enabled")
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        return True  # Default to enabled
    return setting.value.lower() == "true"


async def handle_sse(request: Request):
    """SSE endpoint: opens persistent event stream for MCP protocol."""
    # Auth check: validate Bearer token
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        from starlette.responses import JSONResponse
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    token = auth_header[7:]
    # Validate the token
    from api.utils.auth import hash_token
    from api.database import async_session
    from api.models.settings import AuthToken, UserSettings
    from sqlalchemy import select

    async with async_session() as db:
        # Check if MCP is enabled
        if not await _check_mcp_enabled(db):
            from starlette.responses import JSONResponse
            return JSONResponse({"detail": "MCP is disabled"}, status_code=403)

        token_hash = hash_token(token)
        result = await db.execute(
            select(AuthToken).where(AuthToken.token_hash == token_hash)
        )
        auth_token = result.scalar_one_or_none()
        if auth_token is None:
            from starlette.responses import JSONResponse
            return JSONResponse({"detail": "Invalid token"}, status_code=401)

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


async def handle_messages(request: Request):
    """Handle incoming MCP messages (tool calls, etc.)."""
    # Auth check
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        from starlette.responses import JSONResponse
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    token = auth_header[7:]
    from api.utils.auth import hash_token
    from api.database import async_session
    from api.models.settings import AuthToken, UserSettings
    from sqlalchemy import select

    async with async_session() as db:
        # Check if MCP is enabled
        if not await _check_mcp_enabled(db):
            from starlette.responses import JSONResponse
            return JSONResponse({"detail": "MCP is disabled"}, status_code=403)

        token_hash = hash_token(token)
        result = await db.execute(
            select(AuthToken).where(AuthToken.token_hash == token_hash)
        )
        auth_token = result.scalar_one_or_none()
        if auth_token is None:
            from starlette.responses import JSONResponse
            return JSONResponse({"detail": "Invalid token"}, status_code=401)

    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


# Create a Starlette sub-app that can be mounted on the FastAPI app
mcp_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ],
)
