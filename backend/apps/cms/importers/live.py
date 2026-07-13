from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from typing import Any

from django.db import transaction

from apps.cms.importers.site import DE_ONLY_SLUGS, _body_class, _django_slug, _detect_locale
from apps.cms.media import fix_media_urls_in_html, normalize_wp_media_path
from apps.cms.models import SiteConfig, SitePage

PROD_BASE = "https://turtlecruisecyprus.com"
WP_PAGES_API = f"{PROD_BASE}/wp-json/wp/v2/pages"

# Skip WP utility pages; legal pages have empty REST bodies (handled separately later).
SKIP_WP_SLUGS = {
    "privacy-policy",
    "terms-conditions",
    "terms-conditions-2",
    "fulfillment-policy",
    "sample-page",
}


def _fetch_json(url: str) -> Any:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "TurtleCruiseCMSImport/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response), response.headers
    except urllib.error.URLError:
        proc = subprocess.run(
            [
                "curl",
                "-fsSL",
                "-H",
                "Accept: application/json",
                "-A",
                "TurtleCruiseCMSImport/1.0",
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        return json.loads(proc.stdout), {}


def fetch_all_wp_pages() -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    page_num = 1
    while True:
        url = f"{WP_PAGES_API}?per_page=10&page={page_num}"
        try:
            batch, headers = _fetch_json(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 400:
                break
            raise
        if not isinstance(batch, list) or not batch:
            break
        pages.extend(batch)
        total_pages = int(headers.get("X-WP-TotalPages", "0") or 0)
        if total_pages:
            if page_num >= total_pages:
                break
        elif len(batch) < 10:
            break
        page_num += 1
    return pages


def _locale_from_wp_page(wp_page: dict[str, Any]) -> str:
    link = (wp_page.get("link") or "").lower()
    slug = wp_page.get("slug") or ""
    title = (wp_page.get("title") or {}).get("rendered", "")
    if "/de/" in link or slug in DE_ONLY_SLUGS:
        return "de"
    return _detect_locale(slug, title)


def rewrite_prod_html(html: str) -> str:
    if not html:
        return html

    html = html.replace(f"{PROD_BASE}/wp-content/uploads/", "/media/wp/")
    html = re.sub(
        r"https?://[^/]+/wp-content/uploads/",
        "/media/wp/",
        html,
    )
    html = html.replace('src="/img/dist/', 'src="/static/frontend/img/dist/')

    # Prod morning cruise URL → Django route.
    html = html.replace(f"{PROD_BASE}/cruise/", "/chill-cruise/")
    html = html.replace('href="/cruise/', 'href="/chill-cruise/')
    html = html.replace(f"{PROD_BASE}/contacts-about/", "/contacts/")
    html = html.replace('href="/contacts-about/', 'href="/contacts/')

    return fix_media_urls_in_html(html)


def extract_media_relpaths_from_html(html: str) -> set[str]:
    paths: set[str] = set()
    for match in re.finditer(r"/media/wp/([^\"'>\s]+)", html or ""):
        paths.add(normalize_wp_media_path(match.group(1)))
    for match in re.finditer(r"wp-content/uploads/([^\"'>\s]+)", html or ""):
        paths.add(normalize_wp_media_path(match.group(1)))
    return {p for p in paths if p}


def import_live_pages(min_body: int = 500) -> dict[str, int]:
    wp_pages = fetch_all_wp_pages()
    stats = {"fetched": len(wp_pages), "imported": 0, "skipped": 0}

    with transaction.atomic():
        for wp_page in wp_pages:
            wp_slug = wp_page.get("slug") or ""
            if wp_slug in SKIP_WP_SLUGS:
                stats["skipped"] += 1
                continue

            rendered = (wp_page.get("content") or {}).get("rendered") or ""
            if len(rendered.strip()) < min_body:
                stats["skipped"] += 1
                continue

            locale = _locale_from_wp_page(wp_page)
            slug = _django_slug(wp_slug, locale)
            title = (wp_page.get("title") or {}).get("rendered") or ""
            title = re.sub(r"<[^>]+>", "", title).strip()

            body_html = rewrite_prod_html(rendered)
            SitePage.objects.update_or_create(
                locale=locale,
                slug=slug,
                defaults={
                    "wp_slug": wp_slug,
                    "title": title,
                    "body_html": body_html,
                    "body_class": _body_class(slug),
                    "is_published": True,
                },
            )
            stats["imported"] += 1

    return stats


def _fetch_html(url: str) -> str:
    proc = subprocess.run(
        ["curl", "-fsSL", "-A", "TurtleCruiseCMSImport/1.0", url],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return proc.stdout


def _clean_text(value: str) -> str:
    import html as html_module

    value = re.sub(r"\s+", " ", value or "")
    return html_module.unescape(value).strip()


def _scrape_footer_locale(path: str) -> dict[str, Any]:
    page_html = _fetch_html(f"{PROD_BASE}{path}")
    block = re.search(r"<footer[^>]*>(.*)</footer>", page_html, re.S)
    if not block:
        return {}
    footer = block.group(1)

    title_m = re.search(r'class="footer__title">(.*?)</h2>', footer, re.S)
    lead_m = re.search(r'class="footer__lead">(.*?)</p>', footer, re.S)
    desc_m = re.search(
        r'class="footer__desc">.*?<p class="footer__lead">.*?</p>\s*<p>(.*?)</p>',
        footer,
        re.S,
    )
    locations = []
    for match in re.finditer(
        r'<a href="([^"]+)"[^>]*class="footer__loc-btn"[^>]*>.*?<span>(.*?)</span>',
        footer,
        re.S,
    ):
        locations.append(
            {
                "label": _clean_text(match.group(2)),
                "url": match.group(1),
            }
        )

    bg_desktop_m = re.search(r"<footer.*?<img src=\"([^\"]+)\"", page_html, re.S)
    bg_mobile_m = re.search(r"<footer.*?source[^>]+srcset=\"([^\"]+)\"", page_html, re.S)

    return {
        "title": title_m.group(1).strip() if title_m else "",
        "lead": _clean_text(lead_m.group(1)) if lead_m else "",
        "desc": _clean_text(desc_m.group(1)) if desc_m else "",
        "locations": locations,
        "bg_desktop": rewrite_prod_html(bg_desktop_m.group(1)) if bg_desktop_m else "",
        "bg_mobile": rewrite_prod_html(bg_mobile_m.group(1)) if bg_mobile_m else "",
    }


def _scrape_socials() -> dict[str, str]:
    page_html = _fetch_html(f"{PROD_BASE}/")
    socials: dict[str, str] = {}
    for label in ("TikTok", "Instagram", "Facebook", "YouTube"):
        for match in re.finditer(rf'aria-label="{label}"', page_html):
            chunk = page_html[max(0, match.start() - 250) : match.end() + 120]
            url_m = re.search(r'href="([^"]+)"', chunk)
            if url_m:
                socials[label.lower()] = url_m.group(1)
                break
    return socials


def import_live_site_config() -> dict[str, int]:
    en_footer = _scrape_footer_locale("/")
    de_footer = _scrape_footer_locale("/de/")
    page_html = _fetch_html(f"{PROD_BASE}/")
    copyright_m = re.search(r'class="footer__copy">(.*?)</span>', page_html, re.S)
    made_url_m = re.search(r'class="footer__made".*?<a href="([^"]+)"', page_html, re.S)

    footer = {
        "en": en_footer,
        "de": de_footer,
        "copyright": _clean_text(copyright_m.group(1)) if copyright_m else "© 2026 Turtle Cruise by SCUBACAT",
        "payments_label": "Available",
        "payment_icons": [
            {"url": "/static/frontend/img/dist/visa.svg", "alt": "Visa"},
            {"url": "/static/frontend/img/dist/mastercard.svg", "alt": "Mastercard"},
            {"url": "/static/frontend/img/dist/paypal.svg", "alt": "PayPal"},
            {"url": "/static/frontend/img/dist/revolut.svg", "alt": "Revolut"},
        ],
        "made_by_label": "Made by",
        "made_by_url": made_url_m.group(1) if made_url_m else "https://ochi.design/",
        "made_by_logo": "/static/frontend/img/dist/ochi.svg",
        "footer_logo": "/static/frontend/img/dist/footer-logo.svg",
    }
    socials = _scrape_socials()

    with transaction.atomic():
        SiteConfig.objects.update_or_create(key="footer", defaults={"value": footer})
        if socials:
            SiteConfig.objects.update_or_create(key="socials", defaults={"value": socials})

    return {"footer": 1, "socials": 1 if socials else 0}
