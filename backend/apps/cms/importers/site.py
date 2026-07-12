from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db import transaction

from apps.cms.media import normalize_wp_media_path
from apps.cms.acf_renderer import render_blocks
from apps.cms.blog_post_renderer import excerpt_from_body, hero_image_url, render_blog_post_body
from apps.cms.legal_renderer import render_genesis_legal_html
from apps.cms.models import BlogPost, SiteConfig, SitePage
from apps.frontend.i18n import DE_SLUG_MAP, EN_SLUG_MAP
from apps.migration_wp.importers.wordpress_dump import iter_insert_rows, load_postmeta


def _attachment_map(sql_path: Path) -> dict[int, str]:
    meta = load_postmeta(sql_path)
    out: dict[int, str] = {}
    for post_id, fields in meta.items():
        files = fields.get("_wp_attached_file") or []
        if files:
            out[post_id] = normalize_wp_media_path(files[0])
    return out


def _iter_pages(sql_path: Path):
    for row in iter_insert_rows(sql_path, "wp_posts"):
        if len(row) >= 21 and row[20] == "page" and row[7] == "publish":
            yield {
                "id": int(row[0]),
                "slug": row[11],
                "title": row[5],
                "content": row[4],
            }


DE_ONLY_SLUGS = {
    "de",
    "morgenrundfahrt",
    "sonnenuntergangstour",
    "galerie",
    "bewertungen",
    "haeufige-fragen",
    "kontakt-ueber-uns",
    "vielen-dank-fuer-ihre-buchung",
    "privatcharter",
}


def _django_slug(wp_slug: str, locale: str) -> str:
    mapping = DE_SLUG_MAP if locale == "de" else EN_SLUG_MAP
    path = mapping.get(wp_slug, wp_slug)
    return path.rstrip("/")


def _detect_locale(wp_slug: str, title: str = "") -> str:
    if wp_slug in DE_ONLY_SLUGS:
        return "de"
    if any(
        marker in title
        for marker in (
            "ä",
            "ö",
            "ü",
            "ß",
            "Über uns",
            "Privatcharter",
            "Morgenrundfahrt",
            "Sonnenuntergang",
            "Galerie",
            "Bewertungen",
            "Häufige",
            "Vielen Dank",
            "Startseite",
        )
    ):
        return "de"
    return "en"


def _body_class(slug: str) -> str:
    return slug.replace("/", "-") or "home"


LEGAL_SLUGS = {"privacy-policy", "terms-conditions", "fulfillment-policy"}


def _parse_option_repeater(options: dict, base: str) -> list[dict[str, str]]:
    try:
        count = int(options.get(base, 0) or 0)
    except (TypeError, ValueError):
        count = 0
    items: list[dict[str, str]] = []
    for i in range(count):
        item: dict[str, str] = {}
        prefix = f"{base}_{i}_"
        for key, value in options.items():
            if key.startswith(prefix) and not key.startswith(f"_{base}"):
                item[key[len(prefix) :]] = value
        if item:
            items.append(item)
    return items


def _media_url(media_map: dict[int, str], attachment_id: Any) -> str:
    try:
        aid = int(attachment_id)
    except (TypeError, ValueError):
        return ""
    rel = normalize_wp_media_path(media_map.get(aid, ""))
    return f"/media/wp/{rel.lstrip('/')}" if rel else ""


def _import_footer_config(options: dict, media_map: dict[int, str]) -> None:
    payment_static = [
        "/static/frontend/img/dist/visa.svg",
        "/static/frontend/img/dist/mastercard.svg",
        "/static/frontend/img/dist/paypal.svg",
        "/static/frontend/img/dist/revolut.svg",
    ]
    payment_icons = [
        {"url": url, "alt": item.get("alt", name)}
        for url, name in zip(
            payment_static,
            ("Visa", "Mastercard", "PayPal", "Revolut"),
        )
    ]

    footer = {
        "en": {
            "title": options.get("en_footer_title", ""),
            "lead": options.get("en_footer_lead", ""),
            "desc": options.get("en_footer_desc", ""),
            "locations": _parse_option_repeater(options, "en_locations"),
        },
        "de": {
            "title": options.get("de_footer_title", ""),
            "lead": options.get("de_footer_lead", ""),
            "desc": options.get("de_footer_desc", ""),
            "locations": _parse_option_repeater(options, "de_locations"),
        },
        "copyright": options.get("options_footer_copyright", ""),
        "payments_label": options.get("options_payments_label", "Available"),
        "payment_icons": payment_icons,
        "made_by_label": options.get("options_footer_made_by_label", "Made by"),
        "made_by_url": options.get("options_footer_made_by_url", ""),
        "made_by_logo": "/static/frontend/img/dist/ochi.svg",
        "footer_logo": "/static/frontend/img/dist/footer-logo.svg",
    }
    SiteConfig.objects.update_or_create(key="footer", defaults={"value": footer})


def _meta_description(fields: dict, title: str = "") -> str:
    for key in (
        "_genesis_description",
        "autodescription_description",
        "_open_graph_description",
        "description",
    ):
        values = fields.get(key) or []
        if values and str(values[0]).strip():
            return str(values[0]).strip()[:500]
    return ""


def _legal_body(page_id: int, postmeta: dict, acf_html: str) -> str:
    if acf_html.strip():
        return acf_html
    fields = postmeta.get(page_id, {})
    genesis = render_genesis_legal_html(fields)
    return genesis


def import_site(sql_path: str | Path) -> dict[str, int]:
    sql_path = Path(sql_path)
    media_map = _attachment_map(sql_path)
    postmeta = load_postmeta(sql_path)
    stats = {"pages": 0, "blog": 0, "config": 0}

    with transaction.atomic():
        for page in _iter_pages(sql_path):
            locale = _detect_locale(page["slug"], page["title"])
            slug = _django_slug(page["slug"], locale)
            html_body = render_blocks(page["content"], media_map=media_map, locale=locale)
            if page["slug"] in LEGAL_SLUGS:
                html_body = _legal_body(page["id"], postmeta, html_body)
            SitePage.objects.update_or_create(
                locale=locale,
                slug=slug,
                defaults={
                    "wp_slug": page["slug"],
                    "title": page["title"],
                    "body_html": html_body,
                    "body_class": _body_class(slug),
                    "meta_description": _meta_description(postmeta.get(page["id"], {}), page["title"]),
                    "is_published": True,
                },
            )
            stats["pages"] += 1

        for row in iter_insert_rows(sql_path, "wp_posts"):
            if len(row) >= 21 and row[20] == "post" and row[7] == "publish":
                post_id = int(row[0])
                slug = row[11]
                title = row[5]
                fields = postmeta.get(post_id, {})
                body_html = render_blog_post_body(fields, media_map=media_map)
                if not body_html.strip():
                    body_html = row[4]
                hero = hero_image_url(fields, media_map=media_map)
                excerpt = (row[6] or "").strip() or excerpt_from_body(body_html)
                published_at = row[2] or None
                defaults: dict[str, Any] = {
                    "title": title,
                    "excerpt": excerpt[:300],
                    "body": body_html,
                    "hero_image": hero,
                    "is_published": True,
                }
                if published_at:
                    from django.utils import timezone
                    from django.utils.dateparse import parse_datetime

                    dt = parse_datetime(published_at.replace(" ", "T", 1))
                    if dt:
                        defaults["published_at"] = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                BlogPost.objects.update_or_create(slug=slug, defaults=defaults)
                stats["blog"] += 1

        # Global options from wp_options (social links etc.)
        from apps.migration_wp.importers.wordpress_dump import load_options

        options = load_options(sql_path)
        social_keys = ["tiktok", "instagram", "facebook", "youtube"]
        socials = {k: options.get(f"options_{k}", "") for k in social_keys}
        SiteConfig.objects.update_or_create(key="socials", defaults={"value": socials})
        _import_footer_config(options, media_map)
        stats["config"] += 2

    return stats
