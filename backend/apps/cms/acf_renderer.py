from __future__ import annotations

import html
import json
import re
from typing import Any

from django.template.loader import render_to_string

from apps.cms.media import set_media_map


BLOCK_RE = re.compile(
    r"<!--\s*wp:acf/(?P<name>[\w-]+)\s+(?P<payload>\{.*?\})\s*/-->",
    re.DOTALL,
)


def _ensure_list_item(parent: dict[str, Any], name: str, idx: int) -> dict[str, Any]:
    if name not in parent or not isinstance(parent.get(name), list):
        parent[name] = []
    items: list = parent[name]
    while len(items) <= idx:
        items.append({})
    return items[idx]


def _clean_acf_data(raw: dict[str, Any]) -> dict[str, Any]:
    root: dict[str, Any] = {}
    scalar: dict[str, Any] = {}
    rows: list[tuple[str, Any]] = []

    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if re.search(r"_\d+_", key):
            rows.append((key, value))
        else:
            scalar[key] = value

    row_keys = [k for k, _ in rows]

    for key, value in rows:
        # Skip repeater count markers when nested rows exist.
        if isinstance(value, int) and any(other.startswith(f"{key}_") for other in row_keys):
            continue

        parts = re.split(r"_(\d+)_", key)
        if len(parts) < 3:
            continue

        node: Any = root
        for i in range(0, len(parts) - 2, 2):
            name, idx_s = parts[i], parts[i + 1]
            idx = int(idx_s)
            if not isinstance(node, dict):
                break
            node = _ensure_list_item(node, name, idx)

        if isinstance(node, dict):
            node[parts[-1]] = value

    for key, value in scalar.items():
        existing = root.get(key)
        if isinstance(existing, list):
            continue
        if isinstance(value, int) and any(k.startswith(f"{key}_") for k in row_keys):
            continue
        root[key] = value
    return root


def parse_acf_blocks(content: str) -> list[dict[str, Any]]:
    blocks = []
    for match in BLOCK_RE.finditer(content):
        name = match.group("name")
        try:
            payload = json.loads(match.group("payload"))
        except json.JSONDecodeError:
            continue
        data = _clean_acf_data(payload.get("data", {}))
        blocks.append({"name": name, "data": data})
    return blocks


def render_blocks(
    content: str,
    *,
    media_map: dict[int, str] | None = None,
    locale: str = "en",
) -> str:
    media_map = media_map or {}
    set_media_map(media_map)

    parts: list[str] = []
    for block in parse_acf_blocks(content):
        template = f"blocks/{block['name']}.html"
        ctx = {
            "d": block["data"],
            "locale": locale,
        }
        try:
            parts.append(render_to_string(template, ctx))
        except Exception:
            parts.append(f"<!-- render error: {block['name']} -->")
    plain = BLOCK_RE.sub("", content).strip()
    if plain and not parts:
        parts.append(f'<div class="page-content">{html.escape(plain)}</div>')
    return "\n".join(parts)
