from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase

from apps.bookings.models import Booking
from apps.bookings.services import BookingHoldInput, close_competing_sessions_if_sold_out, create_booking_hold
from apps.cruises.models import Cruise, CruiseDateOverride, CruiseSchedule
from apps.payments.models import Payment
from apps.payments.services import confirm_booking_from_payment_intent, create_or_get_payment_intent


class SoldOutSessionCloseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cruise = Cruise.objects.create(
            code="morning",
            name="Morning Cruise",
            default_adult_price=45,
            default_child_price=25,
            default_capacity=3,
        )
        for weekday in range(7):
            CruiseSchedule.objects.create(
                cruise=cls.cruise,
                weekday=weekday,
                start_time="09:30",
                end_time="14:00",
            )
        cls.target_date = date.today() + timedelta(days=50)

    def _hold(self, email: str, seats: int = 1) -> Booking:
        return create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=self.target_date,
                adults_count=seats,
                children_count=0,
                first_name="Test",
                last_name="User",
                email=email,
                phone="+35700000100",
            )
        )

    @patch("apps.payments.stripe_client.expire_checkout_session")
    @patch("apps.payments.services.create_checkout_session")
    def test_sold_out_closes_other_pending_sessions(self, mock_create, mock_expire):
        session_counter = {"n": 0}

        def next_session(**kwargs):
            session_counter["n"] += 1
            return {
                "id": f"cs_test_{session_counter['n']}",
                "client_secret": "cs_test_secret",
                "status": "open",
                "payment_intent": None,
            }

        mock_create.side_effect = next_session

        holds = [self._hold(f"user{i}@example.com") for i in range(3)]
        for booking in holds:
            create_or_get_payment_intent(booking)

        for booking in holds[:2]:
            booking.confirm()
            booking.save(update_fields=["status", "confirmed_at", "updated_at"])

        # Симулируем «41-ю» бронь: confirmed уже заполнил capacity, pending ещё открыт.
        Booking.objects.create(
            customer=holds[0].customer,
            cruise=self.cruise,
            cruise_date=self.target_date,
            start_time=holds[0].start_time,
            end_time=holds[0].end_time,
            adults_count=1,
            children_count=0,
            total_seats=1,
            adult_unit_price=holds[0].adult_unit_price,
            child_unit_price=holds[0].child_unit_price,
            total_amount=holds[0].adult_unit_price,
            status=Booking.Status.CONFIRMED,
            confirmed_at=holds[0].confirmed_at,
        )

        last_pending = holds[2]
        closed = close_competing_sessions_if_sold_out(holds[1])
        self.assertEqual(closed, 1)

        last_pending.refresh_from_db()
        self.assertEqual(last_pending.status, Booking.Status.EXPIRED)
        self.assertEqual(last_pending.cancel_reason, Booking.CancelReason.SOLD_OUT)
        mock_expire.assert_called_once_with("cs_test_3")

        override = CruiseDateOverride.objects.get(cruise=self.cruise, date=self.target_date)
        self.assertTrue(override.is_closed)

    @patch("apps.notifications.tasks.send_admin_sms.delay")
    @patch("apps.notifications.tasks.send_admin_booking_email.delay")
    @patch("apps.notifications.tasks.send_customer_booking_email.delay")
    @patch("apps.payments.services.close_competing_sessions_if_sold_out")
    def test_confirm_triggers_sold_out_sweep(self, mock_close, mock_customer, mock_admin, mock_sms):
        booking = self._hold("pay@example.com")
        Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            currency=booking.currency,
            stripe_payment_intent_id="pi_confirm",
            idempotency_key=f"booking:{booking.public_id}:confirm",
            status=Payment.Status.REQUIRES_PAYMENT_METHOD,
        )
        confirm_booking_from_payment_intent("pi_confirm")
        mock_close.assert_called_once_with(booking)
