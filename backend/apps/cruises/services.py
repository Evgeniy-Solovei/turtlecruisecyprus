from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import Cruise
from .selectors import get_date_override, get_schedule_for_date


def effective_capacity(cruise: Cruise, cruise_date: date) -> int:
    override = get_date_override(cruise, cruise_date)
    if override and override.capacity_override is not None:
        return override.capacity_override
    return cruise.default_capacity


def effective_prices(cruise: Cruise, cruise_date: date) -> tuple[Decimal, Decimal]:
    override = get_date_override(cruise, cruise_date)
    adult = override.adult_price_override if override and override.adult_price_override is not None else cruise.default_adult_price
    child = override.child_price_override if override and override.child_price_override is not None else cruise.default_child_price
    return adult, child


def is_bookable(cruise: Cruise, cruise_date: date) -> bool:
    override = get_date_override(cruise, cruise_date)
    if override and override.is_closed:
        return False
    return get_schedule_for_date(cruise, cruise_date) is not None
