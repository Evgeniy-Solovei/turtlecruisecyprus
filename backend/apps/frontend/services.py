from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings

from apps.cruises.models import CruiseDateOverride
from apps.cruises.selectors import get_active_cruises
from apps.cruises.time_utils import default_times_for_cruise

from .i18n import BOOKING_I18N, DEFAULT_LOCALE, localized_path


def _working_weekdays(cruise) -> list[int]:
    weekdays = sorted({s.weekday for s in cruise.schedules.all() if s.is_active})
    return weekdays if weekdays else list(range(7))


def _days_off(cruise) -> list[str]:
    return [
        row.date.isoformat()
        for row in CruiseDateOverride.objects.filter(cruise=cruise, is_closed=True).order_by("date")
    ]


def build_booking_config(locale: str = DEFAULT_LOCALE) -> dict:
    cruises = list(get_active_cruises())
    prices: dict[str, float] = {}
    services: dict[str, dict] = {}
    capacity: dict[str, int] = {}
    days_off: dict[str, list[str]] = {}
    working_days: dict[str, list[int]] = {}
    content: dict[str, str] = {}

    routes = {
        "morning": "Ayia Napa Harbour (Limanaki) — Protaras",
        "sunset": "Ayia Napa Harbour (Limanaki) — Konnos Bay",
    }

    for cruise in cruises:
        code = cruise.code
        prices[f"{code}_adult"] = float(cruise.default_adult_price)
        if cruise.child_allowed and code == "morning":
            prices["morning_child"] = float(cruise.default_child_price)

        hours = cruise.default_duration_minutes // 60
        minutes = cruise.default_duration_minutes % 60
        duration_label = f"{hours}h" + (f" {minutes}m" if minutes else "")

        try:
            _, _, time_label = default_times_for_cruise(cruise)
        except ValueError:
            time_label = ""

        services[code] = {
            "title": cruise.name,
            "description": cruise.description,
            "duration_label": duration_label,
        }
        capacity[code] = cruise.default_capacity
        days_off[code] = _days_off(cruise)
        working_days[code] = _working_weekdays(cruise)
        content[f"{code}_route"] = routes.get(code, "")
        content[f"{code}_time"] = time_label

    min_date = (date.today() + timedelta(days=1)).isoformat()

    t = BOOKING_I18N.get(locale, BOOKING_I18N[DEFAULT_LOCALE])

    return {
        "apiBaseUrl": "/api/v1",
        "stripeKey": settings.STRIPE_PUBLIC_KEY or "",
        "thankYouUrl": localized_path(locale, "/thank-you/"),
        "gtmContainerId": getattr(settings, "GTM_CONTAINER_ID", ""),
        "prices": prices,
        "services": services,
        "capacity": capacity,
        "daysOff": days_off,
        "workingDays": working_days,
        "minDate": min_date,
        "content": {
            **content,
            "phone": settings.SUPPORT_PHONE or "+357 97 719 450",
        },
        "i18n": {
            "selectDate": t.get("select_date", "Please select a date."),
            "selectCruise": t.get("select_cruise", "Please select a cruise."),
            "agreeTerms": t.get("agree_terms_required", "Please tick the box to confirm you have read and agree to the Terms and Conditions."),
            "checkout": t.get("checkout", "Checkout"),
            "enterFirstName": t.get("enter_first_name", "Please enter your first name."),
            "enterLastName": t.get("enter_last_name", "Please enter your last name."),
            "enterEmail": t.get("enter_email", "Please enter your email address."),
            "invalidEmail": t.get("invalid_email", "Please enter a valid email address."),
            "enterPhone": t.get("enter_phone", "Please enter your phone number."),
            "invalidPhoneGeneric": t.get("invalid_phone_generic", "Please enter a valid mobile number with country code."),
            "invalidPhoneCountry": t.get("invalid_phone_country", "Please choose the correct country code."),
            "invalidPhoneTooShort": t.get("invalid_phone_too_short", "This phone number looks too short."),
            "invalidPhoneTooLong": t.get("invalid_phone_too_long", "This phone number looks too long."),
            "invalidPhoneNotNumber": t.get("invalid_phone_not_number", "Please enter digits only."),
            "paymentNotReady": "Payment not ready. Please wait.",
            "fullyBooked": "Sorry, this date is fully booked.",
            "fullyBookedPaymentMsg": t.get("fully_booked_msg", "All seats for this date have just been booked."),
            "tooManySeats": t.get("too_many_seats", "You can only book up to {n} seats for this date."),
            "spotsLeft": "spots left!",
            "spotsAvailable": "spots available.",
            "dayOff": "This date is not available (day off).",
            "noCruises": "No cruises on this day.",
            "route": "Route:",
            "adults": t.get("adults", "Adults") + ":",
            "children": t.get("children", "Children") + ":",
            "total": t.get("total", "Total:"),
            "perPerson": "per person",
            "includingBbq": "including BBQ",
            "sessionExpired": "Session expired",
            "sessionExpiredMsg": "Your reservation time has expired. Please start a new booking.",
            "startNewBooking": "Start New Booking",
            "processing": "Processing...",
            "paymentConfirmFailed": t.get(
                "payment_confirm_failed",
                "We could not verify your payment automatically. Please contact us with your booking number.",
            ),
        },
    }
