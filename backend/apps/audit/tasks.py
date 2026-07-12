from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.db.models import Avg, Count
from django.utils import timezone

from .models import JourneyEvent, PageView, VisitorSession

BOOKING_FUNNEL_STEPS = [
    ("popup_open", "", "Открыл форму бронирования"),
    ("step_view", "1", "Шаг 1 — дата"),
    ("step_view", "2", "Шаг 2 — пассажиры"),
    ("step_view", "3", "Шаг 3 — контакты"),
    ("step_view", "4", "Шаг 4 — оплата"),
    ("booking_created", "", "Создал бронь (hold)"),
    ("payment_started", "", "Начал оплату"),
    ("payment_completed", "", "Оплатил"),
]


@shared_task(name="apps.audit.tasks.mark_abandoned_sessions")
def mark_abandoned_sessions() -> int:
    """Помечает сессии бронирования без активности как брошенные."""
    cutoff = timezone.now() - timedelta(minutes=45)
    qs = VisitorSession.objects.filter(
        is_completed=False,
        is_abandoned=False,
        last_seen_at__lt=cutoff,
    ).exclude(last_step="")
    count = qs.update(is_abandoned=True)
    return count


@shared_task(name="apps.audit.tasks.finalize_stale_page_views")
def finalize_stale_page_views() -> int:
    """Закрывает зависшие page views, если браузер не прислал page_exit."""
    cutoff = timezone.now() - timedelta(minutes=20)
    stale = PageView.objects.filter(is_active=True, entered_at__lt=cutoff)
    count = 0
    for page_view in stale.iterator():
        page_view.duration_ms = max(page_view.duration_ms, int((cutoff - page_view.entered_at).total_seconds() * 1000))
        page_view.is_active = False
        page_view.left_at = timezone.now()
        page_view.save(update_fields=["duration_ms", "is_active", "left_at"])
        JourneyEvent.objects.create(
            session=page_view.session,
            event_type="page_exit",
            payload={
                "path": page_view.path,
                "view_id": page_view.view_id,
                "duration_ms": page_view.duration_ms,
                "scroll_depth_pct": page_view.scroll_depth_pct,
                "source": "stale_finalize",
            },
        )
        count += 1
    return count


def _unique_sessions(events, event_type: str, step: str = "") -> int:
    qs = events.filter(event_type=event_type)
    if step:
        qs = qs.filter(step=step)
    return qs.values("session_id").distinct().count()


def build_funnel_summary(days: int = 7) -> dict:
    since = timezone.now() - timedelta(days=days)
    events = JourneyEvent.objects.filter(created_at__gte=since)

    step_counts = (
        events.exclude(step="")
        .values("step", "event_type")
        .annotate(count=Count("id"))
        .order_by("step")
    )

    page_stats = (
        PageView.objects.filter(entered_at__gte=since, is_active=False)
        .values("path")
        .annotate(
            views=Count("id"),
            avg_duration_ms=Avg("duration_ms"),
            avg_scroll_pct=Avg("scroll_depth_pct"),
        )
        .order_by("-views")[:50]
    )

    sessions = VisitorSession.objects.filter(first_seen_at__gte=since)
    sessions_total = sessions.count()

    funnel = []
    prev_unique = None
    for event_type, step, label in BOOKING_FUNNEL_STEPS:
        unique = _unique_sessions(events, event_type, step)
        conversion_from_start = round((unique / sessions_total) * 100, 1) if sessions_total else 0
        conversion_from_prev = round((unique / prev_unique) * 100, 1) if prev_unique else None
        funnel.append(
            {
                "event_type": event_type,
                "step": step,
                "label": label,
                "unique_sessions": unique,
                "conversion_from_start_pct": conversion_from_start,
                "conversion_from_prev_pct": conversion_from_prev,
            }
        )
        if unique:
            prev_unique = unique

    popup_opens = _unique_sessions(events, "popup_open")
    payments_done = _unique_sessions(events, "payment_completed")
    booking_rate = round((payments_done / popup_opens) * 100, 1) if popup_opens else 0

    return {
        "period_days": days,
        "sessions_total": sessions_total,
        "sessions_completed": sessions.filter(is_completed=True).count(),
        "sessions_abandoned": sessions.filter(is_abandoned=True).count(),
        "booking_conversion_pct": booking_rate,
        "funnel": funnel,
        "step_events": list(step_counts),
        "top_pages": [
            {
                "path": row["path"],
                "views": row["views"],
                "avg_duration_sec": round((row["avg_duration_ms"] or 0) / 1000, 1),
                "avg_scroll_pct": round(row["avg_scroll_pct"] or 0, 1),
            }
            for row in page_stats
        ],
    }


def get_session_timeline(session_id: str) -> dict:
    session = VisitorSession.objects.filter(session_id=session_id).select_related("booking").first()
    if not session:
        return {"found": False, "session_id": session_id}

    page_views = list(
        session.page_views.order_by("entered_at").values(
            "view_id",
            "path",
            "page_title",
            "duration_ms",
            "scroll_depth_pct",
            "entered_at",
            "left_at",
            "is_active",
        )
    )
    journey = list(
        session.events.order_by("created_at").values(
            "created_at",
            "event_type",
            "step",
            "cruise_code",
            "payload",
            "booking_id",
        )
    )

    total_time_ms = sum(pv["duration_ms"] or 0 for pv in page_views if not pv["is_active"])

    return {
        "found": True,
        "session": {
            "session_id": session.session_id,
            "booking_public_id": session.booking.public_id if session.booking_id else None,
            "last_step": session.last_step,
            "last_event": session.last_event,
            "is_completed": session.is_completed,
            "is_abandoned": session.is_abandoned,
            "first_seen_at": session.first_seen_at,
            "last_seen_at": session.last_seen_at,
            "referrer": session.referrer,
            "total_page_time_sec": round(total_time_ms / 1000, 1),
        },
        "page_views": page_views,
        "journey_events": journey,
    }
