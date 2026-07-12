from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.bookings.selectors import confirmed_seats_for_date, pending_seats_for_date

from apps.cruises.time_utils import format_time_range, times_for_cruise_date

from .models import Cruise
from .selectors import get_active_cruises, get_date_override, get_schedule_for_date
from .serializers import CruiseSerializer
from .services import effective_capacity, effective_prices


@api_view(["GET"])
def cruise_list(request):
    return Response(CruiseSerializer(get_active_cruises(), many=True).data)


@api_view(["GET"])
def cruise_availability(request, code: str):
    cruise = get_object_or_404(Cruise, code=code, is_active=True)
    cruise_date = date.fromisoformat(request.query_params["date"])
    schedule = get_schedule_for_date(cruise, cruise_date)
    override = get_date_override(cruise, cruise_date)
    capacity = effective_capacity(cruise, cruise_date)
    confirmed = confirmed_seats_for_date(cruise, cruise_date)
    adult_price, child_price = effective_prices(cruise, cruise_date)
    _, _, time_label = times_for_cruise_date(cruise, cruise_date)
    bookable = bool(schedule) and not (override and override.is_closed) and confirmed < capacity
    return Response(
        {
            "cruise": cruise.code,
            "date": cruise_date,
            "bookable": bookable,
            "is_closed": bool(override and override.is_closed),
            "capacity": capacity,
            "booked": confirmed,
            "pending": pending_seats_for_date(cruise, cruise_date),
            "available": max(capacity - confirmed, 0),
            "adult_price": adult_price,
            "child_price": child_price,
            "start_time": schedule.start_time if schedule else None,
            "end_time": schedule.end_time if schedule else None,
            "time_label": time_label,
        }
    )
