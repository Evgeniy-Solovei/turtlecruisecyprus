from pathlib import Path

from django.core.management.base import BaseCommand

from apps.cms.site_media import bake_cms_media_urls
from apps.cms.snapshot import SNAPSHOT_PATH, import_cms_snapshot


class Command(BaseCommand):
    help = "Import CMS content from cms_snapshot/snapshot.json (same HTML as local dev)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            type=str,
            default="",
            help=f"Snapshot path (default: {SNAPSHOT_PATH})",
        )
        parser.add_argument(
            "--no-bake",
            action="store_true",
            help="Skip rewriting /media/wp URLs to /static/frontend/img/site/",
        )

    def handle(self, *args, **options):
        path = Path(options["input"]) if options["input"] else None
        stats = import_cms_snapshot(path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported pages={stats['pages']} configs={stats['configs']} posts={stats['posts']}"
            )
        )
        if not options["no_bake"]:
            baked = bake_cms_media_urls()
            self.stdout.write(
                f"Baked media URLs: pages={baked['pages']} posts={baked['posts']} configs={baked['configs']}"
            )
