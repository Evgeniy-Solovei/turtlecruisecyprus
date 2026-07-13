from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone


class StripeNotConfigured(RuntimeError):
    pass


STRIPE_CHECKOUT_MIN_MINUTES = 30
# Stripe rejects expires_at at exactly +24h; keep a small safety margin.
STRIPE_CHECKOUT_MAX_HOURS = 23
STRIPE_CHECKOUT_MAX_MINUTES = 55


def _stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise StripeNotConfigured("STRIPE_SECRET_KEY is not configured.")
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def amount_to_cents(amount: Decimal) -> int:
    return int((amount * Decimal("100")).quantize(Decimal("1")))


def checkout_session_expires_at() -> int:
    """Stripe требует expires_at (мин. 30 мин, макс. 24 ч). Sold out закрываем отдельно через expire_checkout_session."""
    now = timezone.now()
    return int((now + timedelta(hours=STRIPE_CHECKOUT_MAX_HOURS, minutes=STRIPE_CHECKOUT_MAX_MINUTES)).timestamp())


def checkout_expires_at(checkout_deadline: datetime | None = None) -> int:
    """Нормализует произвольный дедлайн в допустимые границы Stripe."""
    now = timezone.now()
    if checkout_deadline is None:
        return checkout_session_expires_at()
    stripe_min = now + timedelta(minutes=STRIPE_CHECKOUT_MIN_MINUTES)
    stripe_max = now + timedelta(hours=STRIPE_CHECKOUT_MAX_HOURS, minutes=STRIPE_CHECKOUT_MAX_MINUTES)
    expires = checkout_deadline
    if expires < stripe_min:
        expires = stripe_min
    if expires > stripe_max:
        expires = stripe_max
    return int(expires.timestamp())


def create_checkout_session(
    *,
    amount: Decimal,
    currency: str,
    product_name: str,
    metadata: dict,
    idempotency_key: str,
    return_url: str,
    expires_at: int,
):
    stripe = _stripe()
    return stripe.checkout.Session.create(
        ui_mode="embedded",
        mode="payment",
        expires_at=expires_at,
        line_items=[
            {
                "price_data": {
                    "currency": currency.lower(),
                    "unit_amount": amount_to_cents(amount),
                    "product_data": {"name": product_name},
                },
                "quantity": 1,
            }
        ],
        metadata=metadata,
        return_url=return_url,
        idempotency_key=idempotency_key,
    )


def expire_checkout_session(session_id: str):
    stripe = _stripe()
    return stripe.checkout.Session.expire(session_id)


def create_payment_intent(*, amount: Decimal, currency: str, metadata: dict, idempotency_key: str):
    stripe = _stripe()
    return stripe.PaymentIntent.create(
        amount=amount_to_cents(amount),
        currency=currency.lower(),
        automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        metadata=metadata,
        idempotency_key=idempotency_key,
    )


def cancel_payment_intent(payment_intent_id: str):
    stripe = _stripe()
    return stripe.PaymentIntent.cancel(payment_intent_id)


def retrieve_payment_intent(payment_intent_id: str):
    stripe = _stripe()
    return stripe.PaymentIntent.retrieve(payment_intent_id)


def retrieve_checkout_session(session_id: str):
    stripe = _stripe()
    return stripe.Checkout.Session.retrieve(session_id)


def construct_webhook_event(payload: bytes, signature: str):
    stripe = _stripe()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise StripeNotConfigured("STRIPE_WEBHOOK_SECRET is not configured.")
    return stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
