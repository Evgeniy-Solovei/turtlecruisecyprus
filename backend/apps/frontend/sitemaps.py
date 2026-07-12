from __future__ import annotations

from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse

from apps.cms.models import BlogPost, SitePage

from .i18n import DEFAULT_LOCALE, locale_prefix
from .site_data import PAGES

STATIC_PATHS = [
    "",
    "chill-cruise/",
    "sunset-cruise/",
    "private-charter/",
    "gallery/",
    "reviews/",
    "faq/",
    "blog/",
    "contacts/",
    "privacy-policy/",
    "terms-conditions/",
    "fulfillment-policy/",
]


def _loc(path: str, locale: str) -> str:
    prefix = locale_prefix(locale)
    if path in ("", "/"):
        return f"{settings.SITE_BASE_URL.rstrip('/')}{prefix or '/'}"
    return f"{settings.SITE_BASE_URL.rstrip('/')}{prefix}/{path}"


def sitemap_xml(request) -> HttpResponse:
    urls: list[str] = []

    for locale in ("en", "de"):
        for path in STATIC_PATHS:
            urls.append(_loc(path, locale))

        for page in SitePage.objects.filter(locale=locale, is_published=True).exclude(slug=""):
            if f"{page.slug}/" not in STATIC_PATHS:
                urls.append(_loc(f"{page.slug}/", locale))

    for post in BlogPost.objects.filter(is_published=True):
        urls.append(_loc(f"{post.slug}/", DEFAULT_LOCALE))
        urls.append(_loc(f"{post.slug}/", "de"))

    body = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in sorted(set(urls)):
        body += "  <url>\n"
        body += f"    <loc>{escape(url)}</loc>\n"
        body += "  </url>\n"
    body += "</urlset>\n"
    return HttpResponse(body, content_type="application/xml")


def robots_txt(request) -> HttpResponse:
    base = settings.SITE_BASE_URL.rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
