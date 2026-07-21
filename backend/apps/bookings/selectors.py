from __future__ import annotations

from datetime import date

from django.db.models import Sum

from apps.cruises.models import Cruise
from apps.cruises.services import effective_capacity

from .models import Booking


def seats_breakdown_for_date(cruise: Cruise, cruise_date: date) -> tuple[int, int]:
    """Return (confirmed_seats, pending_seats) in one aggregate query."""
    rows = (
        Booking.objects.filter(
            cruise=cruise,
            cruise_date=cruise_date,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING_PAYMENT],
        )
        .values("status")
        .annotate(total=Sum("total_seats"))
    )
    confirmed = 0
    pending = 0
    for row in rows:
        total = int(row["total"] or 0)
        if row["status"] == Booking.Status.CONFIRMED:
            confirmed = total
        elif row["status"] == Booking.Status.PENDING_PAYMENT:
            pending = total
    return confirmed, pending


def confirmed_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    return seats_breakdown_for_date(cruise, cruise_date)[0]


def pending_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    return seats_breakdown_for_date(cruise, cruise_date)[1]


def booked_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    confirmed, pending = seats_breakdown_for_date(cruise, cruise_date)
    return confirmed + pending


def is_date_sold_out(cruise: Cruise, cruise_date: date) -> bool:
    """Новые брони блокируем при confirmed >= capacity. Pending не считаем."""
    return available_seats_for_date(cruise, cruise_date) <= 0


def available_seats_for_date(cruise: Cruise, cruise_date: date, *, capacity: int | None = None) -> int:
    if capacity is None:
        capacity = effective_capacity(cruise, cruise_date)
    confirmed, _ = seats_breakdown_for_date(cruise, cruise_date)
    return max(capacity - confirmed, 0)
