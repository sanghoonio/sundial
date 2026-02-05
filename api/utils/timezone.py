import zoneinfo
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException


def resolve_today(tz: str | None) -> tuple[datetime, datetime, str]:
    """Calculate today's start/end boundaries in UTC, respecting user timezone.

    Args:
        tz: IANA timezone string (e.g. "America/Los_Angeles") or None for UTC.

    Returns:
        (today_start_utc, today_end_utc, local_date_str) where the boundaries
        represent midnight-to-midnight in the user's timezone converted to UTC.

    Raises:
        HTTPException(400) for invalid timezone strings.
    """
    if tz:
        try:
            user_tz = zoneinfo.ZoneInfo(tz)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {tz}")

        now_local = datetime.now(user_tz)
        local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = local_midnight.astimezone(timezone.utc)
        today_end = (local_midnight + timedelta(days=1)).astimezone(timezone.utc)
        local_date = local_midnight.strftime("%Y-%m-%d")
    else:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        local_date = today_start.strftime("%Y-%m-%d")

    return today_start, today_end, local_date
