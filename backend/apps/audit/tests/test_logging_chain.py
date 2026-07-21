from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.audit.models import ApiRequestLog, OperationLog
from apps.audit.trace import build_booking_trace
from apps.bookings.models import Booking
from apps.bookings.services import BookingHoldInput, create_booking_hold
from apps.cruises.models import Cruise, CruiseSchedule
from apps.notifications.models import EmailLog, SmsLog
from apps.notifications.services import send_admin_booking_sms, send_customer_ticket
from apps.payments.services import create_or_get_payment_intent


class BookingChainLoggingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cruise = Cruise.objects.create(
            code="morning",
            name="Morning",
            default_adult_price=45,
            default_child_price=25,
            default_capacity=10,
            legacy_wp_service_id=99002,
        )
        for weekday in range(7):
            CruiseSchedule.objects.create(cruise=cls.cruise, weekday=weekday, start_time="09:30", end_time="14:00")

    def test_hold_creates_operation_log(self):
        target = date.today() + timedelta(days=20)
        with self.captureOnCommitCallbacks(execute=True):
            booking = create_booking_hold(
                BookingHoldInput(
                    cruise_code="morning",
                    cruise_date=target,
                    adults_count=2,
                    children_count=0,
                    first_name="Log",
                    last_name="Test",
                    email="logtest@example.com",
                    phone="+35700000001",
                    session_id="sess-001",
                )
            )
        self.assertTrue(OperationLog.objects.filter(booking=booking, action="hold_created").exists())

    def test_api_middleware_logs_request(self):
        target = date.today() + timedelta(days=21)
        self.client.get(f"/api/v1/cruises/morning/availability/?date={target.isoformat()}")
        self.assertTrue(ApiRequestLog.objects.filter(path__contains="/availability/").exists())

    @patch("apps.notifications.services.send_transactional_email", return_value="msg-1")
    def test_email_logs_operation(self, _mock):
        target = date.today() + timedelta(days=22)
        booking = create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=target,
                adults_count=1,
                children_count=0,
                first_name="Mail",
                last_name="Test",
                email="mailtest@example.com",
                phone="+35700000002",
            )
        )
        send_customer_ticket(booking)
        self.assertTrue(EmailLog.objects.filter(booking=booking).exists())
        self.assertTrue(OperationLog.objects.filter(booking=booking, action="email_sent").exists())

    @override_settings(
        ADMIN_SMS_RECIPIENTS=["+35797719450"],
        CLICKSEND_USERNAME="test",
        CLICKSEND_API_KEY="test",
    )
    @patch("apps.notifications.services.send_sms", return_value="sms-1")
    def test_sms_logs_operation_with_time(self, _mock):
        target = date.today() + timedelta(days=23)
        booking = create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=target,
                adults_count=1,
                children_count=0,
                first_name="Sms",
                last_name="Test",
                email="smstest@example.com",
                phone="+35700000003",
            )
        )
        logs = send_admin_booking_sms(booking)
        self.assertEqual(len(logs), 1)
        self.assertIn("9:30 – 14:00", logs[0].message)
        self.assertTrue(OperationLog.objects.filter(booking=booking, action="sms_sent").exists())

    @patch(
        "apps.payments.services.create_checkout_session",
        return_value={"id": "cs_test", "client_secret": "sec", "status": "open", "payment_intent": None},
    )
    def test_payment_intent_logs_operation(self, _mock):
        target = date.today() + timedelta(days=24)
        booking = create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=target,
                adults_count=1,
                children_count=0,
                first_name="Pay",
                last_name="Test",
                email="paytest@example.com",
                phone="+35700000004",
            )
        )
        create_or_get_payment_intent(booking)
        self.assertTrue(OperationLog.objects.filter(booking=booking, action="checkout_session_created").exists())

    def test_booking_trace_endpoint(self):
        target = date.today() + timedelta(days=25)
        with self.captureOnCommitCallbacks(execute=True):
            booking = create_booking_hold(
                BookingHoldInput(
                    cruise_code="morning",
                    cruise_date=target,
                    adults_count=1,
                    children_count=0,
                    first_name="Trace",
                    last_name="Test",
                    email="trace@example.com",
                    phone="+35700000005",
                    session_id="sess-trace",
                )
            )
        response = self.client.get(f"/api/v1/bookings/{booking.public_id}/trace/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["found"])
        self.assertGreaterEqual(payload["summary"]["operations"], 1)

    def test_trace_builder(self):
        target = date.today() + timedelta(days=26)
        booking = create_booking_hold(
            BookingHoldInput(
                cruise_code="morning",
                cruise_date=target,
                adults_count=1,
                children_count=0,
                first_name="Trace2",
                last_name="Test",
                email="trace2@example.com",
                phone="+35700000006",
            )
        )
        trace = build_booking_trace(booking.public_id)
        self.assertTrue(trace["found"])
        self.assertEqual(trace["booking"]["start_time"], "09:30:00")
        self.assertEqual(trace["booking"]["cruise_time"], "9:30 – 14:00")
