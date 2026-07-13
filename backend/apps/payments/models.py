from __future__ import annotations

from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        REQUIRES_PAYMENT_METHOD = "requires_payment_method", "Нужен способ оплаты"
        REQUIRES_ACTION = "requires_action", "Нужно действие клиента"
        PROCESSING = "processing", "В обработке"
        SUCCEEDED = "succeeded", "Успешно оплачен"
        FAILED = "failed", "Ошибка оплаты"
        CANCELLED = "cancelled", "Отменен"
        REFUNDED = "refunded", "Возврат"

    booking = models.ForeignKey("bookings.Booking", verbose_name="Бронь", related_name="payments", on_delete=models.PROTECT)
    provider = models.CharField("Платежный провайдер", max_length=32, default="stripe")
    status = models.CharField("Статус платежа", max_length=64, choices=Status.choices, default=Status.REQUIRES_PAYMENT_METHOD)
    amount = models.DecimalField("Сумма платежа", max_digits=10, decimal_places=2)
    currency = models.CharField("Валюта", max_length=3, default="EUR")
    stripe_payment_intent_id = models.CharField("Stripe PaymentIntent ID", max_length=128, unique=True, null=True, blank=True)
    stripe_checkout_session_id = models.CharField("Stripe Checkout Session ID", max_length=128, unique=True, null=True, blank=True)
    stripe_charge_id = models.CharField("Stripe Charge ID", max_length=128, blank=True)
    stripe_customer_id = models.CharField("Stripe Customer ID", max_length=128, blank=True)
    transaction_id = models.CharField("Внешний transaction ID", max_length=128, blank=True)
    provider_client_secret = models.CharField("Stripe client secret", max_length=1024, blank=True, help_text="Не показывать клиенту вне платежного flow.")
    idempotency_key = models.CharField("Ключ идемпотентности", max_length=160, unique=True)
    raw_provider_status = models.CharField("Исходный статус провайдера", max_length=128, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    paid_at = models.DateTimeField("Оплачено", null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["booking", "status"]), models.Index(fields=["provider"])]
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"

    def __str__(self) -> str:
        return f"{self.booking.public_id} {self.provider} {self.status}"


class WebhookLog(models.Model):
    provider = models.CharField("Провайдер webhook", max_length=32)
    event_id = models.CharField("ID события", max_length=160)
    event_type = models.CharField("Тип события", max_length=160)
    signature_valid = models.BooleanField("Подпись проверена", default=False)
    processed = models.BooleanField("Обработан", default=False)
    processing_error = models.TextField("Ошибка обработки", blank=True)
    payload = models.JSONField("Payload события", default=dict)
    received_at = models.DateTimeField("Получен", auto_now_add=True)
    processed_at = models.DateTimeField("Обработан в", null=True, blank=True)

    class Meta:
        unique_together = [("provider", "event_id")]
        indexes = [models.Index(fields=["provider", "event_type", "processed"])]
        verbose_name = "Webhook лог"
        verbose_name_plural = "Webhook логи"

    def __str__(self) -> str:
        return f"{self.provider} {self.event_type} {self.event_id}"
