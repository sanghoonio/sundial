"""Recurrence utilities for recurring tasks (spawn-on-complete model)."""

import uuid
from datetime import datetime, timezone

from dateutil.rrule import rrulestr


def generate_series_id() -> str:
    """Generate a unique recurring series identifier."""
    return f"rseries_{uuid.uuid4().hex[:12]}"


def next_occurrence(rrule_str: str, after_dt: datetime) -> datetime | None:
    """Compute the next occurrence after *after_dt* using an RRULE string.

    Returns None if the rule has expired (e.g. COUNT exhausted or UNTIL passed).
    """
    if after_dt.tzinfo is None:
        after_dt = after_dt.replace(tzinfo=timezone.utc)

    rule = rrulestr(rrule_str, dtstart=after_dt)
    nxt = rule.after(after_dt, inc=False)
    if nxt is None:
        return None
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=timezone.utc)
    return nxt


# Simple preset mapping for MCP / natural-language shortcuts
_PRESETS: dict[str, str] = {
    "daily": "FREQ=DAILY",
    "weekly": "FREQ=WEEKLY",
    "monthly": "FREQ=MONTHLY",
    "yearly": "FREQ=YEARLY",
}


def normalize_rule(value: str) -> str:
    """Accept either a preset name or a raw RRULE string and return a valid RRULE."""
    lowered = value.strip().lower()
    if lowered in _PRESETS:
        return _PRESETS[lowered]
    return value.strip()


def human_readable_rule(rrule_str: str) -> str:
    """Convert an RRULE string to a short human-readable description."""
    parts = rrule_str.upper().split(";")
    freq_map = {
        "FREQ=DAILY": "Every day",
        "FREQ=WEEKLY": "Every week",
        "FREQ=MONTHLY": "Every month",
        "FREQ=YEARLY": "Every year",
    }
    label = "Recurring"
    for part in parts:
        if part in freq_map:
            label = freq_map[part]
            break

    for part in parts:
        if part.startswith("COUNT="):
            count = part.split("=")[1]
            label += f" ({count} times)"
        elif part.startswith("UNTIL="):
            raw = part.split("=")[1]
            if len(raw) >= 8:
                label += f" (until {raw[:4]}-{raw[4:6]}-{raw[6:8]})"

    return label
