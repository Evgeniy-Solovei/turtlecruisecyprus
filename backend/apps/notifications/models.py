from __future__ import annotations

from django.db import models


class EmailLog(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "В очереди"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"
        DELIVERED = "delivered", "Доставлено"
        BOUNCED = "bounced", "Возврат/отказ"

    booking = models.ForeignKey("bookings.Booking", verbose_name="Бронь", related_name="email_logs", on_delete=models.CASCADE)
    provider = models.CharField("Email провайдер", max_length=32, default="brevo")
    template_code = models.CharField("Код шаблона", max_length=80)
    recipient = models.EmailField("Получатель")
    subject = models.CharField("Тема письма", max_length=255)
    status = models.CharField("Статус отправки", max_length=32, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField("ID сообщения у провайдера", max_length=160, blank=True)
    error = models.TextField("Ошибка отправки", blank=True)
    payload_snapshot = models.JSONField("Снимок payload без секретов", default=dict)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    sent_at = models.DateTimeField("Отправлено", null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["booking", "template_code", "recipient"]), models.Index(fields=["status"])]
        verbose_name = "Email лог"
        verbose_name_plural = "Email логи"


class SmsLog(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "В очереди"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"
        DELIVERED = "delivered", "Доставлено"

    booking = models.ForeignKey("bookings.Booking", verbose_name="Бронь", related_name="sms_logs", on_delete=models.CASCADE)
    provider = models.CharField("SMS провайдер", max_length=32, default="clicksend")
    recipient = models.CharField("Получатель", max_length=64)
    message = models.TextField("Текст SMS")
    status = models.CharField("Статус отправки", max_length=32, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField("ID сообщения у провайдера", max_length=160, blank=True)
    error = models.TextField("Ошибка отправки", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    sent_at = models.DateTimeField("Отправлено", null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["booking", "recipient"]), models.Index(fields=["status"])]
        verbose_name = "SMS лог"
        verbose_name_plural = "SMS логи"


class TelegramLog(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "В очереди"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"

    booking = models.ForeignKey("bookings.Booking", verbose_name="Бронь", related_name="telegram_logs", on_delete=models.CASCADE)
    provider = models.CharField("Провайдер", max_length=32, default="telegram")
    recipient = models.CharField("Chat ID", max_length=64)
    message = models.TextField("Текст")
    status = models.CharField("Статус отправки", max_length=32, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField("ID сообщения", max_length=160, blank=True)
    error = models.TextField("Ошибка отправки", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    sent_at = models.DateTimeField("Отправлено", null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["booking", "recipient"]), models.Index(fields=["status"])]
        verbose_name = "Telegram лог"
        verbose_name_plural = "Telegram логи"
