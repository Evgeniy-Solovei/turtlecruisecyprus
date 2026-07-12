from __future__ import annotations

import re
from typing import Any

from django import template

from apps.cms.media import get_media_map, resolve_attachment, set_media_map
from apps.cms.models import BlogPost

register = template.Library()


@register.simple_tag
def media(attachment_id: Any) -> str:
    if isinstance(attachment_id, str):
        value = attachment_id.strip()
        if value.startswith(("/", "http://", "https://")):
            return value
    return resolve_attachment(get_media_map(), attachment_id)


@register.filter
def phone_digits(value: str) -> str:
    return re.sub(r"[^0-9+]", "", value or "")


@register.filter
def stars_for(item: dict, global_stars: int = 5) -> int:
    try:
        return int(item.get("stars") or global_stars)
    except (TypeError, ValueError):
        return global_stars


@register.filter
def reviews_column(items: list, col: int) -> list:
    items = items or []
    if col == 1:
        return [items[i] for i in range(0, len(items), 2)]
    return [items[i] for i in range(1, len(items), 2)]


@register.simple_tag
def guest_photo_columns(items: list | None) -> list[tuple[bool, list]]:
    configs = [
        (False, 4),
        (True, 3),
        (False, 4),
        (True, 3),
        (False, 4),
        (True, 3),
    ]
    items = items or []
    columns: list[tuple[bool, list]] = []
    offset = 0
    for is_offset, count in configs:
        chunk = items[offset : offset + count]
        offset += count
        if chunk:
            columns.append((is_offset, chunk))
    return columns


@register.simple_tag
def gallery_masonry_columns(items: list | None) -> list[tuple[bool, list]]:
    items = items or []
    configs = [True, False, True, False]
    columns: list[list] = [[], [], [], []]
    for i, item in enumerate(items):
        columns[i % 4].append(item)
    return [(configs[i], col) for i, col in enumerate(columns) if col]


@register.inclusion_tag("blocks/includes/blog-page-posts.html", takes_context=False)
def blog_page_posts(per_page: int = 9, load_more_label: str = "Load MORE"):
    per_page = max(int(per_page or 9), 1)
    qs = BlogPost.objects.filter(is_published=True)
    total = qs.count()
    max_pages = max((total + per_page - 1) // per_page, 1)
    posts = list(qs[:per_page])
    return {
        "posts": posts,
        "per_page": per_page,
        "max_pages": max_pages,
        "has_more": max_pages > 1,
        "load_more_label": load_more_label,
    }
