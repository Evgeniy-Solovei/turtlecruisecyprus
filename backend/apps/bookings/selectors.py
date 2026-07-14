from __future__ import annotations

from datetime import date

from django.db.models import Sum

from apps.cruises.models import Cruise
from apps.cruises.services import effective_capacity

from .models import Booking


def confirmed_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    total = (
        Booking.objects.filter(
            cruise=cruise,
            cruise_date=cruise_date,
            status=Booking.Status.CONFIRMED,
        ).aggregate(total=Sum("total_seats"))["total"]
        or 0
    )
    return int(total)


def pending_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    total = (
        Booking.objects.filter(
            cruise=cruise,
            cruise_date=cruise_date,
            status=Booking.Status.PENDING_PAYMENT,
        ).aggregate(total=Sum("total_seats"))["total"]
        or 0
    )
    return int(total)


def booked_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    return confirmed_seats_for_date(cruise, cruise_date) + pending_seats_for_date(cruise, cruise_date)


def is_date_sold_out(cruise: Cruise, cruise_date: date) -> bool:
    """Новые брони блокируем при confirmed >= capacity. Pending не считаем."""
    return available_seats_for_date(cruise, cruise_date) <= 0


def available_seats_for_date(cruise: Cruise, cruise_date: date) -> int:
    capacity = effective_capacity(cruise, cruise_date)
    return max(capacity - confirmed_seats_for_date(cruise, cruise_date), 0)
