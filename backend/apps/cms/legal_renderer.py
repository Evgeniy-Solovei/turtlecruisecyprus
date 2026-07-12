from __future__ import annotations

import html
import re
from typing import Any


def _block_count(fields: dict[str, list[str]], prefix: str = "blocks") -> int:
    indices = set()
    for key in fields:
        m = re.match(rf"^{prefix}_(\d+)_", key)
        if m:
            indices.add(int(m.group(1)))
    return max(indices) + 1 if indices else 0


def render_genesis_legal_html(fields: dict[str, list[str]]) -> str:
    """Build legal page HTML from Genesis Custom Blocks postmeta."""
    parts: list[str] = []
    count = _block_count(fields)
    for i in range(count):
        title = _first(fields, f"blocks_{i}_title")
        text = _first(fields, f"blocks_{i}_text")
        bg_type = _first(fields, f"blocks_{i}_type_bg")

        if bg_type == "Image":
            hero_text = text or title
            if hero_text:
                parts.append(f'<p class="legal-hero">{html.unescape(hero_text)}</p>')
            continue

        if title:
            parts.append(f"<h2>{html.unescape(title)}</h2>")

        if text and not title:
            parts.append(f"<p>{html.unescape(text)}</p>")

        content_keys = sorted(
            k
            for k in fields
            if k.startswith(f"blocks_{i}_blocks_content_")
            and k.endswith("_content")
            and not k.startswith("_")
        )
        for ck in content_keys:
            body = _first(fields, ck)
            if body:
                parts.append(html.unescape(body))

    return "\n".join(parts)


def _first(fields: dict[str, list[str]], key: str) -> str:
    vals = fields.get(key) or []
    return vals[0] if vals else ""
