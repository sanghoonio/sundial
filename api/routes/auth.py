from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.settings import UserSettings
from api.schemas.auth import LoginRequest, SetupRequest, TokenResponse, UserResponse
from api.utils.auth import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/setup", response_model=TokenResponse)
async def setup(request: SetupRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password already configured")

    hashed = hash_password(request.password)
    db.add(UserSettings(key="password_hash", value=hashed))
    await db.commit()

    token = create_access_token()
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No password configured. Use /api/auth/setup first.")

    if not verify_password(request.password, row.value):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    token = create_access_token()
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse, dependencies=[Depends(get_current_user)])
async def get_me(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserSettings).where(
            UserSettings.key.in_(["ai_enabled", "calendar_source", "calendar_sync_enabled"])
        )
    )
    rows = {row.key: row.value for row in result.scalars().all()}

    return UserResponse(
        username="admin",
        settings={
            "ai_enabled": rows.get("ai_enabled", "false") == "true",
            "calendar_source": rows.get("calendar_source", ""),
        },
    )
