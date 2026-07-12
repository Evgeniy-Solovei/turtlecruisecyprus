from __future__ import annotations

from django.utils import translation

from .i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES


class LocalePrefixMiddleware:
    """Sets locale from /de/ URL prefix (Polylang-style)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        locale = DEFAULT_LOCALE
        if path == "/de" or path.startswith("/de/"):
            locale = "de"
        elif path.startswith("/en/"):
            locale = "en"

        request.locale = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
        translation.activate(request.locale)
        response = self.get_response(request)
        translation.deactivate()
        return response
