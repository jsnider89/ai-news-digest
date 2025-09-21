"""Helpers for determining U.S. market open/closed status (NYSE/Nasdaq)."""
from __future__ import annotations

from datetime import datetime, time

from zoneinfo import ZoneInfo

from app.utils.time_utils import get_local_timezone

# NYSE/Nasdaq core trading hours: 09:30-16:00 ET, Monday-Friday, excluding major US market holidays.
_EASTERN_TZ = ZoneInfo("America/New_York")


def is_us_market_closed(reference: datetime | None = None) -> bool:
    """Return True if U.S. equity markets are closed for the *day*.

    We only consider weekends and federal market holidays. Intraday trading hours
    are ignored so that briefings produced outside 9:30-16:00 ET still show
    "Market Day" for an otherwise open session.
    """

    local_tz = get_local_timezone()
    local_dt = reference.astimezone(local_tz) if reference else datetime.now(local_tz)
    local_date = local_dt.date()

    # Weekend check (Saturday=5, Sunday=6) using local calendar
    if local_dt.weekday() >= 5:
        return True

    # Evaluate holidays against Eastern calendar at midday of the local date
    eastern_midday = datetime.combine(local_date, time(12, 0), tzinfo=local_tz).astimezone(_EASTERN_TZ)

    holidays = _observed_holidays(eastern_midday.year) | _observed_holidays(eastern_midday.year - 1) | _observed_holidays(eastern_midday.year + 1)
    if eastern_midday.date() in holidays:
        return True

    return False


def format_market_badge(reference: datetime | None = None) -> tuple[str, str]:
    """Return (label_text, style) for the market badge."""

    local_tz = get_local_timezone()
    reference = reference.astimezone(local_tz) if reference else datetime.now(local_tz)
    weekday = reference.strftime("%A")
    date_str = reference.strftime("%b %d")

    closed = is_us_market_closed(reference)
    label = "Market Closed" if closed else "Market Day"
    style = (
        "display:inline-block;padding:6px 10px;border-radius:999px;font-size:12px;margin:6px 0;"
        "font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;"
        f"background:{'#fee2e2' if closed else '#dcfce7'};"
        f"color:{'#991b1b' if closed else '#065f46'};"
        f"border:1px solid {'#fecaca' if closed else '#bbf7d0'};"
    )
    return f"🗓️ {weekday}, {date_str} • {label}", style


def format_date_badge(reference: datetime | None = None) -> tuple[str, str]:
    """Return (label_text, style) for a simple date badge with random color."""

    local_tz = get_local_timezone()
    reference = reference.astimezone(local_tz) if reference else datetime.now(local_tz)
    weekday = reference.strftime("%A")
    date_str = reference.strftime("%b %d")

    # Simple color variations for non-market newsletters
    colors = [
        {"bg": "#f3f4f6", "color": "#374151", "border": "#d1d5db"},  # Gray
        {"bg": "#dbeafe", "color": "#1e40af", "border": "#93c5fd"},  # Blue
        {"bg": "#f3e8ff", "color": "#7c3aed", "border": "#c4b5fd"},  # Purple
        {"bg": "#ecfdf5", "color": "#059669", "border": "#a7f3d0"},  # Green
        {"bg": "#fef3c7", "color": "#d97706", "border": "#fcd34d"},  # Yellow
        {"bg": "#fed7aa", "color": "#ea580c", "border": "#fdba74"},  # Orange
        {"bg": "#fecaca", "color": "#dc2626", "border": "#fca5a5"},  # Red
    ]

    # Use day of year to get consistent but "random" color for the date
    day_of_year = reference.timetuple().tm_yday
    color = colors[day_of_year % len(colors)]

    style = (
        "display:inline-block;padding:6px 10px;border-radius:999px;font-size:12px;margin:6px 0;"
        "font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;"
        f"background:{color['bg']};"
        f"color:{color['color']};"
        f"border:1px solid {color['border']};"
    )
    return f"🗓️ {weekday}, {date_str}", style


def _observed_holidays(year: int) -> set:
    """Return a minimal set of U.S. market holidays for the given year."""

    # For brevity we cover the primary fixed-date or observed holidays likely to impact the digest.
    # Extend this list as needed or integrate an external calendar.
    from datetime import date

    holidays = {
        date(year, 1, 1),    # New Year's Day
        date(year, 7, 4),    # Independence Day
        date(year, 12, 25),  # Christmas Day
        date(year, 6, 19),   # Juneteenth
    }

    # If any holiday falls on a weekend, add observed weekday
    observed = set()
    for day in holidays:
        if day.weekday() == 5:  # Saturday -> observed Friday
            observed.add(day.replace(day=day.day - 1))
        elif day.weekday() == 6:  # Sunday -> observed Monday
            observed.add(day.replace(day=day.day + 1))
    holidays |= observed

    # Add simple approximations for floating holidays
    holidays.add(_nth_weekday_of_month(year, 1, 0, 3))   # MLK Day (3rd Monday Jan)
    holidays.add(_nth_weekday_of_month(year, 2, 0, 3))   # Presidents Day
    holidays.add(_nth_weekday_of_month(year, 5, 0, -1))  # Memorial Day (last Monday May)
    holidays.add(_nth_weekday_of_month(year, 10, 0, 2))  # Columbus Day / Indigenous Peoples' Day (2nd Monday Oct)
    holidays.add(_nth_weekday_of_month(year, 9, 0, 1))   # Labor Day (1st Monday Sep)
    holidays.add(_nth_weekday_of_month(year, 11, 3, 4))  # Thanksgiving (4th Thursday Nov)

    # Good Friday (Friday before Easter Sunday)
    holidays.add(_good_friday(year))

    return holidays


def _nth_weekday_of_month(year: int, month: int, weekday: int, occurrence: int):
    """Return the date of the nth occurrence of a weekday in a given month.

    weekday: Monday=0, Sunday=6. occurrence>0 counts from start, <0 counts from end.
    """

    from datetime import date, timedelta

    if occurrence > 0:
        day = date(year, month, 1)
        while day.weekday() != weekday:
            day += timedelta(days=1)
        for _ in range(occurrence - 1):
            day += timedelta(days=7)
        return day

    # occurrence negative (from end of month)
    day = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    day -= timedelta(days=1)
    while day.weekday() != weekday:
        day -= timedelta(days=1)
    for _ in range(abs(occurrence) - 1):
        day -= timedelta(days=7)
    return day


def _good_friday(year: int):
    """Return the date for Good Friday (Friday before Easter)."""

    from datetime import date, timedelta

    # Anonymous Gregorian algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = 1 + ((h + l - 7 * m + 114) % 31)
    easter = date(year, month, day)
    return easter - timedelta(days=2)
