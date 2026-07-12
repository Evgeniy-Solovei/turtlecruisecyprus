from django.conf import settings
from config.celery import app

from apps.bookings.models import Booking

from .models import EmailLog, SmsLog
from .services import send_admin_booking_notice, send_admin_booking_sms, send_admin_instant_alert, send_customer_ticket


@app.task
def send_customer_booking_email(booking_id: int):
    return send_customer_ticket(Booking.objects.select_related("customer", "cruise").get(id=booking_id)).id


@app.task
def send_admin_booking_email(booking_id: int):
    return [log.id for log in send_admin_booking_notice(Booking.objects.select_related("customer", "cruise").get(id=booking_id))]


@app.task
def send_admin_sms(booking_id: int):
    booking = Booking.objects.select_related("customer", "cruise").get(id=booking_id)
    if settings.ADMIN_NOTIFY_CHANNEL == "both":
        return send_admin_instant_alert(booking)
    return [log.id for log in send_admin_booking_sms(booking)]


@app.task
def retry_failed_notifications() -> dict:
    # Explicit retry policy will be tightened after real provider responses are observed.
    return {"failed_email": EmailLog.objects.filter(status=EmailLog.Status.FAILED).count(), "failed_sms": SmsLog.objects.filter(status=SmsLog.Status.FAILED).count()}
