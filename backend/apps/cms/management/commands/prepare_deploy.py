from django.core.management.base import BaseCommand

from apps.cms.site_media import bake_cms_media_urls, vendor_site_media
from apps.cms.snapshot import export_cms_snapshot


class Command(BaseCommand):
    help = (
        "Before git push: vendor images, bake URLs, export cms_snapshot/snapshot.json. "
        "Server loads this file on every deploy — what you see locally is what ships."
    )

    def handle(self, *args, **options):
        stats = vendor_site_media()
        self.stdout.write(
            f"Images: referenced={stats['referenced']} copied={stats['copied']} "
            f"missing={stats['missing']}"
        )
        if stats["missing"]:
            self.stdout.write(
                self.style.WARNING("Run sync_wp_media or sync_wp_media_live first.")
            )

        baked = bake_cms_media_urls()
        self.stdout.write(
            f"Baked URLs: pages={baked['pages']} posts={baked['posts']} configs={baked['configs']}"
        )

        snap = export_cms_snapshot()
        self.stdout.write(
            self.style.SUCCESS(
                f"Ready to commit: cms_snapshot/snapshot.json + static/frontend/img/site/ "
                f"(pages={snap['pages']}, {snap['path']})"
            )
        )
