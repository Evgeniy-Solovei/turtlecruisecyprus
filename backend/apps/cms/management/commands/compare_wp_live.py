from django.core.management.base import BaseCommand

from apps.cms.importers.live import PROD_BASE, _locale_from_wp_page, fetch_all_wp_pages, rewrite_prod_html
from apps.cms.importers.site import _django_slug
from apps.cms.models import SitePage


class Command(BaseCommand):
    help = "Compare imported CMS pages with live prod (section/image counts)."

    def handle(self, *args, **options):
        import re
        import subprocess

        wp_by_key: dict[tuple[str, str], dict] = {}
        for wp_page in fetch_all_wp_pages():
            locale = _locale_from_wp_page(wp_page)
            slug = _django_slug(wp_page.get("slug") or "", locale)
            html = rewrite_prod_html((wp_page.get("content") or {}).get("rendered") or "")
            if len(html) < 500:
                continue
            wp_by_key[(locale, slug)] = {
                "title": wp_page.get("slug"),
                "html": html,
            }

        self.stdout.write(f"{'locale':5} {'slug':18} {'prod_img':8} {'local_img':8} {'match':5}")
        for (locale, slug), prod in sorted(wp_by_key.items()):
            page = SitePage.objects.filter(locale=locale, slug=slug).first()
            local_html = page.body_html if page else ""
            prod_imgs = len(re.findall(r"/media/wp/", prod["html"]))
            local_imgs = len(re.findall(r"/media/wp/", local_html))
            match = "OK" if page and abs(prod_imgs - local_imgs) <= 2 else "DIFF"
            self.stdout.write(
                f"{locale:5} {slug or 'home':18} {prod_imgs:8} {local_imgs:8} {match:5}"
            )

        self.stdout.write("")
        self.stdout.write("Prod base: " + PROD_BASE)
        self.stdout.write("If DIFF: run python manage.py import_wp_live && python manage.py sync_wp_media_live")
