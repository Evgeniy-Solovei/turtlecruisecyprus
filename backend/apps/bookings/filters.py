from __future__ import annotations

from datetime import datetime

from django.db.models import QuerySet
from django.utils import timezone

from .models import Booking


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), tz)
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1), tz)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1), tz)
    return start, end


def earnings_queryset_for_period(request) -> QuerySet:
    """Только для строки «Выручка» — список броней не трогает."""
    period = request.GET.get("earnings_period", "this_month")
    qs = Booking.objects.filter(status=Booking.Status.CONFIRMED)

    date_from = request.GET.get("earnings_from")
    date_to = request.GET.get("earnings_to")
    if date_from:
        qs = qs.filter(confirmed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(confirmed_at__date__lte=date_to)
    if date_from or date_to:
        return qs

    if period == "all":
        return qs

    now = timezone.localtime()
    if period == "this_month":
        start, end = _month_bounds(now.year, now.month)
    elif period == "last_month":
        month = now.month - 1 or 12
        year = now.year if now.month > 1 else now.year - 1
        start, end = _month_bounds(year, month)
    elif period == "this_year":
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime(now.year, 1, 1), tz)
        end = timezone.make_aware(datetime(now.year + 1, 1, 1), tz)
    else:
        start, end = _month_bounds(now.year, now.month)
        period = "this_month"

    return qs.filter(confirmed_at__gte=start, confirmed_at__lt=end)


def earnings_period_label(request) -> str:
    if request.GET.get("earnings_from") or request.GET.get("earnings_to"):
        return f"{request.GET.get('earnings_from', '…')} — {request.GET.get('earnings_to', '…')}"
    labels = {
        "this_month": "текущий месяц",
        "last_month": "прошлый месяц",
        "this_year": "этот год",
        "all": "всё время",
    }
    return labels.get(request.GET.get("earnings_period", "this_month"), "текущий месяц")
