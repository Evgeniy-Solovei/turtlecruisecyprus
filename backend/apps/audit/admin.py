from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from unfold.admin import ModelAdmin

from .models import ApiRequestLog, JourneyEvent, OperationLog, PageView, VisitorSession
from .tasks import build_funnel_summary


def funnel_dashboard_view(request):
    days = 7
    try:
        days = max(1, min(int(request.GET.get("days", 7)), 90))
    except (TypeError, ValueError):
        days = 7
    data = build_funnel_summary(days=days)
    context = {
        **admin.site.each_context(request),
        "title": "Статистика сайта",
        "data": data,
        "days": days,
        "day_options": [1, 7, 14, 30],
    }
    return TemplateResponse(request, "admin/audit/funnel_dashboard.html", context)


_original_get_urls = admin.site.get_urls


def _custom_admin_urls():
    return [
        path(
            "audit/funnel-dashboard/",
            admin.site.admin_view(funnel_dashboard_view),
            name="audit_funnel_dashboard",
        ),
    ] + _original_get_urls()


admin.site.get_urls = _custom_admin_urls


class DevOnlyAdmin(ModelAdmin):
    """Технические разделы — не показываем владельцу."""

    def has_module_permission(self, request):
        return False


@admin.register(VisitorSession)
class VisitorSessionAdmin(DevOnlyAdmin):
    list_display = ["session_id", "last_step", "last_event", "is_completed", "is_abandoned", "booking", "last_seen_at"]
    list_filter = ["is_completed", "is_abandoned", "last_step"]
    search_fields = ["session_id", "booking__public_id", "ip_address"]
    readonly_fields = ["first_seen_at", "last_seen_at"]
    date_hierarchy = "last_seen_at"


@admin.register(PageView)
class PageViewAdmin(DevOnlyAdmin):
    list_display = ["entered_at", "path", "duration_ms", "scroll_depth_pct", "locale", "session", "is_active"]
    list_filter = ["is_active", "locale"]
    search_fields = ["path", "page_title", "session__session_id"]
    readonly_fields = ["entered_at", "left_at"]
    date_hierarchy = "entered_at"


@admin.register(JourneyEvent)
class JourneyEventAdmin(DevOnlyAdmin):
    list_display = ["created_at", "event_type", "step", "cruise_code", "session", "booking"]
    list_filter = ["event_type", "step", "cruise_code"]
    search_fields = ["session__session_id", "booking__public_id", "event_type"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(DevOnlyAdmin):
    list_display = ["created_at", "method", "path", "action", "status_code", "duration_ms", "session_id", "booking_public_id"]
    list_filter = ["method", "status_code", "action", "path"]
    search_fields = ["path", "action", "session_id", "booking_public_id", "ip_address"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"


@admin.register(OperationLog)
class OperationLogAdmin(DevOnlyAdmin):
    list_display = ["created_at", "category", "action", "status", "entity_type", "entity_id", "booking", "session_id"]
    list_filter = ["category", "action", "status"]
    search_fields = ["entity_id", "session_id", "booking__public_id", "action"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"
