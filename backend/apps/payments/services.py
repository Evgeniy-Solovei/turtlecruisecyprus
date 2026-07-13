from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.audit.models import OperationLog
from apps.audit.services import log_journey_event, log_operation
from apps.bookings.models import Booking
from apps.bookings.services import close_competing_sessions_if_sold_out
from apps.notifications.tasks import send_admin_booking_email, send_admin_sms, send_customer_booking_email

from .models import Payment
from .stripe_client import (
    STRIPE_CHECKOUT_MAX_HOURS,
    STRIPE_CHECKOUT_MAX_MINUTES,
    checkout_session_expires_at,
    create_checkout_session,
    retrieve_checkout_session,
    retrieve_payment_intent,
)


def _stripe_object_id(value) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    return getattr(value, "id", None) or str(value)


def checkout_deadline_for_payment(payment: Payment) -> datetime:
    """Когда Stripe сам закроет эту checkout session (технический срок, не бизнес-логика)."""
    return payment.created_at + timedelta(hours=STRIPE_CHECKOUT_MAX_HOURS, minutes=STRIPE_CHECKOUT_MAX_MINUTES)


def create_or_get_payment_intent(booking: Booking) -> Payment:
    """Создаёт Stripe Checkout Session (embedded) с нативным expires_at."""
    if booking.status not in {
        Booking.Status.PENDING_PAYMENT,
        Booking.Status.EXPIRED,
    }:
        raise ValueError(f"Booking is not pending payment: {booking.status}")
    if (
        booking.status == Booking.Status.EXPIRED
        and booking.cancel_reason == Booking.CancelReason.SOLD_OUT
    ):
        raise ValueError("Booking is no longer available")

    payment = Payment.objects.filter(
        booking=booking,
        provider="stripe",
        status__in=[
            Payment.Status.REQUIRES_PAYMENT_METHOD,
            Payment.Status.REQUIRES_ACTION,
            Payment.Status.PROCESSING,
        ],
    ).first()
    if payment and payment.provider_client_secret:
        return payment

    if payment:
        if payment.stripe_checkout_session_id:
            try:
                session = retrieve_checkout_session(payment.stripe_checkout_session_id)
                client_secret = session.get("client_secret")
                if session.get("status") == "open" and client_secret:
                    payment.provider_client_secret = client_secret
                    payment.save(update_fields=["provider_client_secret"])
                    return payment
            except Exception:
                pass
        payment.delete()

    expires_unix = checkout_session_expires_at()
    metadata = {
        "booking_public_id": booking.public_id,
        "booking_id": str(booking.id),
    }
    attempt = Payment.objects.filter(booking=booking).count() + 1
    idempotency_key = f"booking:{booking.public_id}:checkout-session:v{attempt}"
    return_url = (
        f"{settings.SITE_BASE_URL.rstrip('/')}/booking-return/"
        f"?tc_booking_return={booking.public_id}&session_id={{CHECKOUT_SESSION_ID}}"
    )
    session = create_checkout_session(
        amount=booking.total_amount,
        currency=booking.currency,
        product_name=f"{booking.cruise.name} — {booking.cruise_date.isoformat()}",
        metadata=metadata,
        idempotency_key=idempotency_key,
        return_url=return_url,
        expires_at=expires_unix,
    )
    client_secret = session.get("client_secret")
    if not client_secret:
        raise RuntimeError("Stripe Checkout Session did not return client_secret.")
    payment = Payment.objects.create(
        booking=booking,
        amount=booking.total_amount,
        currency=booking.currency,
        stripe_checkout_session_id=_stripe_object_id(session.get("id")) or "",
        stripe_payment_intent_id=_stripe_object_id(session.get("payment_intent")),
        provider_client_secret=client_secret,
        idempotency_key=idempotency_key,
        raw_provider_status=session.get("status", ""),
        status=_map_checkout_session_status(session.get("status", "")),
    )
    log_operation(
        category="payment",
        action="checkout_session_created",
        entity_type="payment",
        entity_id=str(payment.id),
        booking_id=booking.id,
        details={
            "amount": str(booking.total_amount),
            "currency": booking.currency,
            "checkout_session_id": _stripe_object_id(session.get("id")) or "",
            "stripe_expires_at": checkout_deadline_for_payment(payment).isoformat(),
        },
    )
    return payment


def _map_checkout_session_status(status: str) -> str:
    return {
        "open": Payment.Status.REQUIRES_PAYMENT_METHOD,
        "complete": Payment.Status.SUCCEEDED,
        "expired": Payment.Status.CANCELLED,
    }.get(status, Payment.Status.FAILED)


def _map_payment_intent_status(status: str) -> str:
    return {
        "requires_payment_method": Payment.Status.REQUIRES_PAYMENT_METHOD,
        "requires_action": Payment.Status.REQUIRES_ACTION,
        "processing": Payment.Status.PROCESSING,
        "succeeded": Payment.Status.SUCCEEDED,
        "canceled": Payment.Status.CANCELLED,
    }.get(status, Payment.Status.FAILED)


@transaction.atomic
def _finalize_successful_payment(payment: Payment, payment_intent_id: str, raw_status: str) -> Payment:
    booking = payment.booking
    if payment.status == Payment.Status.SUCCEEDED and booking.status == Booking.Status.CONFIRMED:
        return payment

    payment.status = Payment.Status.SUCCEEDED
    payment.raw_provider_status = raw_status
    payment.transaction_id = payment_intent_id or payment.stripe_checkout_session_id or ""
    payment.paid_at = timezone.now()
    if payment_intent_id and not payment.stripe_payment_intent_id:
        payment.stripe_payment_intent_id = payment_intent_id
    payment.save(
        update_fields=[
            "status",
            "raw_provider_status",
            "transaction_id",
            "paid_at",
            "stripe_payment_intent_id",
            "updated_at",
        ]
    )

    if booking.status == Booking.Status.CONFIRMED:
        return payment

    if (
        booking.status == Booking.Status.EXPIRED
        and booking.cancel_reason == Booking.CancelReason.SOLD_OUT
    ):
        log_operation(
            category="payment",
            action="payment_after_sold_out",
            status=OperationLog.Status.FAILED,
            entity_type="booking",
            entity_id=booking.public_id,
            booking_id=booking.id,
            details={
                "payment_intent_id": payment_intent_id,
                "checkout_session_id": payment.stripe_checkout_session_id,
                "note": "Payment succeeded after sold-out close; manual refund may be required.",
            },
        )
        return payment

    if booking.status in {Booking.Status.CANCELLED, Booking.Status.REFUNDED}:
        log_operation(
            category="payment",
            action="payment_after_cancelled",
            status=OperationLog.Status.FAILED,
            entity_type="booking",
            entity_id=booking.public_id,
            booking_id=booking.id,
            details={
                "payment_intent_id": payment_intent_id,
                "booking_status": booking.status,
                "note": "Payment succeeded on cancelled booking; manual refund may be required.",
            },
        )
        return payment

    booking.confirm()
    booking.save(update_fields=["status", "confirmed_at", "updated_at"])
    session = booking.visitor_sessions.order_by("-last_seen_at").first()
    if session:
        log_journey_event(
            session_id=session.session_id,
            event_type="payment_completed",
            step="4",
            cruise_code=booking.cruise.code,
            booking_id=booking.id,
            payload={"public_id": booking.public_id, "source": "server"},
            completed=True,
        )
    send_customer_booking_email.delay(booking.id)
    send_admin_booking_email.delay(booking.id)
    send_admin_sms.delay(booking.id)
    log_operation(
        category="payment",
        action="booking_confirmed",
        entity_type="booking",
        entity_id=booking.public_id,
        booking_id=booking.id,
        details={
            "payment_intent_id": payment_intent_id,
            "checkout_session_id": payment.stripe_checkout_session_id,
        },
    )
    close_competing_sessions_if_sold_out(booking)
    return payment


@transaction.atomic
def confirm_booking_from_payment_intent(payment_intent_id: str, raw_status: str = "succeeded") -> Payment:
    payment = Payment.objects.select_for_update().select_related("booking").get(stripe_payment_intent_id=payment_intent_id)
    return _finalize_successful_payment(payment, payment_intent_id, raw_status)


@transaction.atomic
def confirm_booking_from_checkout_session(session: dict) -> Payment:
    session_id = _stripe_object_id(session.get("id")) or session["id"]
    payment = Payment.objects.select_for_update().select_related("booking").get(stripe_checkout_session_id=session_id)
    payment_intent_id = _stripe_object_id(session.get("payment_intent")) or payment.stripe_payment_intent_id or ""
    return _finalize_successful_payment(payment, payment_intent_id, session.get("status", "complete"))


@transaction.atomic
def expire_booking_from_checkout_session(session_id: str, status: str = "expired") -> None:
    """Stripe прислал checkout.session.expired — освобождаем места."""
    payment = (
        Payment.objects.select_for_update()
        .select_related("booking")
        .filter(stripe_checkout_session_id=session_id)
        .first()
    )
    if not payment:
        return
    payment.status = Payment.Status.CANCELLED
    payment.raw_provider_status = status
    payment.save(update_fields=["status", "raw_provider_status", "updated_at"])
    booking = payment.booking
    if booking.status != Booking.Status.PENDING_PAYMENT:
        return
    booking.cancel(Booking.Status.EXPIRED, reason=Booking.CancelReason.HOLD_EXPIRED)
    booking.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])
    log_operation(
        category="booking",
        action="expired",
        entity_type="booking",
        entity_id=booking.public_id,
        booking_id=booking.id,
        details={"source": "stripe_webhook", "session_id": session_id},
    )


def verify_payment_intent_and_confirm(booking: Booking, payment_intent_id: str) -> Payment:
    intent = retrieve_payment_intent(payment_intent_id)
    if intent["status"] != "succeeded":
        raise ValueError(f"PaymentIntent is not succeeded: {intent['status']}")
    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        stripe_payment_intent_id=payment_intent_id,
        defaults={
            "amount": booking.total_amount,
            "currency": booking.currency,
            "idempotency_key": f"booking:{booking.public_id}:manual-confirm:{payment_intent_id}",
            "raw_provider_status": intent["status"],
        },
    )
    if payment.status != Payment.Status.SUCCEEDED:
        return confirm_booking_from_payment_intent(payment_intent_id, intent["status"])
    return payment


def verify_checkout_session_and_confirm(booking: Booking, session_id: str) -> Payment:
    if booking.status == Booking.Status.CONFIRMED:
        payment = (
            Payment.objects.filter(booking=booking, status=Payment.Status.SUCCEEDED)
            .order_by("-id")
            .first()
        )
        if payment:
            return payment

    session = retrieve_checkout_session(session_id)
    if session["status"] != "complete":
        raise ValueError(f"Checkout Session is not complete: {session['status']}")
    payment_intent_id = _stripe_object_id(session.get("payment_intent"))
    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        stripe_checkout_session_id=session_id,
        defaults={
            "amount": booking.total_amount,
            "currency": booking.currency,
            "idempotency_key": f"booking:{booking.public_id}:manual-confirm:{session_id}"[:160],
            "raw_provider_status": session["status"],
            "stripe_payment_intent_id": payment_intent_id,
        },
    )
    if payment_intent_id and not payment.stripe_payment_intent_id:
        payment.stripe_payment_intent_id = payment_intent_id
        payment.save(update_fields=["stripe_payment_intent_id", "updated_at"])
    if payment.status != Payment.Status.SUCCEEDED:
        return confirm_booking_from_checkout_session(session)
    return payment


def mark_payment_failed(payment_intent_id: str, status: str) -> None:
    payment = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).select_related("booking").first()
    Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).update(
        status=Payment.Status.FAILED,
        raw_provider_status=status,
        updated_at=timezone.now(),
    )
    if payment:
        log_operation(
            category="payment",
            action="payment_failed",
            status=OperationLog.Status.FAILED,
            entity_type="payment",
            entity_id=payment_intent_id,
            booking_id=payment.booking_id,
            details={"raw_status": status},
        )


