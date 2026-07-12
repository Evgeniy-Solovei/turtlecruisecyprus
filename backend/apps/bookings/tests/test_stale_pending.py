from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import BookingHoldInput, create_booking_hold, expire_stale_pending_bookings
from apps.cruises.models import Cruise, CruiseSchedule
from apps.payments.models import Payment
from apps.payments.stripe_client import STRIPE_CHECKOUT_MAX_HOURS


class StalePendingBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cruise = Cruise.objects.create(
            code="morning",
            name="Morning Cruise",
            default_adult_price=45,
            default_child_price=25,
            default_capacity=40,
        )
        for weekday in range(7):
            CruiseSchedule.objects.create(
                cruise=cls.cruise,
                weekday=weekday,
                start_time="09:30",
                end_time="14:00",
            )

    def _hold(self, email: str) -> Booking:
        return create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=date.today() + timedelta(days=40),
                adults_count=1,
                children_count=0,
                first_name="Test",
                last_name="User",
                email=email,
                phone="+35700000999",
            )
        )

    def test_stale_open_checkout_marked_expired(self):
        booking = self._hold("stale-open@example.com")
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            currency=booking.currency,
            stripe_checkout_session_id="cs_stale_open",
            idempotency_key=f"booking:{booking.public_id}:stale-open",
            status=Payment.Status.REQUIRES_PAYMENT_METHOD,
        )
        stale_time = timezone.now() - timedelta(hours=STRIPE_CHECKOUT_MAX_HOURS, minutes=5)
        Payment.objects.filter(pk=payment.pk).update(created_at=stale_time)

        with patch("apps.payments.stripe_client.retrieve_checkout_session") as mock_session:
            mock_session.return_value = {"status": "open", "id": "cs_stale_open"}
            with patch("apps.payments.stripe_client.expire_checkout_session"):
                count = expire_stale_pending_bookings()

        self.assertEqual(count, 1)
        booking.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertEqual(booking.cancel_reason, Booking.CancelReason.HOLD_EXPIRED)
        self.assertEqual(payment.status, Payment.Status.CANCELLED)

    def test_recent_pending_not_expired(self):
        booking = self._hold("fresh@example.com")
        Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            currency=booking.currency,
            stripe_checkout_session_id="cs_fresh",
            idempotency_key=f"booking:{booking.public_id}:fresh",
            status=Payment.Status.REQUIRES_PAYMENT_METHOD,
        )
        count = expire_stale_pending_bookings()
        self.assertEqual(count, 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING_PAYMENT)

    def test_pending_without_payment_session_expires(self):
        booking = self._hold("no-pay@example.com")
        Booking.objects.filter(pk=booking.pk).update(
            created_at=timezone.now() - timedelta(hours=STRIPE_CHECKOUT_MAX_HOURS, minutes=1)
        )
        count = expire_stale_pending_bookings()
        self.assertEqual(count, 1)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
