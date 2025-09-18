"""Curated timezone catalog for UI selection."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

COMMON_TIMEZONES: tuple[str, ...] = (
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
    "America/Anchorage",
    "America/Halifax",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Warsaw",
    "Europe/Moscow",
    "Africa/Johannesburg",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Hong_Kong",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Australia/Sydney",
    "Australia/Perth",
)


@dataclass(frozen=True)
class TimezoneOption:
    value: str
    label: str


def build_timezone_options(extra: list[str] | None = None) -> list[TimezoneOption]:
    """Return labelled timezone options including optional extras."""
    values: list[str] = list(dict.fromkeys((extra or []) + list(COMMON_TIMEZONES)))
    options: list[TimezoneOption] = []
    now = datetime.utcnow()
    for zone_name in values:
        try:
            tz = ZoneInfo(zone_name)
            abbreviation = now.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).tzname()
            label = f"{zone_name} ({abbreviation})" if abbreviation else zone_name
        except Exception:
            label = zone_name
        options.append(TimezoneOption(value=zone_name, label=label))
    return options

