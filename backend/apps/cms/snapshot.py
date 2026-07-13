from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

SNAPSHOT_PATH = Path(settings.BASE_DIR) / "cms_snapshot" / "snapshot.json"


def export_cms_snapshot(path: Path | None = None) -> dict[str, int]:
    from apps.cms.models import BlogPost, SiteConfig, SitePage

    target = path or SNAPSHOT_PATH
    payload: dict[str, Any] = {
        "pages": list(
            SitePage.objects.order_by("locale", "slug").values(
                "locale",
                "slug",
                "wp_slug",
                "title",
                "body_html",
                "body_class",
                "is_published",
            )
        ),
        "configs": list(SiteConfig.objects.order_by("key").values("key", "value")),
        "posts": list(
            BlogPost.objects.order_by("slug").values(
                "slug",
                "title",
                "body",
                "excerpt",
                "hero_image",
                "cover_image_static",
                "is_published",
                "published_at",
            )
        ),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "pages": len(payload["pages"]),
        "configs": len(payload["configs"]),
        "posts": len(payload["posts"]),
        "path": str(target),
    }


def import_cms_snapshot(path: Path | None = None) -> dict[str, int]:
    from apps.cms.models import BlogPost, SiteConfig, SitePage

    target = path or SNAPSHOT_PATH
    if not target.is_file():
        raise FileNotFoundError(f"CMS snapshot not found: {target}")

    payload = json.loads(target.read_text(encoding="utf-8"))
    stats = {"pages": 0, "configs": 0, "posts": 0}

    with transaction.atomic():
        for row in payload.get("pages") or []:
            SitePage.objects.update_or_create(
                locale=row["locale"],
                slug=row["slug"],
                defaults={
                    "wp_slug": row.get("wp_slug", ""),
                    "title": row.get("title", ""),
                    "body_html": row.get("body_html", ""),
                    "body_class": row.get("body_class", ""),
                    "is_published": bool(row.get("is_published", True)),
                },
            )
            stats["pages"] += 1

        for row in payload.get("configs") or []:
            SiteConfig.objects.update_or_create(
                key=row["key"],
                defaults={"value": row.get("value") or {}},
            )
            stats["configs"] += 1

        for row in payload.get("posts") or []:
            BlogPost.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "title": row.get("title", ""),
                    "body": row.get("body", ""),
                    "excerpt": row.get("excerpt", ""),
                    "hero_image": row.get("hero_image", ""),
                    "cover_image_static": row.get("cover_image_static", ""),
                    "is_published": bool(row.get("is_published", True)),
                    "published_at": row.get("published_at"),
                },
            )
            stats["posts"] += 1

    return stats
