from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.db.models import Avg, Count
from django.utils import timezone

from apps.bookings.models import Booking

from .models import JourneyEvent, PageView, VisitorSession

# Шаги совпадают с cruise-booking.js: 1 = дата/круиз, 2 = контакты, 3 = оплата
BOOKING_FUNNEL_STEPS = [
    ("popup_open", "", "Открыл форму бронирования", "event"),
    ("step_view", "1", "Шаг 1 — дата и круиз", "event"),
    ("step_view", "2", "Шаг 2 — контакты", "event"),
    ("step_view", "3", "Шаг 3 — оплата", "event"),
    ("booking_created", "", "Создал бронь", "holds"),
    ("payment_started", "", "Открыл форму Stripe", "event"),
    ("payment_completed", "", "Оплатил", "paid"),
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


def _funnel_count(
    *,
    events,
    since,
    event_type: str,
    step: str,
    source: str,
    confirmed_bookings: int,
    booking_holds: int,
) -> int:
    if source == "paid":
        return confirmed_bookings
    if source == "holds":
        return booking_holds
    return _unique_sessions(events, event_type, step)


def build_funnel_summary(days: int = 7) -> dict:
    since = timezone.now() - timedelta(days=days)
    events = JourneyEvent.objects.filter(created_at__gte=since)

    page_stats = (
        PageView.objects.filter(entered_at__gte=since, is_active=False)
        .values("path")
        .annotate(
            views=Count("id"),
            avg_duration_ms=Avg("duration_ms"),
        )
        .order_by("-views")[:50]
    )

    sessions = VisitorSession.objects.filter(first_seen_at__gte=since)
    sessions_total = sessions.count()

    confirmed_bookings = Booking.objects.filter(
        status=Booking.Status.CONFIRMED,
        confirmed_at__gte=since,
    ).count()
    booking_holds = Booking.objects.filter(created_at__gte=since).count()
    pending_payment = Booking.objects.filter(
        created_at__gte=since,
        status=Booking.Status.PENDING_PAYMENT,
    ).count()

    funnel = []
    for event_type, step, label, source in BOOKING_FUNNEL_STEPS:
        unique = _funnel_count(
            events=events,
            since=since,
            event_type=event_type,
            step=step,
            source=source,
            confirmed_bookings=confirmed_bookings,
            booking_holds=booking_holds,
        )
        conversion_from_start = round((unique / sessions_total) * 100, 1) if sessions_total else 0
        funnel.append(
            {
                "event_type": event_type,
                "step": step,
                "label": label,
                "unique_sessions": unique,
                "conversion_from_start_pct": conversion_from_start,
            }
        )

    popup_opens = _unique_sessions(events, "popup_open")
    booking_rate = round((confirmed_bookings / popup_opens) * 100, 1) if popup_opens else 0

    return {
        "period_days": days,
        "sessions_total": sessions_total,
        "popup_opens": popup_opens,
        "confirmed_bookings": confirmed_bookings,
        "booking_holds": booking_holds,
        "pending_payment": pending_payment,
        "booking_conversion_pct": booking_rate,
        "funnel": funnel,
        "top_pages": [
            {
                "path": row["path"],
                "views": row["views"],
                "avg_duration_sec": round((row["avg_duration_ms"] or 0) / 1000, 1),
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
