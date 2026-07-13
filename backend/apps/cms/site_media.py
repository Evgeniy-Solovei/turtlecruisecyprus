from __future__ import annotations

import re
import shutil
from pathlib import Path

from django.conf import settings

# Site photos vendored into git — served by WhiteNoise (no /media volume needed).
SITE_MEDIA_STATIC_PREFIX = "/static/frontend/img/site/"
SITE_MEDIA_STATIC_ROOT = Path(settings.BASE_DIR) / "static" / "frontend" / "img" / "site"


def _normalize_rel(rel: str) -> str:
    rel = (rel or "").strip().lstrip("/")
    if not rel:
        return ""
    marker = "wp-content/uploads/"
    idx = rel.lower().find(marker)
    if idx >= 0:
        return rel[idx + len(marker) :]
    return rel


def site_media_static_root() -> Path:
    return SITE_MEDIA_STATIC_ROOT


def site_media_public_url(rel: str) -> str | None:
    rel = _normalize_rel(rel)
    if not rel:
        return None
    if (SITE_MEDIA_STATIC_ROOT / rel).is_file():
        return f"{SITE_MEDIA_STATIC_PREFIX}{rel}"
    return None


def resolve_site_media_url(url: str) -> str:
    """Prefer vendored static copy over /media/wp/ (reliable on deploy)."""
    url = (url or "").strip()
    if not url:
        return url
    if url.startswith(SITE_MEDIA_STATIC_PREFIX):
        return url
    marker = "/media/wp/"
    if marker in url:
        rel = url.split(marker, 1)[1].split("?", 1)[0]
        static_url = site_media_public_url(rel)
        if static_url:
            return static_url
    return url


def rewrite_html_media_urls(html: str) -> str:
    if not html:
        return html

    def _sub(match: re.Match[str]) -> str:
        rel = match.group(1)
        static_url = site_media_public_url(rel)
        return static_url or match.group(0)

    return re.sub(r"/media/wp/([^\"'>\s\)]+)", _sub, html)


def collect_referenced_wp_paths() -> set[str]:
    from apps.cms.models import BlogPost, SiteConfig, SitePage

    paths: set[str] = set()
    pattern = re.compile(r"/media/wp/([^\"'>\s\)]+)")

    for page in SitePage.objects.all():
        for match in pattern.finditer(page.body_html or ""):
            paths.add(match.group(1).split("?", 1)[0])

    for post in BlogPost.objects.all():
        for field in (post.body, post.hero_image, post.excerpt, post.image_url):
            for match in pattern.finditer(field or ""):
                paths.add(match.group(1).split("?", 1)[0])

    for row in SiteConfig.objects.all():
        import json

        blob = json.dumps(row.value or {}, ensure_ascii=False)
        for match in pattern.finditer(blob):
            paths.add(match.group(1).split("?", 1)[0])

    try:
        from apps.frontend import site_content as sc

        for key in sc.HERO_MEDIA:
            paths.add(_normalize_rel(sc.HERO_MEDIA[key]))
        for item in sc.BENEFIT_MEDIA:
            paths.add(_normalize_rel(item["wp"]))
    except Exception:
        pass

    templates = Path(settings.BASE_DIR) / "templates"
    if templates.is_dir():
        for tpl in templates.rglob("*.html"):
            text = tpl.read_text(encoding="utf-8", errors="ignore")
            for match in pattern.finditer(text):
                paths.add(match.group(1).split("?", 1)[0])

    return {p for p in paths if p}


def vendor_site_media(*, dry_run: bool = False) -> dict[str, int]:
    wp_root = Path(settings.MEDIA_ROOT) / "wp"
    dest_root = SITE_MEDIA_STATIC_ROOT
    dest_root.mkdir(parents=True, exist_ok=True)

    referenced = collect_referenced_wp_paths()
    copied = 0
    skipped = 0
    missing = 0

    for rel in sorted(referenced):
        src = wp_root / rel
        dest = dest_root / rel
        if not src.is_file():
            missing += 1
            continue
        if dest.is_file() and dest.stat().st_size == src.stat().st_size:
            skipped += 1
            continue
        if dry_run:
            copied += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    return {
        "referenced": len(referenced),
        "copied": copied,
        "skipped": skipped,
        "missing": missing,
    }
