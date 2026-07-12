from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.audit.trace import build_booking_trace

from .models import Booking
from .serializers import BookingHoldSerializer, BookingSerializer
from .services import BookingError, cancel_booking, create_booking_hold


@api_view(["POST"])
def create_hold(request):
    serializer = BookingHoldSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        booking = create_booking_hold(serializer.to_input())
    except BookingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def booking_trace(request, public_id: str):
    return Response(build_booking_trace(public_id))


@api_view(["GET"])
def booking_detail(request, public_id: str):
    booking = get_object_or_404(Booking.objects.select_related("customer", "cruise"), public_id=public_id)
    return Response(BookingSerializer(booking).data)


@api_view(["GET"])
def booking_status(request, public_id: str):
    booking = get_object_or_404(Booking, public_id=public_id)
    return Response(
        {
            "public_id": booking.public_id,
            "status": booking.status,
            "cancel_reason": booking.cancel_reason or "",
            "payable": booking.status == Booking.Status.PENDING_PAYMENT,
        }
    )


@api_view(["POST"])
def cancel(request, public_id: str):
    booking = get_object_or_404(Booking, public_id=public_id)
    try:
        cancel_booking(booking)
    except BookingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(BookingSerializer(booking).data)
