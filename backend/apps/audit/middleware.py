from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .services import ApiTimer, extract_action_from_path, log_api_request, sanitize_payload


class ApiLoggingMiddleware(MiddlewareMixin):
    LOGGED_PREFIXES = ("/api/v1/", "/wp-admin/admin-ajax.php")

    def process_request(self, request: HttpRequest):
        if not request.path.startswith(self.LOGGED_PREFIXES):
            return None
        request._audit_timer = ApiTimer()
        if request.method == "POST" and request.content_type and "json" in request.content_type:
            request._audit_body = request.body
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse):
        if not request.path.startswith(self.LOGGED_PREFIXES):
            return response

        timer = getattr(request, "_audit_timer", None)
        duration_ms = timer.duration_ms if timer else 0
        request_summary = {}
        session_id = ""
        booking_public_id = ""

        if request.method == "POST":
            if request.content_type and "json" in request.content_type:
                try:
                    raw = getattr(request, "_audit_body", b"") or b""
                    body = json.loads(raw.decode("utf-8") or "{}")
                    request_summary = sanitize_payload(body)
                    session_id = str(body.get("session_id") or body.get("tc_session_id") or "")
                    booking_public_id = str(body.get("booking_id") or "")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_summary = {"parse_error": True}
            elif hasattr(request, "POST"):
                request_summary = sanitize_payload(dict(request.POST))
                session_id = str(request.POST.get("session_id") or request.POST.get("tc_session_id") or "")
                booking_public_id = str(request.POST.get("booking_id") or "")

        response_summary = {}
        if response.get("Content-Type", "").startswith("application/json"):
            try:
                response_summary = sanitize_payload(json.loads(response.content.decode("utf-8") or "{}"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                response_summary = {"parse_error": True}

        action = extract_action_from_path(request.path, request_summary if request.method == "POST" else None)
        if not action and request.method == "POST" and hasattr(request, "POST"):
            action = str(request.POST.get("action") or "")

        log_api_request(
            method=request.method,
            path=request.path,
            action=action,
            query_string=request.META.get("QUERY_STRING", ""),
            status_code=response.status_code,
            duration_ms=duration_ms,
            session_id=session_id,
            booking_public_id=booking_public_id,
            ip_address=request.META.get("REMOTE_ADDR"),
            request_summary=request_summary,
            response_summary=response_summary,
            error="" if response.status_code < 400 else response_summary.get("detail", ""),
        )
        return response
