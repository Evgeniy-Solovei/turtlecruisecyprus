from __future__ import annotations

from django.conf import settings
from django.db import models


class Cruise(models.Model):
    code = models.SlugField("Код круиза", unique=True, help_text="Системный код: morning, sunset. Используется в API и frontend.")
    name = models.CharField("Название круиза", max_length=160)
    description = models.TextField("Описание", blank=True)
    default_adult_price = models.DecimalField("Базовая цена взрослого", max_digits=10, decimal_places=2)
    default_child_price = models.DecimalField("Базовая цена ребенка", max_digits=10, decimal_places=2, default=0)
    child_allowed = models.BooleanField("Дети разрешены", default=True)
    default_capacity = models.PositiveIntegerField("Базовая вместимость", default=30)
    default_duration_minutes = models.PositiveIntegerField("Длительность по умолчанию, минут", default=240)
    is_active = models.BooleanField("Активен для бронирования", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    legacy_wp_service_id = models.PositiveIntegerField("Legacy MotoPress service ID", null=True, blank=True, unique=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Круиз"
        verbose_name_plural = "Круизы"

    def __str__(self) -> str:
        return self.name


class CruiseSchedule(models.Model):
    cruise = models.ForeignKey(Cruise, verbose_name="Круиз", related_name="schedules", on_delete=models.CASCADE)
    weekday = models.PositiveSmallIntegerField("День недели", help_text="0=понедельник, 6=воскресенье")
    start_time = models.TimeField("Время начала")
    end_time = models.TimeField("Время окончания")
    timezone = models.CharField("Часовой пояс", max_length=64, default=settings.TIME_ZONE)
    valid_from = models.DateField("Действует с даты", null=True, blank=True)
    valid_to = models.DateField("Действует до даты", null=True, blank=True)
    is_active = models.BooleanField("Активно", default=True)
    legacy_wp_schedule_id = models.PositiveIntegerField("Legacy MotoPress schedule ID", null=True, blank=True)

    class Meta:
        ordering = ["cruise", "weekday", "start_time"]
        indexes = [
            models.Index(fields=["cruise", "weekday", "is_active"]),
            models.Index(fields=["legacy_wp_schedule_id"]),
        ]
        verbose_name = "Расписание круиза"
        verbose_name_plural = "Расписания круизов"

    def __str__(self) -> str:
        return f"{self.cruise.code} {self.weekday} {self.start_time}-{self.end_time}"


class CruiseDateOverride(models.Model):
    cruise = models.ForeignKey(Cruise, verbose_name="Круиз", related_name="date_overrides", on_delete=models.CASCADE)
    date = models.DateField("Дата")
    capacity_override = models.PositiveIntegerField("Переопределение вместимости", null=True, blank=True)
    is_closed = models.BooleanField("Дата закрыта для бронирования", default=False)
    adult_price_override = models.DecimalField("Переопределение цены взрослого", max_digits=10, decimal_places=2, null=True, blank=True)
    child_price_override = models.DecimalField("Переопределение цены ребенка", max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.TextField("Заметка администратора", blank=True)
    legacy_wp_id = models.PositiveIntegerField("Legacy WP override ID", null=True, blank=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        unique_together = [("cruise", "date")]
        ordering = ["date", "cruise"]
        indexes = [models.Index(fields=["date", "is_closed"])]
        verbose_name = "Исключение/переопределение даты"
        verbose_name_plural = "Исключения/переопределения дат"

    def __str__(self) -> str:
        return f"{self.cruise.code} {self.date}"
