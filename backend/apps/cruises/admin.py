from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Cruise, CruiseDateOverride, CruiseSchedule

LEGACY_FIELDS = (
    "legacy_wp_service_id",
    "legacy_wp_schedule_id",
    "legacy_wp_id",
)


@admin.register(Cruise)
class CruiseAdmin(ModelAdmin):
    list_display = ["name", "code", "default_adult_price", "default_child_price", "default_capacity", "is_active"]
    list_filter = ["is_active", "child_allowed"]
    search_fields = ["code", "name"]
    readonly_fields = ["code"]
    fieldsets = (
        (
            "Основное",
            {
                "description": "Код (morning/sunset) менять нельзя — от него завязан сайт.",
                "fields": ("code", "name", "description", "is_active"),
            },
        ),
        (
            "Цены и места",
            {
                "description": "Сколько мест на лодке и цены по умолчанию. Для одной конкретной даты — раздел «Исключения дат».",
                "fields": ("default_adult_price", "default_child_price", "child_allowed", "default_capacity"),
            },
        ),
    )

    def get_exclude(self, request, obj=None):
        return ("sort_order", "default_duration_minutes", *LEGACY_FIELDS)


@admin.register(CruiseSchedule)
class CruiseScheduleAdmin(ModelAdmin):
    list_display = ["cruise", "weekday_display", "start_time", "end_time", "is_active"]
    list_filter = ["cruise", "weekday", "is_active"]
    fieldsets = (
        (
            "Расписание",
            {
                "description": "В какие дни недели и во сколько ходит круиз. 0 = понедельник, 6 = воскресенье.",
                "fields": ("cruise", "weekday", "start_time", "end_time", "is_active"),
            },
        ),
        (
            "Сезон (необязательно)",
            {
                "description": "Оставьте пустым, если расписание действует круглый год.",
                "fields": ("valid_from", "valid_to"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="День недели", ordering="weekday")
    def weekday_display(self, obj: CruiseSchedule) -> str:
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return names[obj.weekday] if 0 <= obj.weekday <= 6 else str(obj.weekday)

    def get_exclude(self, request, obj=None):
        return ("timezone", *LEGACY_FIELDS)


@admin.register(CruiseDateOverride)
class CruiseDateOverrideAdmin(ModelAdmin):
    list_display = ["cruise", "date", "is_closed", "capacity_override", "adult_price_override", "child_price_override"]
    list_filter = ["cruise", "is_closed"]
    date_hierarchy = "date"
    fieldsets = (
        (
            "Дата",
            {
                "description": "Закрыть день полностью или изменить цену/места только на эту дату.",
                "fields": ("cruise", "date", "is_closed", "note"),
            },
        ),
        ("Переопределения", {"fields": ("capacity_override", "adult_price_override", "child_price_override")}),
    )

    def get_exclude(self, request, obj=None):
        return LEGACY_FIELDS
