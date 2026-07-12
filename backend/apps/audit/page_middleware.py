from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .services import ApiTimer, log_operation


class PageLoggingMiddleware(MiddlewareMixin):
    """Серверный лог HTML-страниц (рендер + путь). Время на странице — из JS-трекера."""

    SKIP_PREFIXES = ("/static/", "/media/", "/admin/", "/api/", "/wp-admin/")

    def _skip(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES)

    def process_request(self, request: HttpRequest):
        if self._skip(request.path):
            return None
        request._page_timer = ApiTimer()
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse):
        if self._skip(request.path) or response.status_code >= 500:
            return response

        timer = getattr(request, "_page_timer", None)
        duration_ms = timer.duration_ms if timer else 0
        session_id = request.COOKIES.get("tc_session_id", "") or request.headers.get("X-TC-Session-Id", "")

        log_operation(
            category="page",
            action="html_request",
            entity_type="page",
            entity_id=request.path[:64],
            session_id=session_id[:64],
            details={
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "locale": getattr(request, "locale", ""),
                "referrer": request.META.get("HTTP_REFERER", "")[:500],
            },
        )
        return response
