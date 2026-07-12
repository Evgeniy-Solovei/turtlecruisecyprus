from __future__ import annotations

import re

# UI assets that ship in git under static/frontend/img/dist/ (not /media/wp/).
STATIC_DIST_FILENAMES = frozenset(
    {
        "visa.svg",
        "mastercard.svg",
        "paypal.svg",
        "revolut.svg",
        "footer-logo.svg",
        "ochi.svg",
        "logo.svg",
        "logo-mob.svg",
        "location-icon.svg",
        "buy-icon.svg",
        "wave.svg",
        "timer.svg",
        "duration.svg",
        "food.svg",
        "stop-timer.svg",
    }
)

STATIC_DIST_PREFIX = "/static/frontend/img/dist/"


def resolve_public_asset_url(url: str) -> str:
    """Prefer git-shipped static paths for known UI icons and fix broken WP paths."""
    url = (url or "").strip()
    if not url:
        return url

    if url.startswith("/img/dist/"):
        return f"{STATIC_DIST_PREFIX}{url.removeprefix('/img/dist/')}"
    if url.startswith("img/dist/"):
        return f"{STATIC_DIST_PREFIX}{url.removeprefix('img/dist/')}"

    filename = url.rsplit("/", 1)[-1].split("?", 1)[0]
    if filename in STATIC_DIST_FILENAMES:
        return f"{STATIC_DIST_PREFIX}{filename}"

    return url


def normalize_footer_config(footer: dict) -> dict:
    if not footer:
        return footer

    out = dict(footer)
    icons = []
    for icon in out.get("payment_icons") or []:
        if not isinstance(icon, dict):
            continue
        icons.append({**icon, "url": resolve_public_asset_url(icon.get("url", ""))})
    out["payment_icons"] = icons
    out["footer_logo"] = resolve_public_asset_url(out.get("footer_logo", ""))
    out["made_by_logo"] = resolve_public_asset_url(out.get("made_by_logo", ""))
    return out
