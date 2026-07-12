from __future__ import annotations

from datetime import date, timedelta

from django.test import TestCase

from apps.bookings.models import Booking
from apps.bookings.services import BookingHoldInput, create_booking_hold
from apps.cruises.models import Cruise, CruiseSchedule


class BookingStatusApiTests(TestCase):
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

    def test_booking_status_endpoint(self):
        booking = create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=date.today() + timedelta(days=30),
                adults_count=1,
                children_count=0,
                first_name="Api",
                last_name="Test",
                email="api@example.com",
                phone="+35700000300",
            )
        )
        response = self.client.get(f"/api/v1/bookings/{booking.public_id}/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], Booking.Status.PENDING_PAYMENT)
        self.assertTrue(data["payable"])

        booking.cancel(Booking.Status.EXPIRED, reason=Booking.CancelReason.SOLD_OUT)
        booking.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])

        response = self.client.get(f"/api/v1/bookings/{booking.public_id}/status/")
        data = response.json()
        self.assertEqual(data["cancel_reason"], Booking.CancelReason.SOLD_OUT)
        self.assertFalse(data["payable"])
