from __future__ import annotations

import json

from django.conf import settings

from apps.cms.models import SiteConfig
from apps.cruises.selectors import get_active_cruises
from apps.cruises.time_utils import default_times_for_cruise

from .i18n import (
    BOOKING_I18N,
    DEFAULT_LOCALE,
    footer_legal_for_locale,
    footer_nav_cols_for_locale,
    language_links,
    locale_prefix,
    nav_for_locale,
)
from .seo import default_seo_meta
from .services import build_booking_config


def _cruise_cards():
    cards = []
    for cruise in get_active_cruises():
        try:
            _, _, time_label = default_times_for_cruise(cruise)
        except ValueError:
            time_label = ""
        cards.append(
            {
                "code": cruise.code,
                "name": cruise.name.upper(),
                "time_label": time_label,
                "adult_price": int(cruise.default_adult_price),
                "child_price": int(cruise.default_child_price) if cruise.child_allowed else None,
                "child_allowed": cruise.child_allowed,
            }
        )
    return cards


def booking_config(request):
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    config = build_booking_config(locale)
    socials = {}
    footer = {}
    try:
        row = SiteConfig.objects.filter(key="socials").first()
        if row:
            socials = row.value
        frow = SiteConfig.objects.filter(key="footer").first()
        if frow:
            footer = frow.value
    except Exception:
        pass

    locale_footer = (footer.get(locale) or footer.get("en") or {}) if footer else {}
    t = BOOKING_I18N.get(locale, BOOKING_I18N[DEFAULT_LOCALE])
    path = request.path_info
    if locale != DEFAULT_LOCALE and path.startswith(f"/{locale}"):
        path = path[len(locale) + 1 :] or "/"

    return {
        "booking_config_json": json.dumps(config),
        "cruise_cards": _cruise_cards(),
        "site": {
            "lang": locale,
            "prefix": locale_prefix(locale),
            "book_label": t["book_now"],
            "nav_links": nav_for_locale(locale),
            "footer_nav_cols": footer_nav_cols_for_locale(locale),
            "footer_legal": footer_legal_for_locale(locale),
            "footer": {
                **locale_footer,
                "copyright": footer.get("copyright", ""),
                "payments_label": footer.get("payments_label", "Available"),
                "payment_icons": footer.get("payment_icons", []),
                "made_by_label": footer.get("made_by_label", "Made by"),
                "made_by_url": footer.get("made_by_url", ""),
                "made_by_logo": footer.get("made_by_logo", ""),
                "footer_logo": footer.get("footer_logo", ""),
            },
            "socials": socials or {
                "tiktok": "https://www.tiktok.com/",
                "instagram": "https://www.instagram.com/",
                "facebook": "https://www.facebook.com/",
                "youtube": "https://www.youtube.com/",
            },
        },
        "t": t,
        "lang_links": language_links(locale, path),
        "current_locale": locale.upper(),
        "is_home": path in ("/", ""),
        "seo": default_seo_meta(request),
        "gtm_container_id": getattr(settings, "GTM_CONTAINER_ID", ""),
    }
