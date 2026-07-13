from __future__ import annotations

from django.db import models


class VisitorSession(models.Model):
    session_id = models.CharField("ID сессии", max_length=64, unique=True, db_index=True)
    booking = models.ForeignKey(
        "bookings.Booking",
        verbose_name="Связанная бронь",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visitor_sessions",
    )
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.TextField("User-Agent", blank=True)
    referrer = models.URLField("Referrer", blank=True, max_length=500)
    last_step = models.CharField("Последний шаг", max_length=64, blank=True)
    last_event = models.CharField("Последнее событие", max_length=64, blank=True)
    is_completed = models.BooleanField("Дошёл до подтверждения", default=False)
    is_abandoned = models.BooleanField("Брошена", default=False)
    first_seen_at = models.DateTimeField("Первый визит", auto_now_add=True)
    last_seen_at = models.DateTimeField("Последняя активность", auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = "Сессия посетителя"
        verbose_name_plural = "Сессии посетителей"

    def __str__(self) -> str:
        return f"{self.session_id} step={self.last_step or '-'}"


class JourneyEvent(models.Model):
    session = models.ForeignKey(VisitorSession, verbose_name="Сессия", on_delete=models.CASCADE, related_name="events")
    booking = models.ForeignKey(
        "bookings.Booking",
        verbose_name="Бронь",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journey_events",
    )
    event_type = models.CharField("Тип события", max_length=64, db_index=True)
    step = models.CharField("Шаг воронки", max_length=32, blank=True, db_index=True)
    cruise_code = models.CharField("Код круиза", max_length=32, blank=True)
    payload = models.JSONField("Данные события", default=dict)
    created_at = models.DateTimeField("Время", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "created_at"]), models.Index(fields=["step", "created_at"])]
        verbose_name = "Событие воронки"
        verbose_name_plural = "События воронки"


class PageView(models.Model):
    session = models.ForeignKey(VisitorSession, verbose_name="Сессия", on_delete=models.CASCADE, related_name="page_views")
    view_id = models.CharField("ID просмотра", max_length=64, db_index=True)
    path = models.CharField("Путь", max_length=500, db_index=True)
    page_title = models.CharField("Заголовок", max_length=255, blank=True)
    locale = models.CharField("Язык", max_length=8, blank=True)
    referrer = models.URLField("Referrer", blank=True, max_length=500)
    duration_ms = models.PositiveIntegerField("Время на странице, мс", default=0)
    scroll_depth_pct = models.PositiveSmallIntegerField("Глубина скролла, %", default=0)
    is_active = models.BooleanField("Активный просмотр", default=True)
    entered_at = models.DateTimeField("Вход", auto_now_add=True, db_index=True)
    left_at = models.DateTimeField("Выход", null=True, blank=True)

    class Meta:
        ordering = ["-entered_at"]
        indexes = [
            models.Index(fields=["path", "entered_at"]),
            models.Index(fields=["session", "entered_at"]),
        ]
        verbose_name = "Просмотр страницы"
        verbose_name_plural = "Просмотры страниц"


class ApiRequestLog(models.Model):
    method = models.CharField("HTTP метод", max_length=8)
    path = models.CharField("Путь", max_length=255, db_index=True)
    action = models.CharField("Action / endpoint", max_length=80, blank=True, db_index=True)
    query_string = models.CharField("Query", max_length=500, blank=True)
    status_code = models.PositiveSmallIntegerField("HTTP статус")
    duration_ms = models.PositiveIntegerField("Длительность, мс", default=0)
    session_id = models.CharField("Session ID", max_length=64, blank=True, db_index=True)
    booking_public_id = models.CharField("Booking public ID", max_length=32, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    request_summary = models.JSONField("Запрос (без секретов)", default=dict)
    response_summary = models.JSONField("Ответ (без секретов)", default=dict)
    error = models.TextField("Ошибка", blank=True)
    created_at = models.DateTimeField("Время", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["path", "status_code", "created_at"])]
        verbose_name = "API лог"
        verbose_name_plural = "API логи"


class OperationLog(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Начато"
        SUCCESS = "success", "Успех"
        FAILED = "failed", "Ошибка"
        SKIPPED = "skipped", "Пропущено"

    category = models.CharField("Категория", max_length=32, db_index=True)
    action = models.CharField("Действие", max_length=64, db_index=True)
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.STARTED)
    entity_type = models.CharField("Тип сущности", max_length=32, blank=True)
    entity_id = models.CharField("ID сущности", max_length=128, blank=True, db_index=True)
    booking = models.ForeignKey(
        "bookings.Booking",
        verbose_name="Бронь",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operation_logs",
    )
    session_id = models.CharField("Session ID", max_length=64, blank=True, db_index=True)
    details = models.JSONField("Детали (без секретов)", default=dict)
    error = models.TextField("Ошибка", blank=True)
    created_at = models.DateTimeField("Время", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category", "action", "created_at"])]
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
