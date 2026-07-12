from django.contrib import admin
from django.db.models import Count, Sum
from django.http import QueryDict
from unfold.admin import ModelAdmin

from .filters import earnings_period_label, earnings_queryset_for_period
from .models import Booking, Customer

_EARNINGS_QUERY_KEYS = frozenset({"earnings_period", "earnings_from", "earnings_to"})


def _strip_earnings_params(query: QueryDict) -> QueryDict:
    clean = query.copy()
    for key in list(clean.keys()):
        if key in _EARNINGS_QUERY_KEYS or key == "e":
            clean.pop(key, None)
    return clean


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ["full_name", "email", "phone", "created_at"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    fieldsets = (
        ("Контакты", {"fields": ("first_name", "last_name", "email", "phone", "country_code")}),
        ("Согласия", {"fields": ("marketing_opt_in",)}),
    )

    def has_module_permission(self, request):
        return False


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    change_list_template = "admin/bookings/booking/change_list.html"
    list_display = [
        "public_id",
        "customer_name",
        "customer_email",
        "cruise",
        "cruise_date",
        "status",
        "total_seats",
        "total_amount",
    ]
    list_filter = ["status", "cruise", "source"]
    search_fields = ["public_id", "customer__email", "customer__phone", "customer__first_name", "customer__last_name"]
    date_hierarchy = "cruise_date"
    readonly_fields = ["public_id", "created_at", "updated_at", "confirmed_at", "cancelled_at"]
    fieldsets = (
        ("Статус", {"fields": ("public_id", "status", "source", "cancel_reason")}),
        ("Клиент", {"fields": ("customer",)}),
        ("Круиз", {"fields": ("cruise", "cruise_date", "start_time", "end_time")}),
        ("Пассажиры и сумма", {"fields": ("adults_count", "children_count", "total_seats", "adult_unit_price", "child_unit_price", "total_amount", "currency")}),
        ("Заметки", {"fields": ("customer_notes", "admin_notes")}),
        ("Даты", {"fields": ("created_at", "updated_at", "confirmed_at", "cancelled_at"), "classes": ("collapse",)}),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        earnings_qs = earnings_queryset_for_period(request)
        agg = earnings_qs.aggregate(total=Sum("total_amount"), count=Count("id"))
        current = request.GET.get("earnings_period", "this_month")
        admin_query = _strip_earnings_params(request.GET)
        period_links = []
        for key, label in [
            ("this_month", "Этот месяц"),
            ("last_month", "Прошлый месяц"),
            ("this_year", "Этот год"),
            ("all", "Всё время"),
        ]:
            q = admin_query.copy()
            q["earnings_period"] = key
            period_links.append({"key": key, "label": label, "url": "?" + q.urlencode()})
        extra_context["earnings_summary"] = {
            "total": agg["total"] or 0,
            "count": agg["count"] or 0,
            "currency": "EUR",
            "period_label": earnings_period_label(request),
            "current_period": current,
            "period_links": period_links,
        }
        request.GET = admin_query
        request.META["QUERY_STRING"] = admin_query.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Клиент")
    def customer_name(self, obj: Booking) -> str:
        return obj.customer.full_name

    @admin.display(description="Email")
    def customer_email(self, obj: Booking) -> str:
        return obj.customer.email
