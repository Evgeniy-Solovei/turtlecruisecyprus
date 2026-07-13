from __future__ import annotations

import re
from typing import Any

from .asset_urls import STATIC_DIST_FILENAMES, STATIC_DIST_PREFIX, resolve_public_asset_url
from .site_media import resolve_site_media_url, rewrite_html_media_urls

_media_map: dict[int, str] = {}


def normalize_wp_media_path(rel: str) -> str:
    """Turn WP attachment paths into `2026/05/file.webp` regardless of server prefix."""
    rel = (rel or "").strip().lstrip("/")
    if not rel:
        return ""
    lowered = rel.lower()
    marker = "wp-content/uploads/"
    idx = lowered.find(marker)
    if idx >= 0:
        return rel[idx + len(marker) :]
    return rel


def set_media_map(media_map: dict[int, str] | None) -> None:
    global _media_map
    _media_map = media_map or {}


def get_media_map() -> dict[int, str]:
    return _media_map


def resolve_attachment(media_map: dict[int, str], attachment_id: Any) -> str:
    if not attachment_id:
        return ""
    try:
        aid = int(attachment_id)
    except (TypeError, ValueError):
        return ""
    rel = normalize_wp_media_path(media_map.get(aid, ""))
    if not rel:
        return ""
    static_url = resolve_site_media_url(f"/media/wp/{rel.lstrip('/')}")
    return static_url


def fix_media_urls_in_html(html: str) -> str:
    """Rewrite broken imported media URLs in stored HTML."""
    if not html:
        return html
    html = re.sub(
        r"/media/wp/home/ochihost/[^/]+/www/wp-content/uploads/",
        "/media/wp/",
        html,
    )
    html = re.sub(
        r'src="/img/dist/([^"]+)"',
        rf'src="{STATIC_DIST_PREFIX}\1"',
        html,
    )
    for name in STATIC_DIST_FILENAMES:
        html = re.sub(
            rf"/media/wp/[^\"'>]*{re.escape(name)}",
            f"{STATIC_DIST_PREFIX}{name}",
            html,
        )
    return rewrite_html_media_urls(html)


def resolve_attachment_url(url: str) -> str:
    return resolve_site_media_url(resolve_public_asset_url(url))
