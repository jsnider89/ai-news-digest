"""Timezone-aware time utilities."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.config.settings import get_settings


def get_local_timezone() -> ZoneInfo:
    """Get the configured local timezone."""
    settings = get_settings()
    return ZoneInfo(settings.default_timezone)


def now_local() -> datetime:
    """Get current time in the configured local timezone."""
    return datetime.now(get_local_timezone())


def to_local_time(dt: datetime) -> datetime:
    """Convert a datetime to the configured local timezone."""
    if dt is None:
        return None

    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(get_local_timezone())


def format_local_time(dt: datetime) -> str | None:
    """Format datetime in local timezone as ISO string."""
    if dt is None:
        return None

    local_dt = to_local_time(dt)
    return local_dt.isoformat()


def local_date_start(dt: datetime | None = None) -> datetime:
    """Get start of day (00:00:00) in local timezone for given date or today."""
    if dt is None:
        dt = now_local()
    else:
        dt = to_local_time(dt)

    return dt.replace(hour=0, minute=0, second=0, microsecond=0)