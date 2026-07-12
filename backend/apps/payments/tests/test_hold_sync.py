from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import BookingHoldInput, create_booking_hold
from apps.cruises.models import Cruise, CruiseSchedule
from apps.payments.models import Payment
from apps.payments.services import (
    checkout_deadline_for_payment,
    confirm_booking_from_payment_intent,
    create_or_get_payment_intent,
    expire_booking_from_checkout_session,
)
from apps.payments.stripe_client import STRIPE_CHECKOUT_MAX_HOURS, checkout_session_expires_at


class StripeCheckoutLifetimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cruise = Cruise.objects.create(
            code="morning",
            name="Morning Cruise",
            default_adult_price=45,
            default_child_price=25,
            default_capacity=10,
        )
        for weekday in range(7):
            CruiseSchedule.objects.create(
                cruise=cls.cruise,
                weekday=weekday,
                start_time="09:30",
                end_time="14:00",
            )

    def _create_hold(self) -> Booking:
        target = date.today() + timedelta(days=40)
        return create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=target,
                adults_count=2,
                children_count=0,
                first_name="Hold",
                last_name="Sync",
                email="hold@example.com",
                phone="+35700000200",
            )
        )

    @patch("apps.payments.services.create_checkout_session")
    def test_checkout_session_uses_stripe_max_lifetime(self, mock_create):
        booking = self._create_hold()
        mock_create.return_value = {
            "id": "cs_test_123",
            "client_secret": "cs_test_secret",
            "status": "open",
            "payment_intent": None,
        }
        before = timezone.now()
        payment = create_or_get_payment_intent(booking)
        expires_unix = mock_create.call_args.kwargs["expires_at"]
        expected = checkout_session_expires_at()
        self.assertAlmostEqual(expires_unix, expected, delta=120)
        deadline = checkout_deadline_for_payment(payment)
        self.assertGreaterEqual((deadline - before).total_seconds(), (STRIPE_CHECKOUT_MAX_HOURS - 1) * 3600)

    @patch("apps.payments.services.create_checkout_session")
    def test_stripe_webhook_expired_marks_booking_expired(self, mock_create):
        mock_create.return_value = {
            "id": "cs_test_expire",
            "client_secret": "cs_test",
            "status": "open",
            "payment_intent": None,
        }
        booking = self._create_hold()
        create_or_get_payment_intent(booking)

        expire_booking_from_checkout_session("cs_test_expire")

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.status, Payment.Status.CANCELLED)

    @patch("apps.notifications.tasks.send_admin_sms.delay")
    @patch("apps.notifications.tasks.send_admin_booking_email.delay")
    @patch("apps.notifications.tasks.send_customer_booking_email.delay")
    def test_late_payment_still_confirms(self, mock_customer, mock_admin, mock_sms):
        booking = self._create_hold()
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            currency=booking.currency,
            stripe_payment_intent_id="pi_late_123",
            idempotency_key=f"booking:{booking.public_id}:test",
            status=Payment.Status.REQUIRES_PAYMENT_METHOD,
        )
        booking.cancel(Booking.Status.EXPIRED, reason=Booking.CancelReason.HOLD_EXPIRED)
        booking.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])

        confirm_booking_from_payment_intent("pi_late_123")

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        mock_customer.assert_called_once_with(booking.id)

    @patch("apps.payments.services.create_checkout_session")
    def test_reuses_existing_open_checkout_session(self, mock_create):
        booking = self._create_hold()
        mock_create.return_value = {
            "id": "cs_test_late",
            "client_secret": "cs_test",
            "status": "open",
            "payment_intent": None,
        }
        payment = create_or_get_payment_intent(booking)
        mock_create.assert_called_once()
        deadline = checkout_deadline_for_payment(payment)
        self.assertGreater(deadline, timezone.now())
