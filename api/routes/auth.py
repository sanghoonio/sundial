from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.settings import AuthToken, UserSettings
from api.schemas.auth import (
    ApiKeyCreatedResponse,
    CreateApiKeyRequest,
    LoginRequest,
    PasswordChangeRequest,
    SetupRequest,
    TokenListItem,
    TokenResponse,
    UsernameChangeRequest,
    UserResponse,
)
from api.utils.auth import (
    CurrentUser,
    generate_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_client_ip(request: Request) -> str | None:
    """Extract client IP, handling proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.get("/status")
async def get_auth_status(db: AsyncSession = Depends(get_db)):
    """Public endpoint to check if password is configured."""
    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    return {"password_configured": result.scalar_one_or_none() is not None}


@router.post("/setup", response_model=TokenResponse)
async def setup(request: SetupRequest, req: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password already configured")

    hashed = hash_password(request.password)
    db.add(UserSettings(key="password_hash", value=hashed))

    # Seed username if not present
    username_row = await db.execute(select(UserSettings).where(UserSettings.key == "username"))
    if username_row.scalar_one_or_none() is None:
        db.add(UserSettings(key="username", value="admin"))

    # Create opaque session token
    raw_token, token_hash = generate_token()
    now = datetime.now(timezone.utc)
    db.add(AuthToken(
        token_hash=token_hash,
        token_type="session",
        name=f"Browser session ({now.strftime('%Y-%m-%d')})",
        scope="read_write",
        ip_address=get_client_ip(req),
        user_agent=req.headers.get("User-Agent"),
    ))
    await db.commit()

    return TokenResponse(access_token=raw_token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No password configured. Use /api/auth/setup first.")

    if not verify_password(request.password, row.value):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    # Create opaque session token
    raw_token, token_hash = generate_token()
    now = datetime.now(timezone.utc)
    db.add(AuthToken(
        token_hash=token_hash,
        token_type="session",
        name=f"Browser session ({now.strftime('%Y-%m-%d')})",
        scope="read_write",
        ip_address=get_client_ip(req),
        user_agent=req.headers.get("User-Agent"),
    ))
    await db.commit()

    return TokenResponse(access_token=raw_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSettings).where(
            UserSettings.key.in_(["ai_enabled", "calendar_source", "calendar_sync_enabled"])
        )
    )
    rows = {row.key: row.value for row in result.scalars().all()}

    return UserResponse(
        username=current_user.username,
        settings={
            "ai_enabled": rows.get("ai_enabled", "false") == "true",
            "calendar_source": rows.get("calendar_source", ""),
        },
    )


# --- Account management ---


@router.put("/username", response_model=UserResponse)
async def change_username(
    request: UsernameChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not request.username or not request.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    result = await db.execute(select(UserSettings).where(UserSettings.key == "username"))
    row = result.scalar_one_or_none()
    if row:
        row.value = request.username.strip()
        row.updated_at = datetime.now(timezone.utc)
    else:
        db.add(UserSettings(key="username", value=request.username.strip()))
    await db.commit()

    return UserResponse(
        username=request.username.strip(),
        settings={},
    )


@router.put("/password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify current password
    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=400, detail="No password configured")

    if not verify_password(request.current_password, row.value):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Update password
    row.value = hash_password(request.new_password)
    row.updated_at = datetime.now(timezone.utc)

    # Revoke all tokens except current session
    await db.execute(
        delete(AuthToken).where(AuthToken.id != current_user.token_id)
    )
    await db.commit()

    return {"detail": "Password changed. All other sessions have been revoked."}


# --- Token management ---


@router.get("/tokens", response_model=list[TokenListItem])
async def list_tokens(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthToken).order_by(AuthToken.created_at.desc())
    )
    tokens = result.scalars().all()

    return [
        TokenListItem(
            id=t.id,
            token_type=t.token_type,
            name=t.name,
            scope=t.scope,
            ip_address=t.ip_address,
            user_agent=t.user_agent,
            last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
            created_at=t.created_at.isoformat() if t.created_at else "",
            is_current=t.id == current_user.token_id,
        )
        for t in tokens
    ]


@router.post("/tokens", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    request: CreateApiKeyRequest,
    req: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.scope not in ("read", "read_write"):
        raise HTTPException(status_code=400, detail="Scope must be 'read' or 'read_write'")

    raw_token, token_hash = generate_token()
    auth_token = AuthToken(
        token_hash=token_hash,
        token_type="api_key",
        name=request.name,
        scope=request.scope,
        ip_address=get_client_ip(req),
        user_agent=req.headers.get("User-Agent"),
    )
    db.add(auth_token)
    await db.commit()
    await db.refresh(auth_token)

    return ApiKeyCreatedResponse(
        id=auth_token.id,
        name=auth_token.name or "",
        scope=auth_token.scope,
        raw_token=raw_token,
    )


@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if token_id == current_user.token_id:
        raise HTTPException(status_code=400, detail="Cannot revoke your current session. Use logout instead.")

    result = await db.execute(select(AuthToken).where(AuthToken.id == token_id))
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    await db.delete(token)
    await db.commit()

    return {"detail": "Token revoked"}


@router.delete("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Delete the current session token from DB
    if current_user.token_id != "legacy_jwt":
        result = await db.execute(
            select(AuthToken).where(AuthToken.id == current_user.token_id)
        )
        token = result.scalar_one_or_none()
        if token:
            await db.delete(token)
            await db.commit()

    return {"detail": "Logged out"}
