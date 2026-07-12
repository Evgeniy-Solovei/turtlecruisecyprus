from __future__ import annotations

import re
import time
import uuid
from typing import Any

from django.utils import timezone

from .models import ApiRequestLog, JourneyEvent, OperationLog, PageView, VisitorSession

SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "stripe",
    "client_secret",
    "payment_intent",
    "card",
    "cvv",
}


def _redact_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if any(part in key_lower for part in SENSITIVE_KEYS):
        return "REDACTED"
    if isinstance(value, dict):
        return sanitize_payload(value)
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value[:20]]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def sanitize_payload(data: dict | None) -> dict:
    if not data:
        return {}
    return {key: _redact_value(key, value) for key, value in data.items()}


def get_or_create_session(
    *,
    session_id: str | None,
    ip_address: str | None = None,
    user_agent: str = "",
    referrer: str = "",
) -> VisitorSession:
    sid = session_id or str(uuid.uuid4())
    session, created = VisitorSession.objects.get_or_create(
        session_id=sid,
        defaults={
            "ip_address": ip_address,
            "user_agent": user_agent[:1000],
            "referrer": referrer[:500],
        },
    )
    if not created:
        updates = {}
        if ip_address:
            updates["ip_address"] = ip_address
        if user_agent:
            updates["user_agent"] = user_agent[:1000]
        if referrer:
            updates["referrer"] = referrer[:500]
        if updates:
            for field, value in updates.items():
                setattr(session, field, value)
            session.save(update_fields=[*updates.keys(), "last_seen_at"])
    return session


def log_journey_event(
    *,
    session_id: str,
    event_type: str,
    step: str = "",
    cruise_code: str = "",
    booking_id: int | None = None,
    payload: dict | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    referrer: str = "",
    completed: bool = False,
    abandoned: bool = False,
) -> JourneyEvent:
    session = get_or_create_session(
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
    )
    if booking_id:
        session.booking_id = booking_id
    session.last_step = step or session.last_step
    session.last_event = event_type
    if completed:
        session.is_completed = True
    if abandoned:
        session.is_abandoned = True
    session.last_seen_at = timezone.now()
    session.save()

    return JourneyEvent.objects.create(
        session=session,
        booking_id=booking_id,
        event_type=event_type,
        step=step,
        cruise_code=cruise_code,
        payload=sanitize_payload(payload),
    )


def log_page_view(
    *,
    session_id: str,
    view_id: str,
    path: str,
    page_title: str = "",
    locale: str = "",
    referrer: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
) -> PageView:
    session = get_or_create_session(
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
    )
    session.last_event = "page_enter"
    session.last_seen_at = timezone.now()
    session.save(update_fields=["last_event", "last_seen_at"])

    page_view, _ = PageView.objects.get_or_create(
        session=session,
        view_id=view_id,
        defaults={
            "path": path[:500],
            "page_title": page_title[:255],
            "locale": locale[:8],
            "referrer": referrer[:500],
        },
    )
    JourneyEvent.objects.create(
        session=session,
        event_type="page_enter",
        payload=sanitize_payload({"path": path, "view_id": view_id, "page_title": page_title, "locale": locale}),
    )
    return page_view


def finalize_page_view(
    *,
    session_id: str,
    view_id: str,
    duration_ms: int = 0,
    scroll_depth_pct: int = 0,
    ip_address: str | None = None,
    user_agent: str = "",
) -> PageView | None:
    session = VisitorSession.objects.filter(session_id=session_id).first()
    if not session:
        return None

    page_view = PageView.objects.filter(session=session, view_id=view_id).first()
    if not page_view:
        return None

    if not page_view.is_active:
        return page_view

    page_view.duration_ms = max(duration_ms, page_view.duration_ms, 0)
    page_view.scroll_depth_pct = min(max(scroll_depth_pct, 0), 100)
    page_view.is_active = False
    page_view.left_at = timezone.now()
    page_view.save(update_fields=["duration_ms", "scroll_depth_pct", "is_active", "left_at"])

    session.last_event = "page_exit"
    session.last_seen_at = timezone.now()
    session.save(update_fields=["last_event", "last_seen_at"])

    JourneyEvent.objects.create(
        session=session,
        event_type="page_exit",
        payload=sanitize_payload(
            {
                "path": page_view.path,
                "view_id": view_id,
                "duration_ms": page_view.duration_ms,
                "scroll_depth_pct": page_view.scroll_depth_pct,
            }
        ),
    )
    return page_view


def heartbeat_page_view(
    *,
    session_id: str,
    view_id: str,
    duration_ms: int = 0,
    scroll_depth_pct: int = 0,
) -> PageView | None:
    page_view = PageView.objects.filter(session__session_id=session_id, view_id=view_id, is_active=True).first()
    if not page_view:
        return None
    page_view.duration_ms = max(duration_ms, page_view.duration_ms)
    page_view.scroll_depth_pct = max(scroll_depth_pct, page_view.scroll_depth_pct)
    page_view.save(update_fields=["duration_ms", "scroll_depth_pct"])
    VisitorSession.objects.filter(session_id=session_id).update(last_seen_at=timezone.now())
    return page_view


def log_operation(
    *,
    category: str,
    action: str,
    status: str = OperationLog.Status.SUCCESS,
    entity_type: str = "",
    entity_id: str = "",
    booking_id: int | None = None,
    session_id: str = "",
    details: dict | None = None,
    error: str = "",
) -> OperationLog:
    return OperationLog.objects.create(
        category=category,
        action=action,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        booking_id=booking_id,
        session_id=session_id,
        details=sanitize_payload(details),
        error=error[:2000],
    )


def log_api_request(
    *,
    method: str,
    path: str,
    action: str = "",
    query_string: str = "",
    status_code: int,
    duration_ms: int,
    session_id: str = "",
    booking_public_id: str = "",
    ip_address: str | None = None,
    request_summary: dict | None = None,
    response_summary: dict | None = None,
    error: str = "",
) -> ApiRequestLog:
    return ApiRequestLog.objects.create(
        method=method,
        path=path,
        action=action,
        query_string=query_string[:500],
        status_code=status_code,
        duration_ms=duration_ms,
        session_id=session_id,
        booking_public_id=booking_public_id,
        ip_address=ip_address,
        request_summary=sanitize_payload(request_summary),
        response_summary=sanitize_payload(response_summary),
        error=error[:2000],
    )


def extract_action_from_path(path: str, body: dict | None = None) -> str:
    if body and body.get("action"):
        return str(body["action"])
    match = re.search(r"/api/v1/([^/]+)", path)
    if match:
        return match.group(1)
    return ""


class ApiTimer:
    def __init__(self):
        self.started = time.perf_counter()

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)
