from __future__ import annotations

import re
from typing import Any

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
    return f"/media/wp/{rel.lstrip('/')}"


def fix_media_urls_in_html(html: str) -> str:
    """Rewrite broken imported media URLs in stored HTML."""
    if not html:
        return html
    return re.sub(
        r"/media/wp/home/ochihost/[^/]+/www/wp-content/uploads/",
        "/media/wp/",
        html,
    )
