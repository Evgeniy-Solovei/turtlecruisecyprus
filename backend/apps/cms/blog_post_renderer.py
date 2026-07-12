from __future__ import annotations

import html
import re
from typing import Any

from apps.cms.media import resolve_attachment


def _first(fields: dict[str, list[str]], key: str) -> str:
    vals = fields.get(key) or []
    return vals[0] if vals else ""


def _parse_layouts(fields: dict[str, list[str]]) -> list[str]:
    raw = _first(fields, "blocks")
    if not raw:
        return []
    return re.findall(r's:\d+:"([^"]+)"', raw)


def _gallery_html(fields: dict[str, list[str]], index: int, media_map: dict[int, str]) -> str:
    image_keys = sorted(
        k
        for k in fields
        if re.match(rf"^blocks_{index}_images_\d+_image$", k)
    )
    if not image_keys:
        return ""

    cols: list[str] = []
    for key in image_keys:
        img_id = _first(fields, key)
        alt_key = key.replace("_image", "_alt")
        alt = html.escape(_first(fields, alt_key))
        src = resolve_attachment(media_map, img_id)
        if not src:
            continue
        cols.append(
            f'<div class="col"><div class="image object-fit">'
            f'<img src="{src}" alt="{alt}"></div></div>'
        )
    if not cols:
        return ""
    return f'<div class="gallery-flex">{"".join(cols)}</div>'


def render_blog_post_body(
    fields: dict[str, list[str]],
    *,
    media_map: dict[int, str] | None = None,
) -> str:
    """Render single-post content HTML from ACF flexible `blocks` postmeta."""
    media_map = media_map or {}
    layouts = _parse_layouts(fields)
    parts: list[str] = []

    for index, layout in enumerate(layouts):
        if layout == "content":
            text = _first(fields, f"blocks_{index}_text")
            if text:
                parts.append(html.unescape(text))
        elif layout == "gallery":
            gallery = _gallery_html(fields, index, media_map)
            if gallery:
                parts.append(gallery)

    return "\n".join(parts)


def hero_image_url(
    fields: dict[str, list[str]],
    *,
    media_map: dict[int, str] | None = None,
) -> str:
    media_map = media_map or {}
    hero_id = _first(fields, "hero_image")
    return resolve_attachment(media_map, hero_id)


def excerpt_from_body(body_html: str, *, max_len: int = 200) -> str:
    text = re.sub(r"<[^>]+>", " ", body_html or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."
