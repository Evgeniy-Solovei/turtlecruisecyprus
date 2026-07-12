from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.cruises.models import Cruise, CruiseDateOverride
from apps.cruises.selectors import get_date_override, get_schedule_for_date
from apps.cruises.services import effective_capacity, effective_prices

from apps.audit.models import OperationLog
from apps.audit.services import log_journey_event, log_operation

from .models import Booking, Customer
from .selectors import confirmed_seats_for_date, is_date_sold_out


class BookingError(ValueError):
    pass


@dataclass(frozen=True)
class BookingHoldInput:
    cruise_code: str
    cruise_date: date
    adults_count: int
    children_count: int
    first_name: str
    last_name: str
    email: str
    phone: str
    customer_notes: str = ""
    source: str = "web"
    session_id: str = ""


def create_booking_hold(data: BookingHoldInput) -> Booking:
    if data.adults_count < 1:
        raise BookingError("At least one adult is required.")
    if data.children_count < 0:
        raise BookingError("Children count cannot be negative.")

    with transaction.atomic():
        cruise = Cruise.objects.select_for_update().get(code=data.cruise_code, is_active=True)
        schedule = get_schedule_for_date(cruise, data.cruise_date)
        override = get_date_override(cruise, data.cruise_date)
        if not schedule or (override and override.is_closed):
            raise BookingError("Cruise is not bookable for this date.")
        if data.children_count and not cruise.child_allowed:
            raise BookingError("Children are not allowed for this cruise.")

        seats = data.adults_count + data.children_count
        if is_date_sold_out(cruise, data.cruise_date):
            raise BookingError("Not enough seats available.")

        adult_price, child_price = effective_prices(cruise, data.cruise_date)
        total_amount = (Decimal(data.adults_count) * adult_price) + (Decimal(data.children_count) * child_price)
        customer, _ = Customer.objects.update_or_create(
            email=data.email.strip().lower(),
            defaults={
                "first_name": data.first_name.strip(),
                "last_name": data.last_name.strip(),
                "phone": data.phone.strip(),
            },
        )
        booking = Booking.objects.create(
            customer=customer,
            cruise=cruise,
            cruise_date=data.cruise_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            adults_count=data.adults_count,
            children_count=data.children_count,
            total_seats=seats,
            adult_unit_price=adult_price,
            child_unit_price=child_price,
            total_amount=total_amount,
            customer_notes=data.customer_notes,
            source=data.source,
        )
        log_operation(
            category="booking",
            action="hold_created",
            entity_type="booking",
            entity_id=booking.public_id,
            booking_id=booking.id,
            session_id=data.session_id,
            details={
                "cruise": cruise.code,
                "date": str(data.cruise_date),
                "seats": seats,
                "total": str(total_amount),
                "cruise_time": f"{schedule.start_time}-{schedule.end_time}",
            },
        )
        if data.session_id:
            log_journey_event(
                session_id=data.session_id,
                event_type="booking_created",
                step="3",
                cruise_code=cruise.code,
                booking_id=booking.id,
                payload={"public_id": booking.public_id, "total": str(total_amount)},
            )
        return booking


def cancel_booking(booking: Booking, *, status: str = Booking.Status.CANCELLED) -> Booking:
    if booking.status == Booking.Status.CONFIRMED:
        raise BookingError("Confirmed bookings must be cancelled by admin workflow.")
    booking.cancel(status, reason=Booking.CancelReason.USER_CANCELLED)
    booking.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])
    log_operation(category="booking", action="cancelled", entity_type="booking", entity_id=booking.public_id, booking_id=booking.id, details={"status": booking.status})
    return booking


def close_competing_sessions_if_sold_out(triggering_booking: Booking) -> int:
    """Когда подтверждённых мест >= capacity — закрываем Stripe-сессии остальных pending."""
    cruise = triggering_booking.cruise
    cruise_date = triggering_booking.cruise_date
    capacity = effective_capacity(cruise, cruise_date)
    confirmed = confirmed_seats_for_date(cruise, cruise_date)
    if confirmed < capacity:
        return 0

    CruiseDateOverride.objects.update_or_create(
        cruise=cruise,
        date=cruise_date,
        defaults={"is_closed": True, "note": "Auto-closed: all seats confirmed."},
    )

    pending_bookings = Booking.objects.filter(
        cruise=cruise,
        cruise_date=cruise_date,
        status=Booking.Status.PENDING_PAYMENT,
    )
    closed = 0
    for booking in pending_bookings:
        if _close_pending_booking_for_sold_out(booking):
            closed += 1

    if closed:
        log_operation(
            category="booking",
            action="sold_out_sessions_closed",
            entity_type="booking",
            entity_id=triggering_booking.public_id,
            booking_id=triggering_booking.id,
            details={
                "cruise": cruise.code,
                "date": str(cruise_date),
                "confirmed_seats": confirmed,
                "capacity": capacity,
                "closed_pending": closed,
            },
        )
    return closed


def _close_pending_booking_for_sold_out(booking: Booking) -> bool:
    from apps.payments.models import Payment
    from apps.payments.stripe_client import StripeNotConfigured, expire_checkout_session

    payment = (
        Payment.objects.filter(
            booking=booking,
            provider="stripe",
            status__in=[
                Payment.Status.REQUIRES_PAYMENT_METHOD,
                Payment.Status.REQUIRES_ACTION,
                Payment.Status.PROCESSING,
            ],
        )
        .exclude(stripe_checkout_session_id="")
        .order_by("-created_at")
        .first()
    )

    if payment and payment.stripe_checkout_session_id:
        try:
            expire_checkout_session(payment.stripe_checkout_session_id)
        except StripeNotConfigured:
            pass
        except Exception as exc:
            log_operation(
                category="payment",
                action="checkout_session_expire_failed",
                status=OperationLog.Status.FAILED,
                entity_type="payment",
                entity_id=payment.stripe_checkout_session_id,
                booking_id=booking.id,
                details={"error": str(exc)},
            )
        payment.status = Payment.Status.CANCELLED
        payment.raw_provider_status = "expired"
        payment.save(update_fields=["status", "raw_provider_status", "updated_at"])

    booking.cancel(Booking.Status.EXPIRED, reason=Booking.CancelReason.SOLD_OUT)
    booking.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])
    log_operation(
        category="booking",
        action="expired",
        entity_type="booking",
        entity_id=booking.public_id,
        booking_id=booking.id,
        details={"source": "sold_out", "cancel_reason": Booking.CancelReason.SOLD_OUT},
    )
    return True


def expire_stale_pending_bookings() -> int:
    """
    Закрывает pending-брони, у которых истёк срок Stripe Checkout (24 ч).

    Основной путь — webhook checkout.session.expired.
    Эта задача — запасной: если webhook не пришёл, бронь всё равно станет «Истекло удержание».
    Не трогает sold out — те уже закрыты через close_competing_sessions_if_sold_out.
    """
    from apps.payments.models import Payment
    from apps.payments.services import expire_booking_from_checkout_session
    from apps.payments.stripe_client import (
        STRIPE_CHECKOUT_MAX_HOURS,
        StripeNotConfigured,
        expire_checkout_session,
        retrieve_checkout_session,
    )

    open_statuses = {
        Payment.Status.REQUIRES_PAYMENT_METHOD,
        Payment.Status.REQUIRES_ACTION,
        Payment.Status.PROCESSING,
    }
    cutoff = timezone.now() - timedelta(hours=STRIPE_CHECKOUT_MAX_HOURS)
    count = 0

    pending_bookings = Booking.objects.filter(status=Booking.Status.PENDING_PAYMENT)
    for booking in pending_bookings.iterator():
        payment = (
            Payment.objects.filter(booking=booking, status__in=open_statuses)
            .order_by("-created_at")
            .first()
        )

        if payment:
            if payment.created_at >= cutoff:
                continue
            session_id = payment.stripe_checkout_session_id
            if session_id:
                try:
                    session = retrieve_checkout_session(session_id)
                    if session.get("status") == "expired":
                        expire_booking_from_checkout_session(session_id)
                        count += 1
                        continue
                    if session.get("status") == "open":
                        try:
                            expire_checkout_session(session_id)
                        except StripeNotConfigured:
                            pass
                except StripeNotConfigured:
                    pass
            _expire_pending_booking_hold(booking, payment=payment, source="stale_checkout_cleanup")
            count += 1
            continue

        if booking.created_at < cutoff:
            _expire_pending_booking_hold(booking, payment=None, source="stale_booking_cleanup")
            count += 1

    return count


def _expire_pending_booking_hold(
    booking: Booking,
    *,
    payment=None,
    source: str,
) -> None:
    from apps.payments.models import Payment

    if payment:
        payment.status = Payment.Status.CANCELLED
        payment.raw_provider_status = "expired"
        payment.save(update_fields=["status", "raw_provider_status", "updated_at"])

    booking.cancel(Booking.Status.EXPIRED, reason=Booking.CancelReason.HOLD_EXPIRED)
    booking.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])
    log_operation(
        category="booking",
        action="expired",
        entity_type="booking",
        entity_id=booking.public_id,
        booking_id=booking.id,
        details={"source": source, "cancel_reason": Booking.CancelReason.HOLD_EXPIRED},
    )
