from __future__ import annotations

import json
import re
import shutil
from functools import lru_cache
from pathlib import Path

from django.conf import settings

# Site photos vendored into git — served by WhiteNoise (no /media volume needed).
SITE_MEDIA_STATIC_PREFIX = "/static/frontend/img/site/"
SITE_MEDIA_STATIC_ROOT = Path(settings.BASE_DIR) / "static" / "frontend" / "img" / "site"
SITE_MEDIA_MANIFEST = SITE_MEDIA_STATIC_ROOT / "manifest.json"
MEDIA_WP_PATTERN = re.compile(r"/media/wp/([^\"'>\s,\)]+)")
SITE_STATIC_PATTERN = re.compile(r"/static/frontend/img/site/([^\"'>\s,\)]+)")


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


def site_media_collectstatic_root() -> Path:
    return Path(settings.STATIC_ROOT) / "frontend" / "img" / "site"


@lru_cache(maxsize=1)
def _load_site_media_manifest() -> set[str]:
    try:
        payload = json.loads(SITE_MEDIA_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return set()
    if isinstance(payload, list):
        return {str(item) for item in payload}
    return set()


def _media_file_exists(rel: str) -> bool:
    rel = _normalize_rel(rel)
    if not rel:
        return False
    if rel in _load_site_media_manifest():
        return True
    for root in (SITE_MEDIA_STATIC_ROOT, site_media_collectstatic_root()):
        if (root / rel).is_file():
            return True
    return False


def site_media_public_url(rel: str) -> str | None:
    rel = _normalize_rel(rel)
    if not rel:
        return None
    if _media_file_exists(rel):
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

    return MEDIA_WP_PATTERN.sub(_sub, html)


def bake_storage_media_urls(value: str) -> str:
    """Persist static URLs in DB so deploy does not depend on /media volume."""
    from apps.cms.media import fix_media_urls_in_html

    return fix_media_urls_in_html(value or "")


def _extract_wp_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for match in MEDIA_WP_PATTERN.finditer(text or ""):
        paths.add(match.group(1).split("?", 1)[0])
    for match in SITE_STATIC_PATTERN.finditer(text or ""):
        paths.add(match.group(1).split("?", 1)[0])
    return paths


def collect_referenced_wp_paths() -> set[str]:
    from apps.cms.models import BlogPost, SiteConfig, SitePage

    paths: set[str] = set()

    for page in SitePage.objects.all():
        paths |= _extract_wp_paths(page.body_html)

    for post in BlogPost.objects.all():
        for field in (post.body, post.hero_image, post.excerpt, post.cover_image_static):
            paths |= _extract_wp_paths(field or "")

    for row in SiteConfig.objects.all():
        import json

        blob = json.dumps(row.value or {}, ensure_ascii=False)
        paths |= _extract_wp_paths(blob)

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
            paths |= _extract_wp_paths(tpl.read_text(encoding="utf-8", errors="ignore"))

    return {p for p in paths if p}


def collect_vendored_wp_paths() -> set[str]:
    """All image paths that must ship in git (manifest + current CMS references)."""
    paths = collect_referenced_wp_paths()
    paths |= _load_site_media_manifest()
    return {p for p in paths if p}


def bake_cms_media_urls() -> dict[str, int]:
    from apps.cms.models import BlogPost, SiteConfig, SitePage

    stats = {"pages": 0, "posts": 0, "configs": 0}

    for page in SitePage.objects.all():
        baked = bake_storage_media_urls(page.body_html)
        if baked != (page.body_html or ""):
            page.body_html = baked
            page.save(update_fields=["body_html"])
            stats["pages"] += 1

    for post in BlogPost.objects.all():
        updates: dict[str, str] = {}
        for field in ("body", "hero_image", "excerpt", "cover_image_static"):
            raw = getattr(post, field) or ""
            baked = bake_storage_media_urls(raw)
            if baked != raw:
                updates[field] = baked
        if updates:
            for field, value in updates.items():
                setattr(post, field, value)
            post.save(update_fields=list(updates))
            stats["posts"] += 1

    for row in SiteConfig.objects.all():
        import json

        blob = json.dumps(row.value or {}, ensure_ascii=False)
        baked = bake_storage_media_urls(blob)
        if baked != blob:
            row.value = json.loads(baked)
            row.save(update_fields=["value"])
            stats["configs"] += 1

    return stats


def _manifest_paths_on_disk() -> set[str]:
    if not SITE_MEDIA_STATIC_ROOT.is_dir():
        return set()
    return {
        str(path.relative_to(SITE_MEDIA_STATIC_ROOT)).replace("\\", "/")
        for path in SITE_MEDIA_STATIC_ROOT.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }


def _write_site_media_manifest(paths: set[str]) -> None:
    merged = sorted(paths | _manifest_paths_on_disk())
    if not merged:
        return
    SITE_MEDIA_MANIFEST.write_text(
        json.dumps(merged, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )
    _load_site_media_manifest.cache_clear()


def vendor_site_media(*, dry_run: bool = False) -> dict[str, int]:
    wp_root = Path(settings.MEDIA_ROOT) / "wp"
    dest_root = SITE_MEDIA_STATIC_ROOT
    dest_root.mkdir(parents=True, exist_ok=True)

    referenced = collect_vendored_wp_paths()
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

    if not dry_run:
        _write_site_media_manifest(referenced)

    return {
        "referenced": len(referenced),
        "copied": copied,
        "skipped": skipped,
        "missing": missing,
        "manifest": len(_load_site_media_manifest()),
    }
