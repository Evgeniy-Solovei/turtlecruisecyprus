from __future__ import annotations

import re
from datetime import date, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.bookings.models import Booking, Customer
from apps.cruises.models import Cruise, CruiseDateOverride, CruiseSchedule
from apps.cruises.time_utils import default_times_for_cruise, format_time_range
from apps.payments.models import Payment

from .wordpress_dump import first_meta, load_mpa_customers, load_options, load_postmeta, load_posts, load_seat_overrides


def minutes_to_time(value: int) -> time:
    return time(hour=value // 60, minute=value % 60)


def parse_first_timetable(serialized: str) -> tuple[list[int], int, int]:
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    day_names = re.findall(r's:\d+:"day";s:\d+:"([a-z]+)";', serialized)
    days = [day_map[name] for name in day_names if name in day_map]
    starts = [int(start) for start in re.findall(r's:\d+:"start";i:(\d+);', serialized)]
    ends = [int(end) for end in re.findall(r's:\d+:"end";i:(\d+);', serialized)]
    return days or list(range(7)), starts[0] if starts else 0, ends[0] if ends else 0


def parse_time_range(value: str, fallback_start: time, fallback_end: time) -> tuple[time, time]:
    match = re.search(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})", value or "")
    if not match:
        return fallback_start, fallback_end
    return time(int(match.group(1)), int(match.group(2))), time(int(match.group(3)), int(match.group(4)))


def booking_status_from_wp(post_status: str) -> str:
    if post_status == "confirmed":
        return Booking.Status.CONFIRMED
    if post_status == "cancelled":
        return Booking.Status.CANCELLED
    if post_status in {"pending", "new", "draft"}:
        return Booking.Status.PENDING_PAYMENT
    return Booking.Status.CANCELLED


def wp_post_datetime(post: dict):
    """Дата из wp_posts.post_date (когда бронь/оплата создана в WordPress)."""
    dt = parse_datetime((post.get("post_date") or "").strip())
    if not dt:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_default_timezone())
    return dt


@transaction.atomic
def import_dump(sql_path: str) -> dict[str, int]:
    options = load_options(sql_path)
    posts = load_posts(sql_path)
    meta = load_postmeta(sql_path)
    stats = {"cruises": 0, "schedules": 0, "overrides": 0, "customers": 0, "bookings": 0, "payments": 0}

    service_by_legacy: dict[int, Cruise] = {}
    for post in posts.values():
        if post["post_type"] != "mpa_service":
            continue
        legacy_id = post["id"]
        price = Decimal(first_meta(meta, legacy_id, "_mpa_price", "0") or "0")
        duration = int(first_meta(meta, legacy_id, "_mpa_duration", "0") or 0)
        capacity = int(first_meta(meta, legacy_id, "_mpa_max_capacity", "30") or 30)
        code = "morning" if legacy_id == 287 or "morning" in post["post_title"].lower() else "sunset"
        cruise, created = Cruise.objects.update_or_create(
            legacy_wp_service_id=legacy_id,
            defaults={
                "code": code,
                "name": post["post_title"],
                "default_adult_price": price,
                "default_child_price": Decimal(options.get("tc_price_child", "25") if code == "morning" else "0"),
                "child_allowed": code == "morning",
                "default_capacity": capacity,
                "default_duration_minutes": duration,
                "is_active": post["post_status"] == "publish",
                "sort_order": 10 if code == "morning" else 20,
            },
        )
        service_by_legacy[legacy_id] = cruise
        stats["cruises"] += int(created)

    for post in posts.values():
        if post["post_type"] != "mpa_schedule":
            continue
        legacy_schedule_id = post["id"]
        timetable = first_meta(meta, legacy_schedule_id, "_mpa_timetable", "")
        days, start, end = parse_first_timetable(timetable)
        cruise = service_by_legacy.get(287 if "morning" in post["post_title"].lower() else 290)
        if not cruise:
            continue
        CruiseSchedule.objects.filter(cruise=cruise, legacy_wp_schedule_id=legacy_schedule_id).exclude(weekday__in=days).delete()
        for day in days:
            _, created = CruiseSchedule.objects.update_or_create(
                cruise=cruise,
                weekday=day,
                legacy_wp_schedule_id=legacy_schedule_id,
                defaults={"start_time": minutes_to_time(start), "end_time": minutes_to_time(end), "is_active": post["post_status"] == "publish"},
            )
            stats["schedules"] += int(created)

    for row in load_seat_overrides(sql_path):
        cruise = service_by_legacy.get(row["service_id"])
        if not cruise:
            continue
        _, created = CruiseDateOverride.objects.update_or_create(
            cruise=cruise,
            date=date.fromisoformat(row["date"]),
            defaults={
                "capacity_override": row["max_seats"] if row["max_seats"] > 0 else None,
                "is_closed": row["is_closed"],
                "note": row["note"],
                "legacy_wp_id": row["legacy_id"],
            },
        )
        stats["overrides"] += int(created)

    customer_by_legacy: dict[int, Customer] = {}
    for row in load_mpa_customers(sql_path):
        if not row["email"]:
            continue
        parts = row["name"].split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        customer, created = Customer.objects.update_or_create(
            legacy_wp_customer_id=row["id"],
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": row["email"].strip().lower(),
                "phone": row["phone"],
            },
        )
        customer_by_legacy[row["id"]] = customer
        stats["customers"] += int(created)

    reservations_by_booking = {
        post["post_parent"]: post for post in posts.values() if post["post_type"] == "mpa_reservation" and post["post_parent"]
    }

    for post in posts.values():
        if post["post_type"] != "mpa_booking":
            continue
        legacy_id = post["id"]
        reservation = reservations_by_booking.get(legacy_id)
        service_id = int(first_meta(meta, reservation["id"], "_mpa_service", "0") or 0) if reservation else 0
        cruise_type = first_meta(meta, legacy_id, "_tc_cruise_type", "")
        cruise = service_by_legacy.get(service_id) or Cruise.objects.filter(code=cruise_type or "morning").first()
        if not cruise:
            continue
        try:
            fallback_start, fallback_end, _ = default_times_for_cruise(cruise)
        except ValueError:
            fallback_start, fallback_end = time(9, 30), time(14, 0)
        reservation_id = reservation["id"] if reservation else None
        reservation_date = first_meta(meta, reservation_id, "_mpa_date", "") if reservation_id else ""
        start_time, end_time = parse_time_range(first_meta(meta, reservation_id, "_mpa_service_time", ""), fallback_start, fallback_end) if reservation_id else (fallback_start, fallback_end)
        total_seats = int(first_meta(meta, reservation_id, "_mpa_capacity", "0") or 0) if reservation_id else 0
        adults = int(first_meta(meta, legacy_id, "_tc_adults", "0") or 0)
        children = int(first_meta(meta, legacy_id, "_tc_children", "0") or 0)
        if total_seats <= 0:
            total_seats = adults + children or 1
        if adults <= 0:
            adults = max(total_seats - children, 1)
        customer_id = int(first_meta(meta, legacy_id, "_mpa_customer_id", "0") or 0)
        customer = customer_by_legacy.get(customer_id)
        if not customer:
            customer_defaults = {
                "first_name": "Legacy",
                "last_name": f"Booking {legacy_id}",
                "email": f"legacy-{legacy_id}@example.invalid",
                "phone": "",
            }
            if customer_id:
                customer, _ = Customer.objects.update_or_create(legacy_wp_customer_id=customer_id, defaults=customer_defaults)
            else:
                customer, _ = Customer.objects.update_or_create(email=customer_defaults["email"], defaults=customer_defaults)
        booking_status = booking_status_from_wp(post["post_status"])
        confirmed_at = wp_post_datetime(post) if booking_status == Booking.Status.CONFIRMED else None
        booking, created = Booking.objects.update_or_create(
            legacy_wp_booking_id=legacy_id,
            defaults={
                "customer": customer,
                "cruise": cruise,
                "cruise_date": date.fromisoformat(reservation_date) if reservation_date else date.today(),
                "start_time": start_time,
                "end_time": end_time,
                "adults_count": adults,
                "children_count": children,
                "total_seats": total_seats,
                "adult_unit_price": cruise.default_adult_price,
                "child_unit_price": cruise.default_child_price,
                "total_amount": Decimal(first_meta(meta, reservation_id, "_mpa_total_price", "") or first_meta(meta, legacy_id, "_tc_total", "0") or "0"),
                "status": booking_status,
                "source": "migration",
                "legacy_wp_reservation_id": reservation_id,
                "confirmed_at": confirmed_at,
            },
        )
        stats["bookings"] += int(created)

    for post in posts.values():
        if post["post_type"] != "mpa_payment":
            continue
        booking_id = int(first_meta(meta, post["id"], "_mpa_booking_id", "0") or 0)
        booking = Booking.objects.filter(legacy_wp_booking_id=booking_id).first()
        if not booking:
            continue
        paid_at = wp_post_datetime(post)
        _, created = Payment.objects.update_or_create(
            booking=booking,
            transaction_id=first_meta(meta, post["id"], "_mpa_transaction_id", "") or f"legacy-payment-{post['id']}",
            defaults={
                "amount": Decimal(first_meta(meta, post["id"], "_mpa_amount", "0") or "0"),
                "currency": first_meta(meta, post["id"], "_mpa_currency", "EUR") or "EUR",
                "status": Payment.Status.SUCCEEDED,
                "idempotency_key": f"legacy-payment:{post['id']}",
                "raw_provider_status": post["post_status"],
                "paid_at": paid_at,
            },
        )
        stats["payments"] += int(created)

    return stats
