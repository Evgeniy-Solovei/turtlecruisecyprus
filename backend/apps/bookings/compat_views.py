from __future__ import annotations

from datetime import date

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.cruises.models import Cruise
from apps.cruises.selectors import get_date_override, get_schedule_for_date
from apps.cruises.services import effective_capacity
from apps.payments.services import checkout_deadline_for_payment, create_or_get_payment_intent, verify_payment_intent_and_confirm

from apps.audit.services import log_journey_event

from .models import Booking
from .selectors import confirmed_seats_for_date
from .serializers import BookingSerializer
from .services import BookingError, BookingHoldInput, cancel_booking, create_booking_hold


def wp_success(data: dict) -> JsonResponse:
    return JsonResponse({"success": True, "data": data})


def wp_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"success": False, "data": {"message": message}}, status=status)


@csrf_exempt
@require_POST
def wordpress_admin_ajax(request):
    action = request.POST.get("action")
    session_id = request.POST.get("session_id") or request.POST.get("tc_session_id") or ""
    try:
        if action == "tc_track_event":
            sid = session_id or request.POST.get("session_id") or ""
            if not sid:
                return wp_error("session_id is required for tracking.", 400)
            log_journey_event(
                session_id=sid,
                event_type=request.POST.get("event_type") or request.POST.get("event", "unknown"),
                step=request.POST.get("step", ""),
                cruise_code=request.POST.get("cruise_type", ""),
                payload={"source": "wp-compat"},
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                completed=request.POST.get("completed") == "1",
                abandoned=request.POST.get("abandoned") == "1",
            )
            return wp_success({"tracked": True})
        if action == "tc_get_availability":
            cruise_type = request.POST.get("cruise_type", "")
            cruise_date = date.fromisoformat(request.POST.get("date", ""))
            cruise = get_object_or_404(Cruise, code=cruise_type, is_active=True)
            schedule = get_schedule_for_date(cruise, cruise_date)
            override = get_date_override(cruise, cruise_date)
            capacity = effective_capacity(cruise, cruise_date)
            confirmed = confirmed_seats_for_date(cruise, cruise_date)
            available = max(capacity - confirmed, 0)
            is_closed = bool(override and override.is_closed)
            is_working = schedule is not None
            is_day_off = is_closed or not is_working
            bookable = is_working and not is_closed and available > 0
            return wp_success(
                {
                    "available": available,
                    "capacity": capacity,
                    "booked": confirmed,
                    "is_day_off": is_day_off,
                    "is_working": is_working,
                    "bookable": bookable,
                }
            )
        if action == "tc_create_booking":
            booking = create_booking_hold(
                BookingHoldInput(
                    cruise_code=request.POST.get("cruise_type", ""),
                    cruise_date=date.fromisoformat(request.POST.get("cruise_date", "")),
                    adults_count=int(request.POST.get("adults", 1)),
                    children_count=int(request.POST.get("children", 0)),
                    first_name=request.POST.get("first_name", ""),
                    last_name=request.POST.get("last_name", ""),
                    email=request.POST.get("email", ""),
                    phone=request.POST.get("phone", ""),
                    customer_notes=request.POST.get("notes", ""),
                    source="wp-compat",
                    session_id=session_id,
                )
            )
            return wp_success({"booking_id": booking.public_id, "total": str(booking.total_amount)})
        if action == "tc_cancel_booking":
            booking = Booking.objects.get(public_id=request.POST.get("booking_id"))
            cancel_booking(booking)
            return wp_success({"booking_id": booking.public_id, "status": booking.status})
        if action == "tc_create_payment_intent":
            booking = Booking.objects.get(public_id=request.POST.get("booking_id"))
            payment = create_or_get_payment_intent(booking)
            return wp_success(
                {
                    "client_secret": payment.provider_client_secret,
                    "payment_intent_id": payment.stripe_payment_intent_id,
                    "checkout_session_id": payment.stripe_checkout_session_id,
                    "checkout_expires_at": checkout_deadline_for_payment(payment).isoformat(),
                }
            )
        if action in {"tc_confirm_payment", "tc_verify_payment"}:
            booking = Booking.objects.get(public_id=request.POST.get("booking_id"))
            payment_id = request.POST.get("payment_id") or request.POST.get("payment_intent")
            verify_payment_intent_and_confirm(booking, payment_id)
            return wp_success({"booking": BookingSerializer(booking).data})
    except Booking.DoesNotExist:
        return wp_error("Booking not found.", 404)
    except (BookingError, ValueError) as exc:
        return wp_error(str(exc), 400)
    return wp_error(f"Unsupported action: {action}", 400)
