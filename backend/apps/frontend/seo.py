from __future__ import annotations

from django.conf import settings

from apps.cms.models import BlogPost, SitePage

from .i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, language_switch_url
from .site_data import PAGES

DEFAULT_DESCRIPTION = "Morning and sunset turtle cruises from Ayia Napa, Cyprus. Book online with SCUBACAT."
DEFAULT_OG_IMAGE = "/static/frontend/img/dist/og-default.jpg"


def absolute_url(path: str) -> str:
    base = settings.SITE_BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def default_seo_meta(request) -> dict:
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    path = request.path_info or "/"
    title = "Turtle Cruise Cyprus"
    description = DEFAULT_DESCRIPTION
    og_type = "website"
    og_image = DEFAULT_OG_IMAGE
    published_at = None

    slug = path.strip("/")
    if locale != DEFAULT_LOCALE and slug.startswith("de/"):
        slug = slug[3:]

    if slug:
        post = BlogPost.objects.filter(slug=slug.split("/")[-1], is_published=True).first()
        if post:
            title = f"{post.title} — Turtle Cruise Cyprus"
            description = (post.excerpt or DEFAULT_DESCRIPTION)[:300]
            og_type = "article"
            og_image = post.image_url or DEFAULT_OG_IMAGE
            published_at = post.published_at
        else:
            page_slug = slug.rstrip("/")
            site_page = SitePage.objects.filter(locale=locale, slug=page_slug, is_published=True).first()
            if site_page:
                title = site_page.title or title
                description = (site_page.meta_description or DEFAULT_DESCRIPTION)[:300]

    alternates = []
    for code in SUPPORTED_LOCALES:
        if code == locale:
            continue
        alternates.append(
            {
                "hreflang": code,
                "url": absolute_url(language_switch_url(locale, code, path)),
            }
        )

    return {
        "title": title,
        "description": description,
        "canonical": absolute_url(path),
        "og_type": og_type,
        "og_image": absolute_url(og_image) if og_image.startswith("/") else og_image,
        "locale": locale,
        "alternates": alternates,
        "published_at": published_at.isoformat() if published_at else "",
        "robots": "index,follow",
    }


def build_seo_meta(request, **overrides) -> dict:
    meta = default_seo_meta(request)
    meta.update({k: v for k, v in overrides.items() if v is not None and v != ""})
    if overrides.get("og_image", "").startswith("/"):
        meta["og_image"] = absolute_url(overrides["og_image"])
    return meta
