from __future__ import annotations

import logging

from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.bookings.models import Booking

from .services import checkout_deadline_for_payment, create_or_get_payment_intent, verify_checkout_session_and_confirm, verify_payment_intent_and_confirm
from .stripe_client import StripeNotConfigured
from .webhooks import handle_stripe_webhook

logger = logging.getLogger(__name__)


def _stripe_error_response(exc: Exception) -> Response | None:
    module = type(exc).__module__
    if not module.startswith("stripe"):
        return None
    message = getattr(exc, "user_message", None) or str(exc)
    return Response({"detail": message}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["POST"])
def stripe_payment_intent(request):
    booking_id = request.data.get("booking_id")
    if not booking_id:
        return Response({"detail": "booking_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    booking = get_object_or_404(Booking.objects.select_related("cruise"), public_id=booking_id)
    try:
        payment = create_or_get_payment_intent(booking)
    except StripeNotConfigured as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_410_GONE)
    except DatabaseError as exc:
        logger.exception("payment_intent db error booking=%s", booking.public_id)
        return Response({"detail": "Payment record could not be saved."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as exc:
        stripe_response = _stripe_error_response(exc)
        if stripe_response is not None:
            return stripe_response
        logger.exception("payment_intent failed booking=%s", booking.public_id)
        return Response({"detail": "Payment setup failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(
        {
            "payment_id": payment.id,
            "payment_intent_id": payment.stripe_payment_intent_id,
            "checkout_session_id": payment.stripe_checkout_session_id,
            "client_secret": payment.provider_client_secret,
            "amount": payment.amount,
            "currency": payment.currency,
            "checkout_expires_at": checkout_deadline_for_payment(payment).isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def stripe_confirm(request):
    booking = get_object_or_404(Booking, public_id=request.data["booking_id"])
    if request.data.get("checkout_session_id"):
        payment = verify_checkout_session_and_confirm(booking, request.data["checkout_session_id"])
    else:
        payment = verify_payment_intent_and_confirm(booking, request.data["payment_intent_id"])
    booking.refresh_from_db()
    return Response({"payment_id": payment.id, "status": payment.status, "booking_status": booking.status})


@api_view(["POST"])
def stripe_webhook(request):
    signature = request.headers.get("Stripe-Signature", "")
    handle_stripe_webhook(request.body, signature)
    return HttpResponse(status=200)
