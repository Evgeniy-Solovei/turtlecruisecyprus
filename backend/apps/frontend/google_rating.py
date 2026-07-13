from __future__ import annotations

import logging
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "site:google_rating"
CACHE_TTL = 60 * 60 * 12  # 12h


def _fetch_places_api() -> dict[str, Any] | None:
    api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", "")
    place_id = getattr(settings, "GOOGLE_PLACE_ID", "")
    if not api_key or not place_id:
        return None

    query = urlencode(
        {
            "place_id": place_id,
            "fields": "rating,user_ratings_total,url",
            "key": api_key,
        }
    )
    url = f"https://maps.googleapis.com/maps/api/place/details/json?{query}"
    try:
        with urlopen(url, timeout=10) as resp:
            import json

            payload = json.loads(resp.read().decode())
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Google Places API failed: %s", exc)
        return None

    if payload.get("status") != "OK":
        logger.warning("Google Places API status: %s", payload.get("status"))
        return None

    result = payload.get("result") or {}
    count = result.get("user_ratings_total")
    score = result.get("rating")
    if count is None and score is None:
        return None

    return {
        "score": str(score or getattr(settings, "GOOGLE_RATING_SCORE", "4.9")),
        "count": int(count or getattr(settings, "GOOGLE_REVIEW_COUNT", 840)),
        "url": result.get("url") or getattr(settings, "GOOGLE_MAPS_URL", ""),
        "source": "google",
    }


def get_site_rating() -> dict[str, Any]:
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    live = _fetch_places_api()
    if live:
        data = live
    else:
        count = int(getattr(settings, "GOOGLE_REVIEW_COUNT", 840))
        data = {
            "score": getattr(settings, "GOOGLE_RATING_SCORE", "4.9"),
            "count": count,
            "url": getattr(settings, "GOOGLE_MAPS_URL", ""),
            "source": "env",
        }

    data["label_en"] = f"Based on {data['count']} reviews"
    data["label_de"] = f"Basierend auf {data['count']} Bewertungen"
    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data
