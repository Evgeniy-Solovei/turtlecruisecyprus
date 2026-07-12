from __future__ import annotations

from django.utils import timezone

from apps.audit.models import OperationLog
from apps.audit.services import log_operation

from .models import WebhookLog
from .services import (
    confirm_booking_from_checkout_session,
    confirm_booking_from_payment_intent,
    expire_booking_from_checkout_session,
    mark_payment_failed,
)
from .stripe_client import construct_webhook_event


def handle_stripe_webhook(payload: bytes, signature: str) -> WebhookLog:
    event = construct_webhook_event(payload, signature)
    log, created = WebhookLog.objects.get_or_create(
        provider="stripe",
        event_id=event["id"],
        defaults={
            "event_type": event["type"],
            "signature_valid": True,
            "payload": event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else dict(event),
        },
    )
    if not created and log.processed:
        log_operation(
            category="payment",
            action="webhook_duplicate_skipped",
            status=OperationLog.Status.SKIPPED,
            entity_type="webhook",
            entity_id=event["id"],
            details={"event_type": event["type"]},
        )
        return log

    try:
        event_type = event["type"]
        obj = event["data"]["object"]
        booking_public_id = (obj.get("metadata") or {}).get("booking_public_id", "")
        log_operation(
            category="payment",
            action="webhook_received",
            entity_type="webhook",
            entity_id=event["id"],
            details={"event_type": event_type, "booking_public_id": booking_public_id},
        )
        if event_type == "checkout.session.completed":
            confirm_booking_from_checkout_session(obj)
        elif event_type == "checkout.session.expired":
            expire_booking_from_checkout_session(obj["id"], obj.get("status", "expired"))
        elif event_type == "payment_intent.succeeded":
            confirm_booking_from_payment_intent(obj["id"], obj.get("status", "succeeded"))
        elif event_type in {"payment_intent.payment_failed", "payment_intent.canceled"}:
            mark_payment_failed(obj["id"], obj.get("status", event_type))
        elif event_type == "charge.refunded":
            log_operation(
                category="payment",
                action="charge_refunded",
                entity_type="webhook",
                entity_id=event["id"],
                details={"charge_id": obj.get("id")},
            )
        log.processed = True
        log.processed_at = timezone.now()
        log.save(update_fields=["processed", "processed_at"])
        log_operation(
            category="payment",
            action="webhook_processed",
            entity_type="webhook",
            entity_id=event["id"],
            details={"event_type": event_type},
        )
    except Exception as exc:
        log.processing_error = str(exc)
        log.save(update_fields=["processing_error"])
        log_operation(
            category="payment",
            action="webhook_failed",
            status=OperationLog.Status.FAILED,
            entity_type="webhook",
            entity_id=event["id"],
            error=str(exc),
        )
        raise
    return log
