from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.bookings.selectors import seats_breakdown_for_date

from apps.cruises.time_utils import format_time_range

from .models import Cruise
from .selectors import get_active_cruises, get_date_override, get_schedule_for_date
from .serializers import CruiseSerializer


@api_view(["GET"])
def cruise_list(request):
    return Response(CruiseSerializer(get_active_cruises(), many=True).data)


@api_view(["GET"])
def cruise_availability(request, code: str):
    cruise = get_object_or_404(Cruise, code=code, is_active=True)
    cruise_date = date.fromisoformat(request.query_params["date"])
    schedule = get_schedule_for_date(cruise, cruise_date)
    override = get_date_override(cruise, cruise_date)

    capacity = (
        override.capacity_override
        if override and override.capacity_override is not None
        else cruise.default_capacity
    )
    adult_price = (
        override.adult_price_override
        if override and override.adult_price_override is not None
        else cruise.default_adult_price
    )
    child_price = (
        override.child_price_override
        if override and override.child_price_override is not None
        else cruise.default_child_price
    )
    confirmed, pending = seats_breakdown_for_date(cruise, cruise_date)
    available = max(capacity - confirmed, 0)
    is_closed = bool(override and override.is_closed)
    time_label = format_time_range(schedule.start_time, schedule.end_time) if schedule else ""

    return Response(
        {
            "cruise": cruise.code,
            "date": cruise_date,
            "bookable": bool(schedule) and not is_closed and available > 0,
            "is_closed": is_closed,
            "capacity": capacity,
            "booked": confirmed,
            "pending": pending,
            "available": available,
            "adult_price": adult_price,
            "child_price": child_price,
            "start_time": schedule.start_time if schedule else None,
            "end_time": schedule.end_time if schedule else None,
            "time_label": time_label,
        }
    )
