from __future__ import annotations

from datetime import date

from django.db.models import Q

from .models import Cruise, CruiseDateOverride, CruiseSchedule


def get_active_cruises():
    return Cruise.objects.filter(is_active=True).prefetch_related("schedules").order_by("sort_order", "name")


def get_schedule_for_date(cruise: Cruise, cruise_date: date) -> CruiseSchedule | None:
    return (
        CruiseSchedule.objects.filter(cruise=cruise, weekday=cruise_date.weekday(), is_active=True)
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=cruise_date))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=cruise_date))
        .order_by("start_time")
        .first()
    )


def get_date_override(cruise: Cruise, cruise_date: date) -> CruiseDateOverride | None:
    return CruiseDateOverride.objects.filter(cruise=cruise, date=cruise_date).first()
