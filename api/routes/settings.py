from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.settings import UserSettings
from api.schemas.settings import SettingsResponse, SettingsUpdate
from api.utils.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])

# Keys that map to the SettingsResponse schema
_SETTINGS_KEYS = {
    "ai_enabled": ("bool", False),
    "ai_auto_tag": ("bool", False),
    "ai_auto_extract_tasks": ("bool", False),
    "calendar_source": ("str", ""),
    "calendar_sync_enabled": ("bool", False),
    "theme": ("str", "light"),
}


def _parse_value(raw: str, vtype: str):
    if vtype == "bool":
        return raw.lower() == "true"
    return raw


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserSettings).where(UserSettings.key.in_(list(_SETTINGS_KEYS.keys())))
    )
    rows = {row.key: row.value for row in result.scalars().all()}

    data = {}
    for key, (vtype, default) in _SETTINGS_KEYS.items():
        if key in rows:
            data[key] = _parse_value(rows[key], vtype)
        else:
            data[key] = default

    return SettingsResponse(**data)


@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    updates = body.model_dump(exclude_unset=True)

    for key, value in updates.items():
        if isinstance(value, bool):
            str_value = "true" if value else "false"
        else:
            str_value = str(value)

        result = await db.execute(select(UserSettings).where(UserSettings.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = str_value
            existing.updated_at = now
        else:
            db.add(UserSettings(key=key, value=str_value, updated_at=now))

    await db.commit()
    return await get_settings(db)
