from __future__ import annotations

from datetime import date, time

from .models import Cruise, CruiseSchedule
from .selectors import get_schedule_for_date


def format_time_display(value: time) -> str:
    """Single display format for cruise times across API, emails, SMS."""
    return value.strftime("%H:%M").lstrip("0") or "0:00"


def format_time_range(start: time, end: time) -> str:
    """Canonical cruise time string used in emails, SMS, API responses."""
    return f"{format_time_display(start)} – {format_time_display(end)}"


def schedule_for_cruise_date(cruise: Cruise, cruise_date: date) -> CruiseSchedule | None:
    return get_schedule_for_date(cruise, cruise_date)


def times_for_cruise_date(cruise: Cruise, cruise_date: date) -> tuple[time | None, time | None, str]:
    schedule = schedule_for_cruise_date(cruise, cruise_date)
    if not schedule:
        return None, None, ""
    label = format_time_range(schedule.start_time, schedule.end_time)
    return schedule.start_time, schedule.end_time, label


def default_times_for_cruise(cruise: Cruise) -> tuple[time, time, str]:
    schedule = (
        CruiseSchedule.objects.filter(cruise=cruise, is_active=True)
        .order_by("weekday", "start_time")
        .first()
    )
    if not schedule:
        raise ValueError(f"No active schedule configured for cruise {cruise.code}")
    return schedule.start_time, schedule.end_time, format_time_range(schedule.start_time, schedule.end_time)
