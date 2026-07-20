from __future__ import annotations

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.audit.models import OperationLog
from apps.audit.services import log_operation
from apps.bookings.models import Booking
from apps.cruises.time_utils import format_time_range

from .brevo_client import send_transactional_email
from .clicksend_client import send_sms
from .models import EmailLog, SmsLog, TelegramLog
from .telegram_client import send_telegram_message


def booking_context(booking: Booking) -> dict:
    """Email context. Times always from booking record (set from CruiseSchedule at hold time)."""
    payment = booking.payments.order_by("-created_at").first()
    cruise_time = format_time_range(booking.start_time, booking.end_time)
    return {
        "booking": booking,
        "customer_name": booking.customer.full_name,
        "booking_public_id": booking.public_id,
        "cruise_name": booking.cruise.name,
        "cruise_date": booking.cruise_date,
        "date_formatted": booking.cruise_date.strftime("%B %d, %Y"),
        "cruise_time": cruise_time,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "adults_count": booking.adults_count,
        "children_count": booking.children_count,
        "adult_total": booking.adults_count * booking.adult_unit_price,
        "child_total": booking.children_count * booking.child_unit_price,
        "total_amount": booking.total_amount,
        "currency": booking.currency,
        "payment_id": payment.stripe_payment_intent_id if payment else "",
        "meeting_point": settings.MEETING_POINT,
        "meeting_point_maps_url": settings.MEETING_POINT_MAPS_URL,
        "support_email": settings.SUPPORT_EMAIL,
        "support_phone": settings.SUPPORT_PHONE,
        "booking_already_paid": True,
        "site_base_url": settings.SITE_BASE_URL,
    }


def _log_email_result(*, booking: Booking, template_code: str, recipient: str, log: EmailLog) -> None:
    if log.status == EmailLog.Status.SENT:
        log_operation(
            category="notification",
            action="email_sent",
            entity_type="email",
            entity_id=str(log.id),
            booking_id=booking.id,
            details={"template": template_code, "recipient": recipient, "provider_message_id": log.provider_message_id},
        )
    else:
        log_operation(
            category="notification",
            action="email_failed",
            status=OperationLog.Status.FAILED,
            entity_type="email",
            entity_id=str(log.id),
            booking_id=booking.id,
            details={"template": template_code, "recipient": recipient},
            error=log.error,
        )


def send_booking_email(*, booking: Booking, recipient: str, template_code: str, subject: str) -> EmailLog:
    context = booking_context(booking)
    html = render_to_string(f"email/{template_code}.html", context)
    log = EmailLog.objects.create(
        booking=booking,
        recipient=recipient,
        template_code=template_code,
        subject=subject,
        payload_snapshot={"booking_public_id": booking.public_id, "template_code": template_code, "cruise_time": context["cruise_time"]},
    )
    try:
        log.provider_message_id = send_transactional_email(to_email=recipient, subject=subject, html=html)
        log.status = EmailLog.Status.SENT
        log.sent_at = timezone.now()
    except Exception as exc:
        log.status = EmailLog.Status.FAILED
        log.error = str(exc)
    log.save(update_fields=["provider_message_id", "status", "sent_at", "error"])
    _log_email_result(booking=booking, template_code=template_code, recipient=recipient, log=log)
    return log


def send_customer_ticket(booking: Booking) -> EmailLog:
    return send_booking_email(
        booking=booking,
        recipient=booking.customer.email,
        template_code="booking_customer",
        subject=f"Turtle Cruise booking #{booking.public_id}",
    )


def send_admin_booking_notice(booking: Booking) -> list[EmailLog]:
    logs = []
    for recipient in settings.ADMIN_EMAIL_RECIPIENTS:
        logs.append(
            send_booking_email(
                booking=booking,
                recipient=recipient,
                template_code="booking_admin",
                subject=f"New booking #{booking.public_id}",
            )
        )
    return logs


def _admin_alert_message(booking: Booking) -> str:
    cruise_time = format_time_range(booking.start_time, booking.end_time)
    return (
        f"New booking #{booking.public_id}\n"
        f"{booking.cruise.name}\n"
        f"Date: {booking.cruise_date}\n"
        f"Time: {cruise_time}\n"
        f"Adults: {booking.adults_count}"
        f"{', Children: ' + str(booking.children_count) if booking.children_count else ''}\n"
        f"Total: {booking.total_amount} {booking.currency}\n"
        f"{booking.customer.full_name} | {booking.customer.phone}"
    )


def send_admin_booking_sms(booking: Booking) -> list[SmsLog]:
    message = _admin_alert_message(booking)
    logs = []
    for recipient in settings.ADMIN_SMS_RECIPIENTS:
        log = SmsLog.objects.create(booking=booking, recipient=recipient, message=message)
        try:
            log.provider_message_id = send_sms(to_phone=recipient, body=message)
            log.status = SmsLog.Status.SENT
            log.sent_at = timezone.now()
            log_operation(
                category="notification",
                action="sms_sent",
                entity_type="sms",
                entity_id=str(log.id),
                booking_id=booking.id,
                details={"recipient": recipient, "provider_message_id": log.provider_message_id},
            )
        except Exception as exc:
            log.status = SmsLog.Status.FAILED
            log.error = str(exc)
            log_operation(
                category="notification",
                action="sms_failed",
                status=OperationLog.Status.FAILED,
                entity_type="sms",
                entity_id=str(log.id),
                booking_id=booking.id,
                details={"recipient": recipient},
                error=str(exc),
            )
        log.save(update_fields=["provider_message_id", "status", "sent_at", "error"])
        logs.append(log)
    return logs


def send_admin_booking_telegram(booking: Booking) -> list[TelegramLog]:
    message = _admin_alert_message(booking)
    logs = []
    for chat_id in settings.TELEGRAM_ADMIN_CHAT_IDS:
        log = TelegramLog.objects.create(booking=booking, recipient=chat_id, message=message)
        try:
            log.provider_message_id = send_telegram_message(chat_id=chat_id, text=message)
            log.status = TelegramLog.Status.SENT
            log.sent_at = timezone.now()
            log_operation(category="notification", action="telegram_sent", entity_type="telegram", entity_id=str(log.id), booking_id=booking.id)
        except Exception as exc:
            log.status = TelegramLog.Status.FAILED
            log.error = str(exc)
            log_operation(
                category="notification",
                action="telegram_failed",
                status=OperationLog.Status.FAILED,
                entity_type="telegram",
                entity_id=str(log.id),
                booking_id=booking.id,
                error=str(exc),
            )
        log.save(update_fields=["provider_message_id", "status", "sent_at", "error"])
        logs.append(log)
    return logs


def send_admin_instant_alert(booking: Booking) -> dict:
    channel = settings.ADMIN_NOTIFY_CHANNEL
    result = {"channel": channel, "telegram": [], "sms": []}

    if channel in {"sms", "both"}:
        if settings.ADMIN_SMS_RECIPIENTS and settings.CLICKSEND_USERNAME and settings.CLICKSEND_API_KEY:
            result["sms"] = [log.id for log in send_admin_booking_sms(booking)]
        else:
            log_operation(
                category="notification",
                action="sms_skipped",
                status=OperationLog.Status.SKIPPED,
                entity_type="booking",
                entity_id=booking.public_id,
                booking_id=booking.id,
                details={"reason": "clicksend_not_configured"},
            )

    if channel in {"telegram", "both"} and settings.TELEGRAM_ADMIN_CHAT_IDS:
        result["telegram"] = [log.id for log in send_admin_booking_telegram(booking)]

    if channel == "none":
        log_operation(category="notification", action="admin_alert_disabled", status=OperationLog.Status.SKIPPED, entity_type="booking", entity_id=booking.public_id, booking_id=booking.id)

    return result
