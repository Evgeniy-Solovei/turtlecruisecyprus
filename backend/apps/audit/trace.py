from __future__ import annotations

from apps.audit.models import ApiRequestLog, JourneyEvent, OperationLog, PageView
from apps.cruises.time_utils import format_time_range

from apps.bookings.models import Booking
from apps.notifications.models import EmailLog, SmsLog, TelegramLog
from apps.payments.models import Payment, WebhookLog


def build_booking_trace(public_id: str) -> dict:
    booking = Booking.objects.select_related("customer", "cruise").filter(public_id=public_id).first()
    if not booking:
        return {"found": False, "public_id": public_id}

    sessions = list(booking.visitor_sessions.order_by("-last_seen_at").values())
    session_ids = [s["id"] for s in sessions]
    page_views = list(
        PageView.objects.filter(session_id__in=session_ids)
        .order_by("entered_at")
        .values(
            "entered_at",
            "left_at",
            "path",
            "page_title",
            "duration_ms",
            "scroll_depth_pct",
            "session__session_id",
            "view_id",
        )
    )
    journey = list(
        JourneyEvent.objects.filter(booking=booking)
        .order_by("created_at")
        .values("created_at", "event_type", "step", "cruise_code", "payload", "session__session_id")
    )
    operations = list(
        OperationLog.objects.filter(booking=booking)
        .order_by("created_at")
        .values("created_at", "category", "action", "status", "entity_type", "entity_id", "details", "error")
    )
    api_logs = list(
        ApiRequestLog.objects.filter(booking_public_id=public_id)
        .order_by("created_at")
        .values("created_at", "method", "path", "action", "status_code", "duration_ms", "error")
    )
    payments = list(
        Payment.objects.filter(booking=booking)
        .order_by("created_at")
        .values("created_at", "status", "amount", "stripe_payment_intent_id", "paid_at")
    )
    pi_ids = set(
        Payment.objects.filter(booking=booking)
        .exclude(stripe_payment_intent_id=None)
        .values_list("stripe_payment_intent_id", flat=True)
    )
    webhooks = []
    for wh in WebhookLog.objects.filter(provider="stripe").order_by("-received_at")[:100]:
        obj = (wh.payload or {}).get("data", {}).get("object", {})
        meta = obj.get("metadata") or {}
        if obj.get("id") in pi_ids or meta.get("booking_public_id") == public_id:
            webhooks.append(
                {
                    "received_at": wh.received_at,
                    "event_type": wh.event_type,
                    "event_id": wh.event_id,
                    "processed": wh.processed,
                    "processing_error": wh.processing_error,
                }
            )
    webhooks.reverse()
    emails = list(
        EmailLog.objects.filter(booking=booking)
        .order_by("created_at")
        .values("created_at", "template_code", "recipient", "status", "provider_message_id", "error")
    )
    sms = list(
        SmsLog.objects.filter(booking=booking)
        .order_by("created_at")
        .values("created_at", "recipient", "status", "provider_message_id", "error")
    )
    telegram = list(
        TelegramLog.objects.filter(booking=booking)
        .order_by("created_at")
        .values("created_at", "recipient", "status", "provider_message_id", "error")
    )

    timeline = []
    for item in operations:
        timeline.append({"at": item["created_at"], "type": "operation", **item})
    for item in page_views:
        timeline.append({"at": item["entered_at"], "type": "page_view", **item})
    for item in journey:
        timeline.append({"at": item["created_at"], "type": "journey", **item})
    for item in api_logs:
        timeline.append({"at": item["created_at"], "type": "api", **item})
    for item in emails:
        timeline.append({"at": item["created_at"], "type": "email", **item})
    for item in sms:
        timeline.append({"at": item["created_at"], "type": "sms", **item})
    for item in telegram:
        timeline.append({"at": item["created_at"], "type": "telegram", **item})
    for item in payments:
        timeline.append({"at": item["created_at"], "type": "payment", **item})
    for item in webhooks:
        timeline.append({"at": item["received_at"], "type": "webhook", **item})
    timeline.sort(key=lambda row: str(row["at"]))

    return {
        "found": True,
        "booking": {
            "public_id": booking.public_id,
            "status": booking.status,
            "cruise": booking.cruise.code,
            "cruise_date": str(booking.cruise_date),
            "start_time": booking.start_time.isoformat(),
            "end_time": booking.end_time.isoformat(),
            "cruise_time": format_time_range(booking.start_time, booking.end_time),
            "total_amount": str(booking.total_amount),
            "customer_email": booking.customer.email,
        },
        "sessions": sessions,
        "page_views": page_views,
        "timeline": timeline,
        "summary": {
            "operations": len(operations),
            "journey_events": len(journey),
            "page_views": len(page_views),
            "api_calls": len(api_logs),
            "emails": len(emails),
            "sms": len(sms),
            "telegram": len(telegram),
            "payments": len(payments),
            "webhooks": len(webhooks),
        },
    }
