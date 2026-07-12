from __future__ import annotations

from datetime import date, timedelta

from django.test import TestCase

from apps.bookings.models import Booking
from apps.bookings.services import BookingError, BookingHoldInput, create_booking_hold
from apps.cruises.models import Cruise, CruiseDateOverride, CruiseSchedule


class AvailabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cruise = Cruise.objects.create(
            code="morning",
            name="Morning Cruise",
            default_adult_price=45,
            default_child_price=25,
            default_capacity=10,
            legacy_wp_service_id=9991,
        )
        for weekday in range(7):
            CruiseSchedule.objects.create(
                cruise=cls.cruise,
                weekday=weekday,
                start_time="09:30",
                end_time="14:00",
            )

    def test_availability_endpoint(self):
        target = date.today() + timedelta(days=30)
        response = self.client.get(f"/api/v1/cruises/morning/availability/?date={target.isoformat()}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["capacity"], 10)
        self.assertEqual(payload["available"], 10)
        self.assertTrue(payload["bookable"])

    def test_closed_date_override(self):
        target = date.today() + timedelta(days=31)
        CruiseDateOverride.objects.create(cruise=self.cruise, date=target, is_closed=True)
        response = self.client.get(f"/api/v1/cruises/morning/availability/?date={target.isoformat()}")
        self.assertFalse(response.json()["bookable"])

    def test_pending_hold_does_not_reduce_available_seats(self):
        target = date.today() + timedelta(days=32)
        create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=target,
                adults_count=3,
                children_count=0,
                first_name="Test",
                last_name="User",
                email="test@example.com",
                phone="+35700000000",
            )
        )
        response = self.client.get(f"/api/v1/cruises/morning/availability/?date={target.isoformat()}")
        payload = response.json()
        self.assertEqual(payload["booked"], 0)
        self.assertEqual(payload["pending"], 3)
        self.assertEqual(payload["available"], 10)

    def test_capacity_limit_after_confirmed_fill(self):
        target = date.today() + timedelta(days=33)
        for i in range(10):
            booking = create_booking_hold(
                BookingHoldInput(
                    cruise_code="morning",
                    cruise_date=target,
                    adults_count=1,
                    children_count=0,
                    first_name="Test",
                    last_name=str(i),
                    email=f"test{i}@example.com",
                    phone=f"+3570000000{i}",
                )
            )
            booking.confirm()
            booking.save(update_fields=["status", "confirmed_at", "updated_at"])
        with self.assertRaises(BookingError):
            create_booking_hold(
                BookingHoldInput(
                    cruise_code="morning",
                    cruise_date=target,
                    adults_count=1,
                    children_count=0,
                    first_name="Overflow",
                    last_name="User",
                    email="overflow@example.com",
                    phone="+35700000099",
                )
            )

    def test_wp_compat_availability(self):
        target = date.today() + timedelta(days=35)
        response = self.client.post(
            "/wp-admin/admin-ajax.php",
            {
                "action": "tc_get_availability",
                "date": target.isoformat(),
                "cruise_type": "morning",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("available", payload["data"])
