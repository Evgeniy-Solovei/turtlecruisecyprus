from __future__ import annotations

import secrets

from django.db import models
from django.utils import timezone


class Customer(models.Model):
    first_name = models.CharField("Имя", max_length=120)
    last_name = models.CharField("Фамилия", max_length=120, blank=True)
    email = models.EmailField("Email клиента")
    phone = models.CharField("Телефон клиента", max_length=64)
    country_code = models.CharField("Код страны телефона", max_length=8, blank=True)
    marketing_opt_in = models.BooleanField("Согласие на маркетинг", default=False)
    legacy_wp_customer_id = models.PositiveIntegerField("Legacy MotoPress customer ID", null=True, blank=True, unique=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["email"]), models.Index(fields=["phone"])]
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.full_name or self.email


class Booking(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PENDING_PAYMENT = "pending_payment", "Ожидает оплату"
        CONFIRMED = "confirmed", "Подтверждена"
        CANCELLED = "cancelled", "Отменена"
        EXPIRED = "expired", "Истекло удержание"
        PAYMENT_FAILED = "payment_failed", "Ошибка оплаты"
        REFUNDED = "refunded", "Возврат"

    class CancelReason(models.TextChoices):
        SOLD_OUT = "sold_out", "Места закончились"
        HOLD_EXPIRED = "hold_expired", "Истекло удержание"
        USER_CANCELLED = "user_cancelled", "Отменено пользователем"

    OCCUPIES_SEATS = {Status.PENDING_PAYMENT, Status.CONFIRMED}

    public_id = models.CharField("Публичный номер брони", max_length=32, unique=True, editable=False)
    customer = models.ForeignKey(Customer, verbose_name="Клиент", related_name="bookings", on_delete=models.PROTECT)
    cruise = models.ForeignKey("cruises.Cruise", verbose_name="Круиз", related_name="bookings", on_delete=models.PROTECT)
    cruise_date = models.DateField("Дата круиза")
    start_time = models.TimeField("Время начала")
    end_time = models.TimeField("Время окончания")
    adults_count = models.PositiveIntegerField("Количество взрослых", default=1)
    children_count = models.PositiveIntegerField("Количество детей", default=0)
    total_seats = models.PositiveIntegerField("Всего занятых мест", default=1)
    adult_unit_price = models.DecimalField("Цена за взрослого", max_digits=10, decimal_places=2)
    child_unit_price = models.DecimalField("Цена за ребенка", max_digits=10, decimal_places=2)
    total_amount = models.DecimalField("Итоговая сумма", max_digits=10, decimal_places=2)
    currency = models.CharField("Валюта", max_length=3, default="EUR")
    status = models.CharField("Статус брони", max_length=32, choices=Status.choices, default=Status.PENDING_PAYMENT)
    cancel_reason = models.CharField(
        "Причина отмены/истечения",
        max_length=32,
        choices=CancelReason.choices,
        blank=True,
    )
    customer_notes = models.TextField("Комментарий клиента", blank=True)
    admin_notes = models.TextField("Заметки администратора", blank=True)
    source = models.CharField("Источник брони", max_length=32, default="web", help_text="web, admin, migration, wp-compat")
    legacy_wp_booking_id = models.PositiveIntegerField("Legacy MotoPress booking ID", null=True, blank=True, unique=True)
    legacy_wp_reservation_id = models.PositiveIntegerField("Legacy MotoPress reservation ID", null=True, blank=True, unique=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    confirmed_at = models.DateTimeField("Подтверждено", null=True, blank=True)
    cancelled_at = models.DateTimeField("Отменено/истекло", null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cruise", "cruise_date", "status"]),
            models.Index(fields=["legacy_wp_booking_id"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Бронь"
        verbose_name_plural = "Брони"

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12].upper()
        super().save(*args, **kwargs)

    def confirm(self) -> None:
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()

    def cancel(self, status: str = Status.CANCELLED, *, reason: str = "") -> None:
        self.status = status
        self.cancelled_at = timezone.now()
        if reason:
            self.cancel_reason = reason

    def __str__(self) -> str:
        return f"{self.public_id} {self.cruise.code} {self.cruise_date}"
