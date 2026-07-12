from __future__ import annotations

from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from apps.bookings.models import Booking

from .services import (
    finalize_page_view,
    heartbeat_page_view,
    log_journey_event,
    log_page_view,
)
from .tasks import build_funnel_summary, get_session_timeline


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def track_event(request):
    data = request.data
    session_id = data.get("session_id") or data.get("tc_session_id")
    if not session_id:
        return Response({"detail": "session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    event_type = str(data.get("event_type") or data.get("event") or "unknown")
    page_action = str(data.get("page_action") or "")

    if event_type in {"page_enter", "page_exit", "page_heartbeat"} or page_action:
        action = page_action or event_type
        view_id = str(data.get("view_id") or "")
        if not view_id:
            return Response({"detail": "view_id is required for page tracking."}, status=status.HTTP_400_BAD_REQUEST)

        if action in {"page_enter", "enter"}:
            page_view = log_page_view(
                session_id=str(session_id),
                view_id=view_id,
                path=str(data.get("path") or "/"),
                page_title=str(data.get("page_title") or ""),
                locale=str(data.get("locale") or ""),
                referrer=request.META.get("HTTP_REFERER", ""),
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            return Response({"id": page_view.id, "view_id": view_id}, status=status.HTTP_201_CREATED)

        if action in {"page_exit", "exit"}:
            page_view = finalize_page_view(
                session_id=str(session_id),
                view_id=view_id,
                duration_ms=int(data.get("duration_ms") or 0),
                scroll_depth_pct=int(data.get("scroll_depth_pct") or 0),
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            return Response({"id": page_view.id if page_view else None}, status=status.HTTP_200_OK)

        if action in {"page_heartbeat", "heartbeat"}:
            page_view = heartbeat_page_view(
                session_id=str(session_id),
                view_id=view_id,
                duration_ms=int(data.get("duration_ms") or 0),
                scroll_depth_pct=int(data.get("scroll_depth_pct") or 0),
            )
            return Response({"id": page_view.id if page_view else None}, status=status.HTTP_200_OK)

    booking_db_id = data.get("booking_db_id")
    booking_public_id = data.get("booking_id") or data.get("booking_public_id")
    if not booking_db_id and booking_public_id:
        booking_db_id = Booking.objects.filter(public_id=booking_public_id).values_list("id", flat=True).first()

    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {
        k: v for k, v in data.items() if k not in {"session_id", "tc_session_id", "event_type", "event", "step"}
    }

    event = log_journey_event(
        session_id=str(session_id),
        event_type=event_type,
        step=str(data.get("step") or ""),
        cruise_code=str(data.get("cruise_code") or data.get("cruise_type") or ""),
        booking_id=booking_db_id,
        payload=payload,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referrer=request.META.get("HTTP_REFERER", ""),
        completed=bool(data.get("completed")),
        abandoned=bool(data.get("abandoned")),
    )
    return Response({"id": event.id, "session_id": session_id}, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def track_events_batch(request):
    events = request.data.get("events")
    if not isinstance(events, list):
        return Response({"detail": "events must be a list."}, status=status.HTTP_400_BAD_REQUEST)

    created = 0
    for item in events[:50]:
        if not isinstance(item, dict):
            continue
        session_id = item.get("session_id") or item.get("tc_session_id")
        if not session_id:
            continue
        event_type = str(item.get("event_type") or item.get("event") or "unknown")
        booking_public_id = item.get("booking_id") or item.get("booking_public_id")
        booking_db_id = item.get("booking_db_id")
        if not booking_db_id and booking_public_id:
            booking_db_id = Booking.objects.filter(public_id=booking_public_id).values_list("id", flat=True).first()

        log_journey_event(
            session_id=str(session_id),
            event_type=event_type,
            step=str(item.get("step") or ""),
            cruise_code=str(item.get("cruise_code") or item.get("cruise_type") or ""),
            booking_id=booking_db_id,
            payload=item.get("payload") if isinstance(item.get("payload"), dict) else {},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referrer=request.META.get("HTTP_REFERER", ""),
            completed=bool(item.get("completed")),
            abandoned=bool(item.get("abandoned")),
        )
        created += 1
    return Response({"created": created}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def funnel_summary(request):
    days = int(request.query_params.get("days", 7))
    return Response(build_funnel_summary(days=days))


@api_view(["GET"])
@permission_classes([IsAdminUser])
def session_detail(request, session_id: str):
    return Response(get_session_timeline(session_id))
