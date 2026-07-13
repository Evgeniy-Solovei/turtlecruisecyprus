from django.core.management.base import BaseCommand

from apps.cms.site_media import bake_cms_media_urls


class Command(BaseCommand):
    help = "Rewrite /media/wp/ URLs in CMS DB rows to /static/frontend/img/site/."

    def handle(self, *args, **options):
        stats = bake_cms_media_urls()
        self.stdout.write(
            self.style.SUCCESS(
                f"Baked pages={stats['pages']} posts={stats['posts']} configs={stats['configs']}"
            )
        )
