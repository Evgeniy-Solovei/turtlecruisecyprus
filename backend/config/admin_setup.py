"""Скрываем лишнее в админке и ведём на «Брони» при входе."""

from __future__ import annotations

import types

from django.contrib import admin
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.urls import reverse


def hide_from_admin_index(model_admin_class: type) -> type:
    """Модель остаётся в системе, но не показывается в списке приложений."""

    original = model_admin_class.has_module_permission

    def has_module_permission(self, request):
        return False

    model_admin_class.has_module_permission = has_module_permission
    return model_admin_class


def configure_admin_site() -> None:
    try:
        admin.site.unregister(Group)
    except admin.sites.NotRegistered:
        pass

    def index_redirect(self, request, extra_context=None):
        return redirect(reverse("admin:bookings_booking_changelist"))

    admin.site.index = types.MethodType(index_redirect, admin.site)


def dashboard_callback(request, context):
    """Unfold: убираем лишние приложения, если index всё же откроется."""
    allowed = {"bookings", "cruises", "payments", "notifications", "auth", "cms"}
    filtered = []
    for app in context.get("app_list", []):
        if app.get("app_label") not in allowed:
            continue
        if app.get("app_label") == "auth":
            app = {**app, "models": [m for m in app["models"] if m.get("object_name") == "User"]}
        if app.get("app_label") == "cms":
            app = {**app, "models": [m for m in app["models"] if m.get("object_name") in {"BlogPost", "SitePage"}]}
        filtered.append(app)
    context["app_list"] = filtered
    return context
